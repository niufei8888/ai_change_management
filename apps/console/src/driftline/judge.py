"""Dynamic expectations: an LLM judging the hand-written criteria for one case.

Two limits are baked into how this is used, not papered over:

1. It runs on the same model as the chatbot, read from the same .env MODEL
   (TO-28). Simple, and one fewer key to manage -- but a model judging its own
   output is systematically lenient, and swapping MODEL silently invalidates
   every historical verdict. Production would pin a separate judge model, ideally
   from a different family.
2. It is single-sample, so it drifts (TO-12).

Both are why nothing here feeds BenchResult.passed. These verdicts explain; the
deterministic checks decide.
"""

from pydantic import BaseModel

from agent import llm
from agent.graph import runner
from driftline.dataset import Case

# Low temperature, not zero: the judge is advisory anyway, and pinning it to 0
# would only make the leniency more consistent, not less real.
JUDGE_TEMPERATURE = 0.0

JUDGE_SYSTEM = """You are evaluating one response from a documentation assistant called Ask Luma.

You will be given the user's persona, their question, the evidence the assistant retrieved, a
summary of what the assistant actually did, its final answer, and a numbered list of
expectations written by a human reviewer.

Return exactly one verdict per expectation, keyed by its index. For each:
- verdict is "pass" only if the answer clearly satisfies that expectation.
- verdict is "fail" if it does not, or if the answer is ambiguous about it.
- reason must quote or paraphrase the specific part of the answer you based the verdict on.
  Never write a generic reason like "the tone was fine" with nothing pointing at the text.

Judge only the listed expectations. Do not invent additional criteria, do not comment on
formatting, and do not reward or penalise length unless an expectation mentions it.

The action summary tells you what tools ran and how the turn ended. Use it as context: if
nothing was retrieved, an answer containing specific product details is not grounded, whatever
it sounds like."""


class ExpectationVerdict(BaseModel):
    index: int
    verdict: str  # "pass" | "fail"
    reason: str


class JudgeOutput(BaseModel):
    verdicts: list[ExpectationVerdict]


def _action_summary(outcome: runner.Outcome) -> str:
    """What the judge is told about the trajectory.

    The tool-call tag appears here even though a deterministic check already owns
    the verdict on it. Same fact, two roles: there it is the gate, here it is the
    context that lets a grounding verdict say why.
    """
    tools = [step["tool"] for step in outcome.trajectory if step.get("tool")]
    lines = [
        f"- tools called: {', '.join(tools) if tools else 'none'}",
        f"- search rounds: {outcome.loop_count}",
        f"- evidence chunks retrieved: {len(outcome.evidence)}",
        f"- turn ended as: {outcome.terminated_by}",
    ]
    return "\n".join(lines)


def _evidence_block(outcome: runner.Outcome) -> str:
    if not outcome.evidence:
        return "(nothing was retrieved)"
    return "\n\n".join(
        f"[{item['article_title']} > {item['heading']}]\n{item['text']}"
        for item in outcome.evidence
    )


def run(case: Case, outcome: runner.Outcome) -> tuple[list[dict], llm.LLMResult | None]:
    """One LLM call per case, regardless of how many expectations it has."""
    if not case.expectations:
        return [], None

    listed = "\n".join(
        f"{e.index}. [{e.policy}] {e.expect}" for e in case.expectations
    )
    user = (
        f"USER PERSONA\n{case.persona_note}\n\n"
        f"QUESTION\n{case.question}\n\n"
        f"EVIDENCE THE ASSISTANT RETRIEVED\n{_evidence_block(outcome)}\n\n"
        f"WHAT THE ASSISTANT DID\n{_action_summary(outcome)}\n\n"
        f"FINAL ANSWER\n{outcome.answer or '(empty)'}\n\n"
        f"EXPECTATIONS TO JUDGE\n{listed}"
    )

    output, result = llm.call_structured(
        JUDGE_SYSTEM, user, JudgeOutput, temperature=JUDGE_TEMPERATURE
    )

    by_index = {v.index: v for v in output.verdicts}
    verdicts = []
    for expectation in case.expectations:
        verdict = by_index.get(expectation.index)
        verdicts.append(
            {
                "index": expectation.index,
                "policy": expectation.policy,
                "expect": expectation.expect,
                # A missing verdict is reported as missing rather than defaulted
                # to pass or fail. Defaulting either way would invent a judgement
                # the judge never made.
                "verdict": verdict.verdict if verdict else "missing",
                "reason": verdict.reason if verdict else "judge returned no verdict for this",
            }
        )
    return verdicts, result
