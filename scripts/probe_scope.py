"""Finds a `covered` question that is in scope for the baseline and out of scope for
BAD_SCOPE_V2.

The covered case has two jobs at once: prove the bot answers a well-documented
question, and be the case the known regression breaks. If the stricter scope rule
still lets the question through, the golden dataset has no teeth against the one
regression we can reproduce.

Only calls the plan node, so a candidate costs 2 requests instead of the 8-12 a
full case pair would. Matters because the free tier allows 15 per minute.

    uv run python scripts/probe_scope.py
"""

import sys
import time
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
load_dotenv()

from agent import corpus  # noqa: E402
from agent.graph import plan  # noqa: E402
from behavior_core.config import BAD_SCOPE_V2, BASELINE_V1  # noqa: E402

CANDIDATES = [
    "How do I keep a character looking the same across different shots?",
    "How should I work with the Luma agent to get better results?",
    "What is the best way to write prompts so my videos come out better?",
    "How do I avoid wasting credits while I iterate?",
    "What is a good workflow for going from a rough idea to a finished shot?",
    "How do I stop my character's face from changing between shots?",
    "What should I do when the generated motion is not what I described?",
]

PAUSE = 9  # two calls per candidate against a 15/minute ceiling


def main() -> None:
    corpus.load()
    print(f"{'in_scope under':>16}  baseline  strict   question")
    for question in CANDIDATES:
        baseline, _ = plan.run(question, BASELINE_V1)
        time.sleep(PAUSE)
        strict, _ = plan.run(question, BAD_SCOPE_V2)
        time.sleep(PAUSE)

        wanted = baseline.in_scope and not strict.in_scope
        print(
            f"{'USABLE' if wanted else '':>16}  "
            f"{str(baseline.in_scope):8}  {str(strict.in_scope):7}  {question}"
        )
        if not strict.in_scope:
            print(f"{'':16}  strict refusal: {strict.refusal_reason}")


if __name__ == "__main__":
    main()
