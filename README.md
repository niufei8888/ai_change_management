# Ask Luma + Driftline

Two things in one repo, deliberately: an AI product, and the system that manages changes to its behavior.

- **Ask Luma** (`/`) — a Q&A assistant that answers questions about Luma AI products using only the official documentation. Internally a ReAct loop: decide scope, search, check whether the evidence is enough, search again (max 3 rounds), then answer — or say plainly that the docs do not cover it. [apps/chatbot/README.md](apps/chatbot/README.md)
- **Driftline** (`/console`) — the console that introduces, evaluates and manages changes to that behavior. Edit the six versioned levers, try them on a single conversation, run them against a golden dataset, save as a version, activate. [apps/console/README.md](apps/console/README.md)

The second one is the point. Ask Luma exists to be the thing under management.

## Run it

```bash
uv sync
cp .env.example .env                     # then fill in GEMINI_API_KEY
uv run python -m ask_luma.cli init-db
uv run uvicorn server.main:app --reload --port 8000
```

- <http://localhost:8000> — the chatbot
- <http://localhost:8000/console> — the console

Or `docker compose up --build`. There is no frontend build step, and the corpus is committed, so nothing needs to reach the internet except the model API.

## The one idea worth knowing

Behavior is a **versioned configuration** resolved on the critical path, not something compiled into a deploy. Six levers — three prompts, the tool description, temperature, and the loop cap — are hashed into a `config_hash`, stored as a `Version` row, and looked up on every single request. That is what makes it possible to change behavior, evaluate the change, ship it, and roll it back without touching the code.

Evaluation splits every golden case into two halves that are treated very differently:

- **fixed observations** — facts about what actually happened, read off the trajectory, deterministic, **blocking**
- **dynamic expectations** — hand-written judgements about what the answer should be like, scored by an LLM judge, non-deterministic and (sharing the evaluated model) systematically lenient, **advisory**

`BenchResult.passed` never reads the judge's verdicts. The distinction lives in the code, not just in the docs.

## Layout

```
packages/behavior_core   config, versions, tables, on-the-critical-path resolution
packages/agent           the ReAct kernel and the tool registry -- shared by both apps
apps/chatbot             Ask Luma: serving surface
apps/console             Driftline: control surface
apps/server              the only module that imports both, one process hosts both
corpus/                  39 articles, fetched at build time, committed
datasets/golden.yaml     2 personas, 3 golden cases
ai-discussion/           the full design record, in Chinese, including rejected approaches
```

`apps/chatbot` and `apps/console` never import each other. Both depend on `packages/agent`, which is what makes "the benchmark ran the same loop production runs" structurally true rather than a claim.

## Design record

Written in Chinese, and it is the honest version — it includes the approaches that did not work and the reasons.

- [ai-discussion/design_high_level.md](ai-discussion/design_high_level.md) — the whole product
- [ai-discussion/design_step1_ai_app.md](ai-discussion/design_step1_ai_app.md) — Ask Luma, including five attempts at a demo regression that all failed to reproduce
- [ai-discussion/design_step2_console_with_benchmark.md](ai-discussion/design_step2_console_with_benchmark.md) — Driftline
- [ai-discussion/trade-offs.md](ai-discussion/trade-offs.md) — 30 numbered decisions, each with what it costs and what would overturn it
