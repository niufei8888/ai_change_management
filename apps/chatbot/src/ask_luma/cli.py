"""Debug entry points that do not need a browser.

    uv run python -m ask_luma.cli init-db
    uv run python -m ask_luma.cli search "share a skill"
    uv run python -m ask_luma.cli ask "What is a Skill in Luma?"
    uv run python -m ask_luma.cli models
"""

import json
import sys

from dotenv import load_dotenv

load_dotenv()

from ask_luma import corpus, llm, search  # noqa: E402
from ask_luma.graph import runner  # noqa: E402
from behavior_core import config_client  # noqa: E402
from behavior_core.db import init_db  # noqa: E402


def cmd_init_db() -> None:
    init_db()
    print("tables created, v1-baseline seeded")


def cmd_search(query: str) -> None:
    corpus.load()
    hits = search.search_docs(query)
    print(f"{len(hits)} hits for {query!r}\n")
    for hit in hits:
        print(f"  {hit['article_title']} > {hit['heading']}")
        print(f"    {hit['text'][:160].strip()}...\n")


def cmd_ask(question: str) -> None:
    corpus.load()
    resolved = config_client.resolve("cli")
    outcome = runner.run(question, resolved.config)

    print(f"\n{outcome.answer}\n")
    print("-" * 70)
    print(
        f"version={resolved.version_label} arm={resolved.arm} "
        f"terminated_by={outcome.terminated_by} loops={outcome.loop_count} "
        f"llm_calls={outcome.llm_call_count} {outcome.latency_ms}ms ${outcome.cost_usd:.6f}"
    )
    for step in outcome.trajectory:
        print("  " + json.dumps({k: v for k, v in step.items() if k != "text"}, default=str))


def cmd_models() -> None:
    """List the model ids this key can actually use, so MODEL can be pinned to a real one."""
    import os

    import httpx

    response = httpx.get(
        "https://generativelanguage.googleapis.com/v1beta/models",
        headers={"x-goog-api-key": os.environ["GEMINI_API_KEY"]},
        timeout=30,
    )
    response.raise_for_status()
    for model in response.json()["models"]:
        if "generateContent" in model.get("supportedGenerationMethods", []):
            print(model["name"].removeprefix("models/"))


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    command, args = sys.argv[1], sys.argv[2:]

    if command == "init-db":
        cmd_init_db()
    elif command == "models":
        cmd_models()
    elif command == "search":
        cmd_search(" ".join(args))
    elif command == "ask":
        cmd_ask(" ".join(args))
    else:
        raise SystemExit(f"unknown command {command!r}\n{__doc__}")


if __name__ == "__main__":
    main()
