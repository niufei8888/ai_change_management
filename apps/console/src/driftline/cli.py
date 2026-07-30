"""Run the benchmark from a terminal, before any frontend exists.

    uv run python -m driftline.cli dataset            # parse and print, no LLM calls
    uv run python -m driftline.cli bench              # active version
    uv run python -m driftline.cli bench bad-scope    # the regression this exists to catch

The design's checkpoint: bench and judge must work here first, so that a red
result is unambiguously the chatbot's behavior and not a fetch bug in the UI.
"""

import sys

from dotenv import load_dotenv

load_dotenv()

from agent import corpus  # noqa: E402
from behavior_core import config_client  # noqa: E402
from behavior_core.config import BAD_SCOPE_V2, BASELINE_V1, BehaviorConfig  # noqa: E402
from behavior_core.db import init_db  # noqa: E402
from driftline import bench, dataset  # noqa: E402

CONFIGS: dict[str, tuple[str, BehaviorConfig | None]] = {
    "active": ("active version from the database", None),
    "baseline": ("BASELINE_V1 constant", BASELINE_V1),
    "bad-scope": ("BAD_SCOPE_V2 -- the over-refusal regression", BAD_SCOPE_V2),
}


def cmd_dataset() -> None:
    data = dataset.load()
    print(f"dataset v{data.version} hash={data.hash} cases={len(data.cases)}\n")
    for persona, note in data.personas.items():
        print(f"  persona {persona}: {note}")
    for case in data.cases:
        print(f"\n  [{case.id}] persona={case.persona} policies={','.join(case.policies)}")
        print(f"    Q: {case.question}")
        print("    fixed observations:")
        for name, spec in case.observations.items():
            print(f"      {name} = {spec}")
        print("    dynamic expectations:")
        for expectation in case.expectations:
            print(f"      {expectation.index} [{expectation.policy}] {expectation.expect}")


def cmd_bench(which: str) -> None:
    if which not in CONFIGS:
        raise SystemExit(f"unknown config {which!r}, pick one of {sorted(CONFIGS)}")

    init_db()
    corpus.load()
    label, config = CONFIGS[which]
    if config is None:
        resolved = config_client.resolve("cli")
        config, label = resolved.config, resolved.version_label

    print(f"running 3 cases against {which} ({label}) hash={config.config_hash()}")
    print("serial with throttling, expect 60-90s\n")
    _report(bench.run_sync(config, version_label=which))


def _report(payload: dict) -> None:
    run = payload["run"]
    blocking = [r for r in payload["results"]]
    passed = sum(1 for r in blocking if r["passed"])

    for result in blocking:
        mark = "PASS" if result["passed"] else "FAIL"
        flags = " (cached)" if result["cached"] else ""
        print(f"{'=' * 78}\n[{mark}] {result['case_id']}  persona={result['persona']}{flags}")
        if result["error"]:
            print(f"  ERROR\n{result['error']}")
            continue

        print(f"  Q: {result['question']}")
        print(f"\n{result['answer']}\n")
        print("  fixed observations (blocking):")
        for name, check in result["observations"].items():
            print(f"    [{'ok ' if check['passed'] else 'BAD'}] {name}: {check['detail']}")
        print("  dynamic expectations (advisory, single sample):")
        for verdict in result["verdicts"]:
            print(f"    [{verdict['verdict']}] {verdict['policy']}: {verdict['reason']}")
        print(
            f"  {result['terminated_by']}  {result['latency_ms']}ms  ${result['cost_usd']:.6f}"
        )

    print(f"\n{'=' * 78}")
    print(
        f"{passed}/{len(blocking)} cases passed their fixed observations  "
        f"model={run['model']}  ${run['total_cost_usd']:.6f}"
    )
    print(f"run={run['id']} config={run['config_hash']} dataset={run['dataset_hash']}")
    sys.exit(0 if passed == len(blocking) else 1)


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    command = sys.argv[1]

    if command == "dataset":
        cmd_dataset()
    elif command == "bench":
        cmd_bench(sys.argv[2] if len(sys.argv) > 2 else "active")
    else:
        raise SystemExit(f"unknown command {command!r}\n{__doc__}")


if __name__ == "__main__":
    main()
