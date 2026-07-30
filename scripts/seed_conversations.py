"""Ask the running server one question per terminal state, to source the seed fixture.

    uv run python scripts/seed_conversations.py        # needs the server up on :8000

The Conversation rows this produces are what `seed_demo.py export` picks up. They
have to come through the real HTTP path rather than being constructed by hand: a
hand-written row would not carry the version_id, config_hash and trajectory that
the whole product is about, and a fixture that lies about its own provenance is
worse than no fixture.

Throttled because the free tier allows 15 requests/minute and one question spends
three to five of them.
"""

import json
import sys
import time
import urllib.request

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"

# One per value of terminated_by. The Production tab's outcome column means nothing
# if every seeded row says "answered".
QUESTIONS = [
    ("What is a Skill in Luma and when should I create one?", "answered"),
    ("How much does a Luma subscription cost per month?", "exhausted"),
    ("Write me a Python function to reverse a linked list.", "refused_out_of_scope"),
]
PAUSE_SECONDS = 22


def ask(question: str) -> dict:
    request = urllib.request.Request(
        f"{BASE}/api/chat",
        json.dumps({"session_id": "seed-source", "question": question}).encode(),
        {"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request) as response:
        return json.load(response)


def main() -> None:
    ok = True
    for index, (question, expected) in enumerate(QUESTIONS):
        data = ask(question)
        hit = data["terminated_by"] == expected
        ok = ok and hit
        # The response carries version_label, not config_hash -- the hash is stored
        # on the row rather than returned. Fine here: the export reads the row.
        print(
            f"  [{'ok ' if hit else 'BAD'}] {data['terminated_by']:22} "
            f"{data['version_label']:14} ${data['cost_usd']:.6f}  {question[:44]}"
        )
        if index < len(QUESTIONS) - 1:
            time.sleep(PAUSE_SECONDS)

    print("\nnow run: uv run python scripts/seed_demo.py export")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
