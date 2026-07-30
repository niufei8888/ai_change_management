"""Checks whether a candidate question terminates the same way on repeated runs.

Half of choosing a golden case is picking a question whose *baseline* behavior is
stable. A case that flakes between `answered` and `exhausted` reports retrieval
variance as a behavior regression, which is worse than not testing it: it teaches
whoever reads the results to ignore red.

    uv run python scripts/probe_stability.py 3 "question here"
"""

import sys
import time
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
load_dotenv()

from agent import corpus  # noqa: E402
from agent.graph import runner  # noqa: E402
from behavior_core.config import BASELINE_V1  # noqa: E402
from driftline import checks, dataset  # noqa: E402

PAUSE = 22


def main() -> None:
    samples = int(sys.argv[1])
    question = " ".join(sys.argv[2:])
    corpus.load()
    case = dataset.load().case("covered")

    outcomes = []
    for index in range(samples):
        if index:
            time.sleep(PAUSE)
        outcome = runner.run(question, BASELINE_V1)
        observations, passed = checks.run(case, outcome)
        outcomes.append(outcome.terminated_by)
        print(f"\n--- sample {index + 1} -> {outcome.terminated_by}  {len(outcome.answer.split())} words")
        for name, check in observations.items():
            print(f"    [{'ok ' if check['passed'] else 'BAD'}] {name}: {check['detail']}")
        print(f"    covered-case fixed observations: {'PASS' if passed else 'FAIL'}")
        print(f"\n{outcome.answer}")

    print(f"\n{'=' * 74}\nterminated_by across {samples} samples: {outcomes}")
    print("stable:", len(set(outcomes)) == 1)


if __name__ == "__main__":
    main()
