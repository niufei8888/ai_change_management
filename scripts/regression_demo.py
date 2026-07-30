"""Drives the console's Simulation over HTTP with the regression config.

This is the acceptance check that matters most: BAD_SCOPE_V2 changes one field,
the answer still reads fine, cost and latency both drop, and every aggregate
metric says ship it. Only the fixed observations catch it.

Needs the server running:  uv run uvicorn server.main:app --port 8000

    uv run python scripts/regression_demo.py                # BAD_SCOPE_V2
    uv run python scripts/regression_demo.py active         # the live version
"""

import json
import sys
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from behavior_core.config import BAD_SCOPE_V2  # noqa: E402

BASE = "http://127.0.0.1:8000/api/console"


def call(path: str, payload: dict | None = None) -> dict:
    body = json.dumps(payload).encode() if payload is not None else None
    request = urllib.request.Request(
        BASE + path, data=body, headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(request) as response:
        return json.load(response)


def main() -> None:
    which = sys.argv[1] if len(sys.argv) > 1 else "bad-scope"
    if which == "active":
        active = next(v for v in call("/versions") if v["status"] == "active")
        config, label = active["config"], active["label"]
    else:
        config, label = BAD_SCOPE_V2.model_dump(), "bad-scope-v2"

    run_id = call("/simulate", {"config": config, "version_label": label})["run_id"]
    print(f"run {run_id} against {label} -- serial and throttled, expect 60-90s")

    while True:
        payload = call(f"/runs/{run_id}")
        run = payload["run"]
        if run["status"] != "running":
            break
        print(f"  {len(payload['results'])}/{run['case_total']} cases…")
        time.sleep(5)

    results = payload["results"]
    print(f"\nstatus={run['status']} config={run['config_hash']} ${run['total_cost_usd']:.6f}\n")
    for result in results:
        print("=" * 76)
        print(f"[{'PASS' if result['passed'] else 'FAIL'}] {result['case_id']}  persona={result['persona']}")
        print(f"  {result['answer'][:260]}")
        print(f"  terminated_by={result['terminated_by']} calls cost=${result['cost_usd']:.6f}")
        for name, check in result["observations"].items():
            print(f"    [{'ok ' if check['passed'] else 'BAD'}] {name}: {check['detail']}")
        for verdict in result["verdicts"]:
            print(f"    [{verdict['verdict']}] {verdict['policy']}: {verdict['reason'][:170]}")

    passed = sum(1 for r in results if r["passed"])
    print("=" * 76)
    print(f"{passed}/{len(results)} passed fixed observations")


if __name__ == "__main__":
    main()
