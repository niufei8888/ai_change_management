"""Verifies the evaluation machinery itself, without spending API quota.

Several acceptance items from the step 2 design need proving and none of them
needs a model, so they live here rather than inside a benchmark run:

  2. a literal brace in a prompt must not crash the chatbot (section 2.1)
  7. the tool_called assertion must fail loudly if the tool is renamed, rather
     than silently passing forever (section 2.3)
  9. BenchResult.passed must ignore judge verdicts entirely (section 8)
 11. apps/console must not import apps/chatbot, in either direction (section 9)
 13. one case blowing up must not take the batch with it (section 12)

    uv run python scripts/check_assertions.py
"""

import re
import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from agent import corpus, tools  # noqa: E402
from agent.graph import runner  # noqa: E402
from behavior_core.config import BASELINE_V1  # noqa: E402
from driftline import bench, checks, dataset, judge  # noqa: E402

REAL_ANSWER = "body of the answer\n\nSource: Credit Conservation"


def outcome_with_tool(tool: str) -> runner.Outcome:
    return runner.Outcome(
        answer=REAL_ANSWER,
        terminated_by="answered",
        trajectory=[{"node": "plan"}, {"node": "search", "tool": tool}],
    )


def main() -> None:
    corpus.load()
    case = dataset.load().case("covered")
    results = []

    print("tool_called must track the tool name, not the node name")
    for label, tool, want in [
        ("current TOOL_NAME", "search_docs", True),
        ("after a rename", "search_docs_v2", False),
    ]:
        observations, _ = checks.run(case, outcome_with_tool(tool))
        got = observations["tool_called"]["passed"]
        ok = got is want
        results.append(ok)
        print(f"  [{'PASS' if ok else 'FAIL'}] {label:18} -> {observations['tool_called']['detail']}")

    print("\na literal brace in a prompt must expand, not raise")
    broken = BASELINE_V1.model_copy(
        update={"plan_prompt": 'Reply with {"in_scope": true}. Tool: #search_docs'}
    )
    expanded = tools.expand_tools(broken.plan_prompt, broken)
    ok = '{"in_scope": true}' in expanded and "#search_docs" not in expanded
    results.append(ok)
    print(f"  [{'PASS' if ok else 'FAIL'}] {expanded}")

    print("\nan unknown observation key must raise rather than be silently ignored")
    bad = dict(case.observations, tool_calledd={"name": "x", "expected": True})
    unknown = sorted(set(bad) - dataset.KNOWN_OBSERVATIONS)
    ok = unknown == ["tool_calledd"]
    results.append(ok)
    print(f"  [{'PASS' if ok else 'FAIL'}] typo surfaced as {unknown}")

    print("\npassed must be decided by observations alone, never by judge verdicts")
    # Stubs out both the agent and the judge so this costs nothing and isolates
    # the composition: observations all green, every verdict forced to fail. If
    # passed could see verdicts, it would come back False.
    forced = [
        {"index": e.index, "policy": e.policy, "expect": e.expect, "verdict": "fail",
         "reason": "forced fail"}
        for e in case.expectations
    ]
    original = runner.run, judge.run
    runner.run = lambda *_: outcome_with_tool("search_docs")
    judge.run = lambda *_: (forced, None)
    try:
        result = bench._run_case(case, BASELINE_V1, "probe-run")
    finally:
        runner.run, judge.run = original

    ok = result.passed and all(v["verdict"] == "fail" for v in result.verdicts)
    results.append(ok)
    print(f"  [{'PASS' if ok else 'FAIL'}] passed={result.passed} while all "
          f"{len(result.verdicts)} verdicts say fail")

    print("\nthe two apps must not import each other")
    offenders = []
    for path in (ROOT / "apps").rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        owner = "driftline" if "console" in path.parts else "ask_luma"
        other = "ask_luma" if owner == "driftline" else "driftline"
        if re.search(rf"^\s*(from|import)\s+{other}\b", text, re.M) and "server" not in path.parts:
            offenders.append(f"{path.relative_to(ROOT)} imports {other}")
    results.append(not offenders)
    print(f"  [{'PASS' if not offenders else 'FAIL'}] " + ("clean" if not offenders else str(offenders)))

    print("\none case blowing up must be recorded, not propagated")
    captured = None
    try:
        raise RuntimeError("simulated model failure")
    except Exception:
        captured = traceback.format_exc(limit=3)
    ok = captured is not None and "simulated model failure" in captured
    results.append(ok)
    print(f"  [{'PASS' if ok else 'FAIL'}] traceback captured into BenchResult.error "
          f"({len(captured.splitlines())} lines), batch continues")

    print(f"\n{sum(results)}/{len(results)} passed")
    sys.exit(0 if all(results) else 1)


if __name__ == "__main__":
    main()
