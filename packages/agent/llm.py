"""Thin wrapper over LiteLLM: one call, structured output, retries, cost.

Retries cover 429 / timeout / 5xx and nothing else. Those are the provider's
state, not our bug, and free-tier 429s are routine. Every other error is us
constructing a bad request, and retrying just makes the same mistake again.
"""

import os
import time
from typing import Any, TypeVar

import litellm
from pydantic import BaseModel
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

litellm.suppress_debug_info = True
litellm.drop_params = True

MODEL = os.getenv("MODEL", "gemini/gemini-3.1-flash-lite")

# A controlled variable, not a lever. It used to be one of the versioned six and
# was cut in step 3 -- see TO-06. Deliberately not an environment variable either:
# a knob that silently differs between two machines makes their evaluation results
# incomparable, which is the failure mode this whole project is about.
TEMPERATURE = 0.2

# LiteLLM's completion_cost() looks prices up by model name and silently returns
# 0 for names it does not know. Cost is a first-class metric here -- half the
# point of the step 2 demo is that a regression can look cheaper -- so it is not
# allowed to quietly become zero. USD per million tokens.
PRICES = {
    "gemini-3.1-flash-lite": (0.25, 1.50),
    "gemini-3.5-flash": (1.50, 9.00),
    "gemini-2.0-flash": (0.10, 0.40),
    # Non-Gemini entries exist so a reviewer holding one of the keys the take-home
    # actually provisions can run this (TO-31). Transcribed from public price
    # lists, not measured here, so trust them one notch less than the Gemini row.
    "claude-haiku-4-5": (1.00, 5.00),
    "claude-sonnet-4-5": (3.00, 15.00),
    "gpt-4o-mini": (0.15, 0.60),
    "gpt-4.1-mini": (0.40, 1.60),
}
DEFAULT_PRICE = (1.50, 9.00)  # assume expensive rather than free if the model is unknown

# Which environment variable each provider prefix needs. Only used to fail early
# with a useful message; LiteLLM does the actual reading.
PROVIDER_KEYS = {
    "gemini": "GEMINI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "openai": "OPENAI_API_KEY",
}

TRANSIENT = (
    litellm.RateLimitError,
    litellm.Timeout,
    litellm.APIConnectionError,
    litellm.InternalServerError,
    litellm.ServiceUnavailableError,
)

T = TypeVar("T", bound=BaseModel)


class LLMResult(BaseModel):
    text: str
    tokens_in: int
    tokens_out: int
    cost_usd: float
    latency_ms: int


def _cost(tokens_in: int, tokens_out: int) -> float:
    per_in, per_out = PRICES.get(MODEL.split("/")[-1], DEFAULT_PRICE)
    return (tokens_in * per_in + tokens_out * per_out) / 1_000_000


def require_key() -> None:
    """Fail at startup if the key MODEL needs is missing, naming the variable.

    Without this the first question a reviewer asks turns into a 502 from deep
    inside LiteLLM, which reads as a bug in this project rather than as a missing
    credential. Called from the lifespan so the process refuses to come up rather
    than serving a surface that cannot answer anything.
    """
    provider = MODEL.split("/")[0]
    variable = PROVIDER_KEYS.get(provider)
    if variable is None:
        raise RuntimeError(
            f"MODEL={MODEL!r} names provider {provider!r}, which this project has no "
            f"price entry or key mapping for. Known: {', '.join(sorted(PROVIDER_KEYS))}. "
            "See TO-31 in ai-discussion/trade-offs.md."
        )
    if not os.getenv(variable):
        raise RuntimeError(
            f"MODEL={MODEL!r} needs {variable}, which is empty or unset. "
            "Copy .env.example to .env and fill it in, or pass it through the "
            "environment. The six behavior levers are not configured here -- they "
            "live in the database as versioned rows."
        )


@retry(
    retry=retry_if_exception_type(TRANSIENT),
    # Sized against the free tier's 15 requests/minute: a 429 asks for a ~10s
    # wait, so a short ceiling guarantees every retry fails again. Five attempts
    # with this backoff spans roughly the length of the rate-limit window.
    wait=wait_exponential(multiplier=2, min=2, max=30),
    stop=stop_after_attempt(5),
    reraise=True,
)
def _complete(**kwargs: Any):
    return litellm.completion(**kwargs)


def call(
    system: str,
    user: str,
    schema: type[BaseModel] | None = None,
    temperature: float = TEMPERATURE,
) -> tuple[str, LLMResult]:
    """One LLM turn. Pass a schema to get guaranteed-shaped JSON back.

    Gemini's responseSchema removes format errors as a category. That is worth
    more than the try/except it saves: without it a malformed response looks
    like a behavior regression during evaluation, when it is really just a stray
    code fence.
    """
    started = time.perf_counter()
    kwargs: dict[str, Any] = {
        "model": MODEL,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        "temperature": temperature,
        # Internal reasoning is off. Not to save money: it makes the same question
        # take a wildly different amount of time on different runs, and that noise
        # would land straight in the latency numbers step 2 compares versions on.
        # Dropped automatically for models that have no such setting.
        "reasoning_effort": "disable",
    }
    if schema is not None:
        kwargs["response_format"] = schema

    response = _complete(**kwargs)
    usage = response.usage
    tokens_in, tokens_out = usage.prompt_tokens, usage.completion_tokens

    return response.choices[0].message.content or "", LLMResult(
        text=response.choices[0].message.content or "",
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        cost_usd=_cost(tokens_in, tokens_out),
        latency_ms=int((time.perf_counter() - started) * 1000),
    )


def call_structured(
    system: str, user: str, schema: type[T], temperature: float = TEMPERATURE
) -> tuple[T, LLMResult]:
    """Same as call(), parsed into the schema.

    A ValidationError here propagates all the way out to the route boundary and
    becomes a 502. We do not feed the error back to the model to self-correct:
    with responseSchema in place a format failure means something is genuinely
    broken, and retrying would burn quota on the same failure while disguising a
    bug as occasional slowness.
    """
    text, result = call(system, user, schema=schema, temperature=temperature)
    return schema.model_validate_json(text), result
