# Ask Luma + Driftline

Two things in one repo, deliberately: an AI product, and the system that manages changes to its behavior.

- **Ask Luma** (`/`) — a Q&A assistant that answers questions about Luma AI products using only the official documentation. Internally a ReAct loop: decide scope, search, check whether the evidence is enough, search again (max 3 rounds), then answer — or say plainly that the docs do not cover it. [apps/chatbot/README.md](apps/chatbot/README.md)
- **Driftline** (`/console`) — the console that introduces, evaluates and manages changes to that behavior. Edit the four versioned levers, try them on a single conversation, run them against a golden dataset, save as a version, activate. [apps/console/README.md](apps/console/README.md)

The second one is the point. Ask Luma exists to be the thing under management.

Start with [APPROACH.md](APPROACH.md) for what was built and why, what was left out, and what breaks first.

## Live

**<!-- RENDER_URL -->** (chatbot) · **<!-- RENDER_URL -->/console** (console)

Two things to expect, both consequences of a free hosting tier rather than of anything being broken:

- **The first request can take about a minute.** The instance sleeps after 15 minutes of no traffic. Render shows its own loading page while it wakes up.
- **The data resets.** A free instance loses its filesystem every time it sleeps, so the conversation history and benchmark runs you see are re-seeded from [`datasets/demo_seed.json`](datasets/demo_seed.json) on each cold start. They are real recorded runs, not fabricated rows, and seeded conversations are marked `seeded` in the Production tab. Anything you produce yourself survives until the next sleep.

Running it locally avoids both. See [design_step4_deploy.md](ai-discussion/design_step4_deploy.md) for why this tier was chosen anyway.

## Run it

```bash
docker compose up --build
```

Or without Docker:

```bash
uv sync
cp .env.example .env                     # then fill in your provider's key
uv run python -m ask_luma.cli init-db
uv run python scripts/seed_demo.py load  # optional: real pre-computed data to look at
uv run uvicorn server.main:app --reload --port 8000
```

- <http://localhost:8000> — the chatbot
- <http://localhost:8000/console> — the console

There is no frontend build step and the corpus is committed, so nothing needs to reach the internet except the model API.

**About the API key.** This was built and measured on Gemini (`gemini/gemini-3.1-flash-lite`, [Google AI Studio](https://aistudio.google.com/apikey)), which is not one of the keys this take-home provisions. `MODEL` also accepts `anthropic/…` and `openai/…` — the key check, price table and routing are all in place, but I had neither key and never ran them, so `.env.example` says "wired, not verified" rather than "supported" ([TO-31](ai-discussion/trade-offs.md)).

With no key at all, `scripts/seed_demo.py load` inserts real exported rows — two benchmark runs, one green baseline and one catching the regression — so the console is worth looking at before you spend a request.

## The one idea worth knowing

Behavior is a **versioned configuration** resolved on the critical path, not something compiled into a deploy. Four levers — one prompt per node in the ReAct loop, plus the tool description — are hashed into a `config_hash`, stored as a `Version` row, and looked up on every single request. That is what makes it possible to change behavior, evaluate the change, ship it, and roll it back without touching the code.

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
datasets/demo_seed.json  real rows exported from a live run, for a populated console
ai-discussion/           the full design record, in Chinese, including rejected approaches
```

`apps/chatbot` and `apps/console` never import each other. Both depend on `packages/agent`, which is what makes "the benchmark ran the same loop production runs" structurally true rather than a claim.

## Design record

Written in Chinese, and it is the honest version — it includes the approaches that did not work and the reasons.

- [ai-discussion/design_high_level.md](ai-discussion/design_high_level.md) — the whole product
- [ai-discussion/design_step1_ai_app.md](ai-discussion/design_step1_ai_app.md) — Ask Luma, including five attempts at a demo regression that all failed to reproduce
- [ai-discussion/design_step2_console_with_benchmark.md](ai-discussion/design_step2_console_with_benchmark.md) — Driftline
- [ai-discussion/design_step3_misc_and_wrap_up.md](ai-discussion/design_step3_misc_and_wrap_up.md) — the two signposted non-goals, and the delivery surface
- [ai-discussion/trade-offs.md](ai-discussion/trade-offs.md) — 21 numbered decisions, each with what it costs and what would overturn it, and an index of the five that carry the argument
