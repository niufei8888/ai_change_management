# Ask Luma

A Q&A service that answers questions about Luma AI products and nothing else. Internally it is a ReAct loop: decide whether the question is in scope and whether to search, plan the query, search the local docs, decide whether the evidence is enough, search again if not (three rounds at most), and only then answer. If three rounds are not enough it says plainly that it does not know.

Design doc: [ai-discussion/design_step1_ai_app.md](../../ai-discussion/design_step1_ai_app.md) (Chinese)

This service is the thing being managed. The system that manages changes to it lives in [`apps/console/`](../console/README.md) (Driftline). **This service does not depend on `apps/console`.** Both depend on `packages/agent` (the same ReAct kernel) and `packages/behavior_core` (config and tables).

The kernel is in `packages/agent` rather than in this directory because the console's benchmark has to run **the same code** the chatbot serves users with. Keeping the kernel here would force the console to import the chatbot, which would make the control plane depend on the serving plane.

Every command below runs from the **repository root**, not from this directory. The whole monorepo has one `pyproject.toml` and one `.venv`.

---

## Prerequisites

- [uv](https://docs.astral.sh/uv/) — it provisions its own Python 3.12+ and leaves your system Python alone
- An API key for one provider (see below)

> This was built and measured on **Gemini** ([Google AI Studio](https://aistudio.google.com/apikey), the free tier is enough), which is not one of the keys the take-home's `.env.example` provisions. Anthropic and OpenAI are wired up as alternatives but were never run — see [TO-31](../../ai-discussion/trade-offs.md) and the comments in `.env.example`. The process refuses to start if `MODEL` names a provider whose key is missing, and says which variable it wants.

The frontend is a single static file with **no build step**, so Node is not needed ([TO-22](../../ai-discussion/trade-offs.md)).

## The corpus has to be in place first

The service loads `corpus/` into memory at startup and **fails to start if it is missing**. That is deliberate: booting with an empty index presents as "the model says it doesn't know to everything", which looks like a prompt or model problem and sends you debugging in entirely the wrong direction.

The fetched corpus (39 articles) is committed. To re-fetch:

```bash
uv run python scripts/fetch_corpus.py            # only what is missing
uv run python scripts/fetch_corpus.py --force    # all of it
```

Fetching is a **one-off build-time action**. At runtime the service only reads local files and never reaches lumalabs.ai.

---

## Option 1: native Python (best for debugging)

```bash
uv sync                                  # create .venv and install
cp .env.example .env                     # then fill in your provider's key

uv run python -m ask_luma.cli init-db    # create tables, make BASELINE_V1 active
uv run python scripts/seed_demo.py load  # optional: real pre-computed data to look at

# chatbot only
uv run uvicorn ask_luma.main:app --reload --port 8000

# chatbot + console in one process (recommended, see apps/console/README.md)
uv run uvicorn server.main:app --reload --port 8000
```

Open <http://localhost:8000>; the console is at <http://localhost:8000/console>.

`init-db` is **idempotent and self-healing**: it guarantees the `config_hash` of `BASELINE_V1` in the code is the one marked active in the database. Re-run it after editing a prompt constant in `config.py` — older rows become `archived` rather than being deleted. "The active version's hash matches no config in the source" is precisely the kind of invisible drift this project exists to remove.

To change the frontend, edit `apps/chatbot/web/index.html` and reload the browser. The visual tokens are the `:root` block at the top of the file, following Anthropic's Claude: warm paper background, serif headings over sans-serif body, terracotta as the only accent, and it follows the system dark mode.

While a request is in flight the UI shows one generic thinking indicator and **not what each step is doing** ([TO-17](../../ai-discussion/trade-offs.md)). The full trajectory is available in a collapsible panel once the answer arrives.

### Debugging entry points

```bash
# ask one question and print the whole trajectory, no browser
uv run python -m ask_luma.cli ask "What is a Skill in Luma?"

# exercise retrieval only, spends no API quota
uv run python -m ask_luma.cli search "share a skill with teammates"

# list the models this key can actually reach, to pick a pinned version for MODEL
uv run python -m ask_luma.cli models

# per-node logging
LOG_LEVEL=debug uv run uvicorn server.main:app --reload --port 8000
```

### The only test

```bash
uv run python scripts/smoke.py
```

**There are no unit tests** ([TO-22](../../ai-discussion/trade-offs.md)). This is a demo, not a system to maintain, and the entire subject of the project is using the step 2 benchmark to catch AI behavior regressions — the golden dataset plus the judge is this project's version of a regression suite. See [apps/console/README.md](../console/README.md) for how to run it.

`smoke.py` exercises four real paths and prints the trajectories: a question the docs cover, a question they do not, a question with nothing to do with Luma, and **a legitimate question being refused after the `in_scope` rule is tightened**. That last one is the premise of step 2's whole headline demo, which is why it is verified here in step 1 — **the demo was originally going to use `tool_description`, and all five attempts at that failed to reproduce**. See [design_step1_ai_app.md §14.1](../../ai-discussion/design_step1_ai_app.md).

To run just that last case and save quota: `uv run python scripts/smoke.py regression`

### Breakpoints

Under `--reload` you can attach an editor debugger directly. Three places are worth a breakpoint if you want to watch the ReAct loop:

- `packages/agent/graph/runner.py` — loop entry/exit conditions and the cap
- `packages/agent/graph/reflect.py` — the `resolved` decision, which is what determines whether there is another round
- `packages/agent/search.py` — scoring, and the threshold below which it returns nothing

The code is **let-it-fail** ([TO-22](../../ai-discussion/trade-offs.md)): errors are not caught, and a problem crashes where it happens with a full traceback. There are exactly three pieces of error handling in the project — `tenacity` retrying 429 / timeout / 5xx in `llm.py`, the route boundary in `main.py` that writes a `Conversation` carrying `error` and returns 502, and per-case isolation in the console's benchmark runner. **When debugging you never have to hunt for the place that swallowed an exception, because outside those three nothing does.**

---

## Option 2: Docker Compose (best for handing it to someone)

```bash
cp .env.example .env                     # then fill in your provider's key
docker compose up --build
```

Open <http://localhost:8000>.

Single-stage pure Python image, **one uvicorn process**. No Node stage because the frontend has no build step, and the corpus is baked into the image so the running container needs no network access at all. Tables are created and the v1 baseline is written on first start.

`./data` is mounted as the SQLite directory, so data survives a rebuild. If you have no `.env`, the container still starts and then exits with a message naming the environment variable it wants — a missing credential should not present as a missing file.

```bash
docker compose logs -f      # follow logs
docker compose down         # stop; ./data is kept
```

---

## Configuration

There are two kinds of key in `.env`, and the distinction matters.

### System-level settings (shared by every version; changing one replaces the whole baseline)

| Key | Notes |
| --- | --- |
| `MODEL` | `gemini/…`, `anthropic/…` or `openai/…`. Give a **pinned version**, not a `-latest` alias — aliases drift, and the drift masquerades as "the prompt I edited changed the behavior". |
| `GEMINI_API_KEY` / `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` | Whichever one `MODEL` needs. Never commit it. |
| `DB_PATH` | Defaults to `./data/app.db`. |
| `LOG_LEVEL` | `info` / `debug`. |

### Behavior configuration — the four versioned levers, **not in `.env`**

`plan_prompt`, `reflect_prompt`, `synthesize_prompt`, `tool_description`

These live in the `Version` table and are resolved **on every request** through `config_client` in `packages/behavior_core`. That is what makes it possible to switch versions without a deploy, ramp a percentage of traffic, and roll back instantly — everything step 2 does rests on it.

Temperature and the loop cap used to be levers and were cut ([TO-06](../../ai-discussion/trade-offs.md)). They are now constants — `TEMPERATURE` in `packages/agent/llm.py`, `MAX_LOOPS` in `packages/agent/graph/runner.py` — and deliberately not environment variables, because a knob that quietly differs between two machines makes their evaluation results incomparable.

To change behavior, change the version row (the console gives that a UI). **Do not hardcode prompts.** `BASELINE_V1` in `packages/behavior_core/config.py` is only the seed written on first start; it is not what gets read at runtime.

---

## Endpoints

| Method | Path | Notes |
| --- | --- | --- |
| `POST` | `/api/chat` | `{session_id, question}` → answer, citations, full trajectory metadata |
| `GET` | `/api/conversations` | filtered by `session_id` (the frontend restoring history) or `tag` / `arm` (experiment slices) |
| `GET` | `/api/health` | includes `corpus_hash`, `article_count`, the active version |

Three, and no debug endpoints. **The corpus is not exposed** — retrieved articles are context for the model, not a directory for users to browse; citations come back with the `/api/chat` response instead ([TO-17](../../ai-discussion/trade-offs.md)).

The `POST /api/chat` response carries `terminated_by` (`answered` / `exhausted` / `refused_out_of_scope`), `loop_count`, `llm_call_count` and a per-node `trajectory`. The frontend's "how this answer was produced" panel is rendering exactly that.

## Troubleshooting

**Startup complains the corpus is missing** — run `uv run python scripts/fetch_corpus.py`.

**Startup complains about a key** — `MODEL` names a provider whose key is unset. The message says which variable; see `.env.example`.

**A `Source:` line names an article that does not exist** — check that `corpus/index.json` agrees with `corpus/*.md`. `index.json` is the single source of truth for what counts as a real article title.

**Lots of 429s** — free-tier rate limiting. The ReAct loop spends 3–5 LLM calls per question, so it burns quota faster than a single-shot Q&A. Wait for the window, or test one question with `cli ask` instead of running the whole smoke script.

**Every answer is "I don't know"** — check whether `/api/health` reports `article_count: 0` (corpus did not load); then look at `terminated_by` in the trajectory. If it is always `exhausted`, either the retrieval threshold is too strict or `reflect` is being too demanding.

**What should `MODEL` be** — run `uv run python -m ask_luma.cli models` to see what your key can reach.
