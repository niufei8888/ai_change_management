# Driftline

The console for introducing, evaluating and managing changes to Ask Luma's behavior. The left pane edits the four versioned levers — one prompt per node in the ReAct loop, plus the tool description. The right pane has three tabs: **Conversation** runs one turn with the draft config and lays out every intermediate state, **Simulation** runs the golden dataset against it, and **Production** shows real traffic with the behavior version that produced each answer.

Design docs (Chinese): [design_step2_console_with_benchmark.md](../../ai-discussion/design_step2_console_with_benchmark.md) for the console and the benchmark, [design_step3_misc_and_wrap_up.md](../../ai-discussion/design_step3_misc_and_wrap_up.md) for the two signposted non-goals below.

The thing being managed is `apps/chatbot`. **This service does not import it** — both depend on `packages/agent` (the same ReAct kernel) and `packages/behavior_core` (config, versions, tables). That is not tidiness: the benchmark has to run the same code the chatbot serves users with, or "the benchmark measures production behavior" degrades from a structural fact into a claim.

Every command runs from the **repository root**.

---

## Start it

```bash
uv sync
uv run python -m ask_luma.cli init-db          # create tables, make BASELINE_V1 active
uv run python scripts/seed_demo.py load        # optional: real pre-computed runs to look at
uv run uvicorn server.main:app --reload --port 8000
```

- The console: <http://localhost:8000/console>
- The chatbot it manages: <http://localhost:8000/>

`server.main` is the only module that imports both apps ([TO-08](../../ai-discussion/trade-offs.md)). **One process buys something real**: `config_client`'s five-second cache lives in process memory, so an Activate in the console invalidates the exact cache the chatbot reads and the next request picks up the new version immediately. Two processes also work, with up to five seconds of lag.

Running `seed_demo.py load` is worth it on a fresh database. It inserts real exported rows — two benchmark runs (a green baseline and the regression being caught), a few conversations covering all three terminal states, and the versions they refer to. Without an API key it is the only way to see a populated console; with one, it saves 80 seconds and a chunk of the rate limit before you have anything to look at. Seeded conversations are marked in the Production tab so canned data is never mistaken for something you just produced.

## Two kinds of assertion

A golden case splits in half, and that split is the skeleton of the whole evaluation:

| | fixed observation | dynamic expectation |
| --- | --- | --- |
| what it is | a fact about what actually happened | a judgement about what the answer should be like |
| who decides | a deterministic check reading the trajectory and output, no LLM | an LLM judge |
| reproducible | yes | no, it wobbles ([TO-10](../../ai-discussion/trade-offs.md)) |
| gating | **blocking** | **advisory**, labelled "single sample" in the UI |

`BenchResult.passed` is decided **by fixed observations alone; the code never reads `verdicts`**. The judge is the same model as the thing being evaluated ([TO-05](../../ai-discussion/trade-offs.md)), so it both wobbles and is systematically lenient about its own output. A signal like that must not be able to turn a run green.

The judge **can see** the tool-call tag and `terminated_by`, but does not decide them. It gets them so its semantic judgement has something to stand on — so it can say "this sentence has no source, because nothing was retrieved in that round". The same fact, gating in one place and explanatory in the other.

## It runs without a browser

```bash
uv run python -m driftline.cli dataset          # parse and print the dataset, zero API calls
uv run python -m driftline.cli bench            # the active version
uv run python -m driftline.cli bench baseline   # BASELINE_V1 from the code
uv run python -m driftline.cli bench bad-scope  # BAD_SCOPE_V2, the reason this benchmark exists
```

A checkpoint from the design: `bench.py` and `judge.py` **had to work from the command line before any frontend existed**, so that a red result is unambiguously the chatbot's behavior and never a fetch bug in the UI.

```bash
# spends no quota; checks the assertion machinery itself: does a tool rename get
# caught, does a literal { crash, can a verdict contaminate passed, do the two apps
# import each other, does one case blowing up take the batch with it
uv run python scripts/check_assertions.py

# drive a Simulation of the regression over HTTP (needs the server running)
uv run python scripts/regression_demo.py
```

## The rate limit is a constraint, not an optimisation

The free tier allows **15 requests per minute**. One full Simulation is 3 cases × (3–5 chatbot calls + 1 judge call) = **12–18 requests**, which sits right against the ceiling. So the runner is **serial and throttled** (20 seconds between cases) and a run takes 50–80 seconds. Concurrency would not be faster here; it would just spend the time in backoff.

Two mitigations:

- **Result caching**, keyed on `config_hash` + `dataset_hash` + `corpus_hash` + `case_id`. Re-running the same config is instant and free. `corpus_hash` has to be in the key — re-fetching the corpus changes what retrieval returns, and without it the cache would pass off behavior under the old corpus as current behavior.
- **Per-case error isolation.** This is the third and last piece of error handling in the project (an explicit exception to [TO-22](../../ai-discussion/trade-offs.md)): a case that blows up is recorded as that case's `BenchResult.error` and the batch continues. Having the first case's crash also hide the other two results is much worse than one red line.

## `#search_docs`

Prompts refer to tools as `#search_docs`, expanded by `expand_tools()` in `packages/agent/tools.py` into the current value of the `tool_description` lever. Typing `#` in the editor opens autocomplete, and an existing mention renders as a chip in the preview below showing what it expands to.

It replaced a `{tool_description}` placeholder: once a prompt is free text in a UI, an author typing a literal `{` makes `str.format()` raise `KeyError` inside `plan.run()` — several layers away from anything they touched. See [TO-26](../../ai-discussion/trade-offs.md).

The tool name is defined in exactly one place, `TOOL_NAME` in `packages/agent/search.py`, and three things have to agree: the mention in the prompt, the `tool` field on the search node in the trajectory, and `tool_called.name` in `datasets/golden.yaml`. The assertion reads the `tool` field and **not** the `node` name — reading the node name would make the assertion pass silently forever after a rename, which is worse than having no assertion because it manufactures confidence.

## The dataset

`datasets/golden.yaml`, a file rather than a table ([TO-13](../../ai-discussion/trade-offs.md)). The dataset is an **input**: changing an assertion changes the standard the product is held to, so it has to go through code review and has to be diffable. In a database it becomes the hiding place for "who quietly loosened a check, and when".

The parser recognises exactly 7 observation keys and **raises on anything else**. A misspelled key that is silently ignored is an assertion that does nothing — "written but not running" is more dangerous than not written.

The wording of the `covered` case was selected with `scripts/probe_scope.py` and `scripts/probe_stability.py` rather than written by hand. The reason is in [TO-29](../../ai-discussion/trade-offs.md) and in the YAML comments: the first hand-written wording let the regression walk past the entire dataset unnoticed.

## Endpoints

All under `/api/console`.

| Method | Path | Notes |
| --- | --- | --- |
| `GET` | `/versions` | version list (active / draft / archived) with the full config |
| `POST` | `/versions` | save the draft as a new version |
| `POST` | `/versions/{id}/activate` | 100% switch plus `config_client.invalidate()` |
| `GET` | `/tools` | the data behind `#` autocomplete |
| `GET` | `/dataset` | personas, cases, observations, expectations in full |
| `POST` | `/playground/chat` | body carries the whole config; returns answer, trajectory, evidence, expanded prompts |
| `POST` | `/simulate` | body carries the whole config; starts a BackgroundTask, returns `run_id` |
| `GET` | `/runs/{id}` | one run's status plus the BenchResults finished so far (the frontend polls this) |
| `GET` | `/runs` | past runs |
| `GET` | `/health` | model, `corpus_hash`, `dataset_hash`, case count, `TOOL_REGISTRY` |

The Production tab reads `GET /api/conversations`, which belongs to the chatbot. That is not the boundary violation it looks like: the rule is about Python imports, and one process serves both apps on one origin, so a page fetching an HTTP endpoint has not crossed anything.

**Playground conversations are not written to the `Conversation` table.** That table means real traffic; mixing experiments into it makes "how is this version doing in production" permanently unanswerable.

Polling rather than SSE: a run writes one row per case as it finishes, so polling gets per-case progress for free ([TO-17](../../ai-discussion/trade-offs.md) reached the same conclusion for `/chat`).

## Two things deliberately not built

Both are visible in the UI rather than left as blank space, because blank space and a deliberate omission look identical to someone reading the screen.

**Gradual rollout has no control surface.** Activate is a **100% switch**. The runtime for splitting traffic, however, is already on the request path and runs on every single request: `config_client.resolve()` buckets by a salted hash of `session_id`, compares against `rollout_pct`, and stamps `arm` and `experiment_tag` onto both the response and the stored conversation. What is missing is a way to create an `Experiment` row and a ramp policy — health thresholds, a step schedule, an auto-rollback trigger. The left pane shows the controls that would drive it, disabled.

**Production traffic cannot be sliced by tag.** `GET /api/conversations` already accepts `?tag=` and `?arm=`, and `experiment_tag` is indexed, so the query path exists and is what the Production tab reads through. Not built on top of it: filtering and search by tag, a baseline-vs-candidate comparison, promoting a production conversation into `datasets/golden.yaml` as a new case, and re-running the judge over a tagged slice on a schedule with a violation-rate threshold. For that last one the missing pieces are the schedule and the threshold — not the judge, and not the data.

**Simulation runs alone; it does not show the baseline side by side** ([TO-25](../../ai-discussion/trade-offs.md)). So you see "this case is failing" rather than "this case flipped from pass to fail". Results are stored keyed by `config_hash`, so adding a comparison view later needs no change to the data model.

## Known limitations

- P6 covers **jailbreak** only — a user demanding in their own turn that the model break its instructions. It does **not** cover prompt injection through the data channel, where the malicious instruction is hidden in a retrieved document. Testing that means planting poisoned text in `corpus/`, at which point the corpus is no longer faithful to the source site and `corpus_hash` stops meaning anything.
- The judge is the same model as the thing being judged: self-evaluation bias, and swapping the model makes every historical verdict incomparable.
- 3 cases, one sample each; statistically weak, and the UI says `n=1` rather than pretending otherwise. The way to fix it is **more dimensions per case** (persona is one) rather than more cases.
- Non-Gemini providers are wired but unverified ([TO-31](../../ai-discussion/trade-offs.md)). The specific risk is structured output: the design assumes a real `responseSchema`, and a provider that only emulates one in the prompt would bring back the parse failures that assumption removed.
