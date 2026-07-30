"""The only test in the project (TO-23).

Not a unit test suite: it exercises the four behaviors that step 2 is built on
top of, prints the trajectory, and lets you read whether the product actually
behaves. Regression protection is step 2's job -- golden dataset plus judge is
this project's version of a test suite.

    uv run python scripts/smoke.py
"""

import json
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
load_dotenv()

from ask_luma import corpus  # noqa: E402
from ask_luma.graph import runner  # noqa: E402
from behavior_core.config import BAD_SCOPE_V2, BASELINE_V1  # noqa: E402
from behavior_core.db import init_db  # noqa: E402

CASES = [
    ("covered by the docs", "What is a Skill in Luma and when should I create one?", "answered"),
    ("not in the docs", "How much does a Luma subscription cost per month?", "exhausted"),
    ("nothing to do with Luma", "Write a Python function to reverse a linked list.",
     "refused_out_of_scope"),
]

# The free tier allows 15 requests/minute and one question costs 3-5 of them, so
# a back-to-back run trips the limit and spends its time in backoff instead. This
# is a smoke script, not a benchmark; waiting is cheaper than retrying.
PAUSE_SECONDS = 25


def show(label: str, question: str, outcome: runner.Outcome, expected: str | None) -> bool:
    ok = expected is None or outcome.terminated_by == expected
    mark = "PASS" if ok else "FAIL"
    print(f"\n{'=' * 78}\n[{mark}] {label}\n  Q: {question}")
    print(f"\n{outcome.answer}\n")
    print(
        f"  terminated_by={outcome.terminated_by}"
        + (f" (expected {expected})" if expected else "")
        + f"  loops={outcome.loop_count}  llm_calls={outcome.llm_call_count}"
        f"  {outcome.latency_ms}ms  ${outcome.cost_usd:.6f}"
    )
    if outcome.citations:
        print(f"  citations: {[c['title'] for c in outcome.citations]}")
    for step in outcome.trajectory:
        print("    " + json.dumps(step, default=str))
    return ok


def main() -> None:
    # `smoke.py regression` runs only the last check. Handy while iterating on it
    # without spending the free tier's 15 requests/minute on cases that pass.
    only_tool = len(sys.argv) > 1 and sys.argv[1] == "regression"

    init_db()
    corpus.load()
    print(f"corpus: hash={corpus.stats()[0]} articles={corpus.stats()[1]} chunks={corpus.stats()[2]}")

    results, outcomes = [], {}
    if not only_tool:
        for label, question, expected in CASES:
            outcomes[question] = runner.run(question, BASELINE_V1)
            results.append(show(label, question, outcomes[question], expected))
            time.sleep(PAUSE_SECONDS)

    # The regression step 2 exists to catch. One field changes, the answer still
    # reads fine, and cost and latency both drop -- so every aggregate metric
    # says ship it. Only the trajectory shows what happened.
    #
    # Checked here rather than in step 2 on purpose: the original plan hung this
    # demo on tool_description and it turned out not to reproduce at all (see
    # design_step1_ai_app.md 14.1). Finding that out during a demo would be bad.
    # A legitimate, well-documented question that names no product or feature, so
    # the stricter scope rule refuses it.
    question = "How should I work with the Luma agent to get better results?"
    baseline = outcomes.get(question) or runner.run(question, BASELINE_V1)
    time.sleep(PAUSE_SECONDS)
    candidate = runner.run(question, BAD_SCOPE_V2)

    # Asserts only the candidate's side. The baseline flakes between `answered`
    # and `exhausted` on this question depending on which query the planner picks,
    # so "baseline answered AND candidate refused" would be a flaky assertion.
    # That flakiness is itself the argument for step 2 running each golden case
    # several times instead of trusting one sample -- see 14.1.
    refused = candidate.terminated_by == "refused_out_of_scope"
    cheaper = candidate.cost_usd < baseline.cost_usd
    print(f"\n{'=' * 78}\n[{'PASS' if refused and cheaper else 'FAIL'}] tightening the scope rule "
          "refuses a question the docs answer well")
    for name, outcome in (("baseline ", baseline), ("bad-scope", candidate)):
        print(f"  {name}  terminated_by={outcome.terminated_by:20} loops={outcome.loop_count}"
              f"  calls={outcome.llm_call_count}  ${outcome.cost_usd:.6f}  {outcome.latency_ms}ms")
    print(f"  {baseline.cost_usd / max(candidate.cost_usd, 1e-9):.0f}x cheaper, "
          f"{baseline.latency_ms / max(candidate.latency_ms, 1):.0f}x faster "
          "-- which is why aggregate metrics would wave it through")
    print(f"\n  baseline answer:\n{baseline.answer}\n\n  bad-scope answer:\n{candidate.answer}\n")

    results.append(refused and cheaper)
    print(f"\n{'=' * 78}\n{sum(results)}/{len(results)} passed")
    sys.exit(0 if all(results) else 1)


if __name__ == "__main__":
    main()
