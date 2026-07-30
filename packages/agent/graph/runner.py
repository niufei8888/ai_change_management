"""The ReAct loop: plan -> search -> reflect -> (loop) -> synthesize.

Every node appends its own latency and token counts to the trajectory. That
granularity is the point: when step 2 sees a version get slower, it has to be
able to say which node got slower, otherwise the diff is just a number.
"""

import time
from dataclasses import dataclass, field
from typing import Any

from agent import llm, search
from agent.graph import plan, reflect, synthesize
from behavior_core.config import BehaviorConfig


@dataclass
class Outcome:
    answer: str
    citations: list[dict[str, str]] = field(default_factory=list)
    trajectory: list[dict[str, Any]] = field(default_factory=list)
    retrieved_articles: list[str] = field(default_factory=list)
    # The actual chunks the synthesize node saw. The trajectory records that a
    # search happened and what it hit; grounding can only be judged against the
    # text itself, so the evidence has to leave the loop with the answer.
    evidence: list[dict[str, str]] = field(default_factory=list)
    terminated_by: str = ""
    loop_count: int = 0
    llm_call_count: int = 0
    latency_ms: int = 0
    cost_usd: float = 0.0
    tokens_in: int = 0
    tokens_out: int = 0


def _record(outcome: Outcome, node: str, result: llm.LLMResult, **fields: Any) -> None:
    outcome.llm_call_count += 1
    outcome.cost_usd += result.cost_usd
    outcome.tokens_in += result.tokens_in
    outcome.tokens_out += result.tokens_out
    outcome.trajectory.append(
        {
            "node": node,
            **fields,
            "latency_ms": result.latency_ms,
            "tokens_in": result.tokens_in,
            "tokens_out": result.tokens_out,
        }
    )


def run(question: str, config: BehaviorConfig) -> Outcome:
    started = time.perf_counter()
    outcome = Outcome(answer="")

    decision, result = plan.run(question, config)
    _record(
        outcome,
        "plan",
        result,
        in_scope=decision.in_scope,
        needs_search=decision.needs_search,
        query=decision.query,
    )

    if not decision.in_scope:
        outcome.answer = (
            "I can only answer questions about Luma AI products and the Luma documentation. "
            f"{decision.refusal_reason or ''}".strip()
        )
        outcome.terminated_by = "refused_out_of_scope"
        return _finish(outcome, started)

    evidence: list[dict[str, str]] = []
    tried: list[str] = []
    seen_chunks: set[tuple[str, str]] = set()
    query = decision.query or question

    while decision.needs_search and outcome.loop_count < config.max_loops:
        outcome.loop_count += 1
        search_started = time.perf_counter()
        hits = search.search_docs(query)
        tried.append(query)

        fresh = [h for h in hits if (h["slug"], h["heading"]) not in seen_chunks]
        seen_chunks.update((h["slug"], h["heading"]) for h in fresh)
        evidence.extend(fresh)

        # `tool` is what the benchmark asserts on, and it is the same constant the
        # prompt's `#search_docs` reference resolves through. Reading the node
        # name instead would keep passing after a rename.
        outcome.trajectory.append(
            {
                "node": "search",
                "tool": search.TOOL_NAME,
                "query": query,
                "hits": len(hits),
                "new_hits": len(fresh),
                "articles": sorted({h["article_title"] for h in hits}),
                "latency_ms": int((time.perf_counter() - search_started) * 1000),
            }
        )

        reflection, result = reflect.run(question, evidence, tried, config)
        _record(
            outcome,
            "reflect",
            result,
            resolved=reflection.resolved,
            missing=reflection.missing,
            next_query=reflection.next_query,
        )
        if reflection.resolved:
            break

        next_query = (reflection.next_query or "").strip()
        # A reflect node that keeps asking for the same thing will happily burn
        # every remaining loop. Treat a repeat as "no progress" and stop early:
        # cheaper, and more honest than pretending the extra rounds helped.
        if not next_query or next_query.lower() in {t.lower() for t in tried}:
            outcome.trajectory.append({"node": "search", "skipped": "query_repeated"})
            break
        query = next_query

    sufficient = bool(evidence) and any(
        step.get("node") == "reflect" and step.get("resolved") for step in outcome.trajectory
    )
    answer, result = synthesize.run(question, evidence, config, sufficient)
    _record(outcome, "synthesize", result, mode="answer" if sufficient else "insufficient")

    outcome.answer = answer.strip()
    outcome.terminated_by = "answered" if sufficient else "exhausted"
    outcome.retrieved_articles = sorted({item["article_title"] for item in evidence})
    outcome.evidence = evidence
    outcome.citations = _cited(answer, evidence)
    return _finish(outcome, started)


def _cited(answer: str, evidence: list[dict[str, str]]) -> list[dict[str, str]]:
    """Citations ride along with the answer so the frontend never needs a corpus endpoint."""
    return [
        {"title": item["article_title"], "url": item["url"]}
        for item in {e["article_title"]: e for e in evidence}.values()
        if item["article_title"].lower() in answer.lower()
    ]


def _finish(outcome: Outcome, started: float) -> Outcome:
    outcome.latency_ms = int((time.perf_counter() - started) * 1000)
    return outcome
