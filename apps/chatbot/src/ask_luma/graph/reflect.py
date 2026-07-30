from pydantic import BaseModel

from ask_luma import llm
from behavior_core.config import BehaviorConfig


class Reflection(BaseModel):
    resolved: bool
    missing: str | None = None
    next_query: str | None = None


def run(
    question: str, evidence: list[dict[str, str]], tried: list[str], config: BehaviorConfig
) -> tuple[Reflection, llm.LLMResult]:
    """Is the evidence enough? Three small fields, no prose.

    Keeping this node from writing any of the answer is what makes it cheap and
    makes `resolved` a clean signal that step 2 can assert on. It costs one
    extra LLM call versus letting it answer opportunistically.
    """
    blocks = "\n\n".join(
        f"[{item['article_title']} > {item['heading']}]\n{item['text']}" for item in evidence
    ) or "(nothing found so far)"

    user = (
        f"Question: {question}\n\n"
        f"Queries already tried: {', '.join(tried)}\n\n"
        f"Evidence:\n{blocks}"
    )
    return llm.call_structured(config.reflect_prompt, user, config.temperature, Reflection)
