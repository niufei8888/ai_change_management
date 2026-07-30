# APPROACH

**Live at <!-- RENDER_URL -->** (console at `/console`), and `docker compose up --build` locally. The hosted instance is a free tier: the first request after idle takes about a minute to wake, and its data resets on each cold start. §Deployment at the bottom says what that cost bought and what it did not.

---

## What you built and why

Two things in one repo, and the second one is the point.

**Ask Luma** (`/`) is a Q&A assistant over the 39-article Luma AI Learning Center. Internally it is a ReAct loop — decide scope, plan a query, search, check whether the evidence is enough, search again (three rounds at most), then answer, or say plainly that the docs do not cover it.

**Driftline** (`/console`) is the system that introduces, evaluates and manages changes to that behavior. Ask Luma exists to be the thing under management.

### The one idea

The prompt lists seven levers — "prompts, model routing, tool usage, retrieval strategies, temperature, guardrails, post-processing". I read the list as making a single point: **the unit of change is a behavior configuration, not a prompt.** So a version here is four levers hashed together into a `config_hash`:

```
plan_prompt · reflect_prompt · synthesize_prompt · tool_description
```

Three separately-versioned prompts rather than one big one, because that is what makes a diff attributable — when an assertion fails you can say *which node* to fix. And `tool_description` is in there deliberately: it is what stops this from degrading into a prompt-management tool, and it is where the sharpest failure mode lives.

It was six. `temperature` and `max_loops` were levers and I cut them, which costs something real — see [What I intentionally left out](#what-you-intentionally-left-out).

That configuration is resolved **on the critical path** — `config_client.resolve(session_id)` runs on every single request. Nothing is compiled into the deploy. This is the whole reason a version can be activated, evaluated and rolled back without touching code, and it is a decision you have to make before writing anything else, because retrofitting it means rewriting the serving path.

### Who I built it for

The prompt says "a team" and does not say which one. I did not ask; I picked, and the pick shows up everywhere. **The user is the person who is about to change AI behavior and needs to know what the change does before real traffic finds out.** Not a researcher chasing a benchmark number, not an ops engineer watching dashboards. That is why the console has no aggregate score, why the diff is word-level, and why every result is one click from the trajectory that produced it.

### What "working software" means here

- 2,983 lines of Python, 1,340 lines of hand-written frontend, no build chain
- One process serves both apps; `docker compose up --build` is the whole setup
- 39 articles committed (`corpus_hash 73224a81445a5258`), so the container needs no network except the model API
- A golden dataset of 3 cases and 2 personas (`dataset_hash 1f7c2f65d6f95198`)
- Two real benchmark runs shipped as seed data, so the console has content before you spend a single API call

The full design record — including the approaches that failed and why — is in [`ai-discussion/`](ai-discussion/). It is written in Chinese; it is a working record rather than a deliverable, and it is honest in a way a polished writeup is not.

---

## Key decisions and tradeoffs

There are 21 numbered decisions in [`ai-discussion/trade-offs.md`](ai-discussion/trade-offs.md), each with what it costs and what would overturn it. Five carry the argument.

### 1. Behavior is a versioned configuration, resolved on the request path

[TO-06](ai-discussion/trade-offs.md), [TO-07](ai-discussion/trade-offs.md). Covered above. The cost is real: the control plane becomes a **runtime dependency** of the product, and there is now a failure mode where a request cannot be served because the config could not be read.

I originally had a fail-open to last-known-good and **deleted it**. Two reasons. It was dead code — after merging into one process this is a local SQLite read with no partial-failure mode. And more importantly, silently serving traffic with a stale config manufactures exactly the situation this product exists to eliminate: behavior that does not match what you think is deployed, with no signal. If this ever splits into two processes and the hop becomes HTTP, fail-open goes back in.

### 2. Blocking checks must be deterministic; the LLM judge is advisory only

[TO-10](ai-discussion/trade-offs.md), [TO-05](ai-discussion/trade-offs.md). Every golden case splits in half:

| | fixed observations | dynamic expectations |
| --- | --- | --- |
| what | facts about what happened, read off the trajectory | judgements about what the answer should be like |
| who decides | deterministic code, no LLM | an LLM judge |
| reproducible | yes | no |
| gating | **blocking** | **advisory** |

`BenchResult.passed` is computed from `observations` alone. **The code never reads `verdicts`** — and `scripts/check_assertions.py` stubs the judge to return all-fail, runs the real `bench._run_case`, and asserts `passed is True`. The distinction is enforced by executable code rather than by this document.

That matters because the judge is the same model being evaluated. Two independent problems follow, and neither is "we did it for simplicity":

1. **Self-evaluation bias.** A model grading its own output is known to be systematically lenient.
2. **Model drift invalidates every historical baseline.** Swap the judge model and no previous verdict is comparable. In production the judge has to be pinned independently of the model under test, or "let's upgrade the chatbot model" silently replaces your entire baseline.

There is also no aggregate score, on purpose. `0.82 → 0.85` tells you nothing; "case 3's P3 went from pass to fail because it invented an export format that does not exist" is actionable. An average would also dilute a fatal violation into a rounding error. The cost is that you cannot glance at two versions and see which is "better" — which is the intended effect, because that decision should not be compressible into one number.

### 3. The regression that improved every aggregate metric

This is the demo, and it is worth being precise about.

Someone sees the bot answer a question it should not have, so they tighten the scope rule in `plan_prompt` — "only questions naming a specific product, model or feature are in scope; if unsure, refuse." The single most natural fix anyone would make. Same question, before and after:

```
baseline    answered              loops=1  calls=3  $0.001797  3690ms   substantive answer, three citations
bad-scope   refused_out_of_scope  loops=0  calls=1  $0.000148   893ms   "this request is too broad"

12x cheaper. 4x faster.
```

That is one run; the ratio moves between 12x and 16x because the baseline itself is not deterministic — it sometimes needs a second search round. Which is its own finding, and the reason the smoke script only asserts on the candidate side: an assertion of the form "baseline answers *and* candidate refuses" would be flaky.

Cost down, latency down, fewer LLM calls, and the answer that does come back is crisp. **Every aggregate metric says this is an improvement.** The product is broken. An entire class of legitimate questions now gets refused, and the only thing that catches it is a deterministic assertion that a case which should have been answered was refused.

This is why cost and latency are first-class metrics here even though the model is not a lever ([TO-05](ai-discussion/trade-offs.md)): *whether the model retrieves at all* moves both, so the cheapest-looking version can be the broken one.

### 4. Retrieval is deliberately weak

[TO-02](ai-discussion/trade-offs.md). `search_docs` is keyword matching over local files. No embeddings, no vector store, no reranker. Retrieval quality is not the subject; change safety is, and RAG would import a whole second vocabulary of evaluation (recall@k, chunk attribution) that eats the time and blurs the line.

The cost — genuinely bad recall on conceptual questions — turns out to be a benefit twice over. Whether the model admits it does not know when retrieval comes back empty is the best possible test for the refusal policy. And weak retrieval **amplifies** how much the tool description matters, which is what makes decision 3 land.

### 5. Small enough to read in one sitting

[TO-22](ai-discussion/trade-offs.md). One decision applied four ways: let-it-fail error handling (exactly three `try` sites in the whole project), no unit tests, no frontend build chain on either page.

The reasoning is the same each time. Defensive code turns 200 lines of core logic into 500, and the extra 300 say nothing about the product. And "runs in a clean Linux container" is worth more than extensibility here — no `node_modules`, no build step, a single-stage pure-Python image, one fewer entire category of "does not install on the reviewer's machine".

The honest cost: pure functions like the retrieval scorer and the rollout bucketer would have been cheap to unit-test and are now only covered by eyeballing a smoke run.

---

## What you intentionally left out

Two of these are **visible in the UI rather than absent from it**, because blank space and a deliberate omission look identical to whoever is reading the screen.

### Gradual rollout has no control surface — but the runtime is live

Activate is a **100% switch**. Traffic is never split.

What is easy to get wrong here is the direction of the claim. This is not "we stored a column for later". `config_client.resolve()` already buckets **every request** by a salted hash of `session_id`, compares it against `rollout_pct`, picks candidate or baseline, and stamps `arm` and `experiment_tag` onto both the response and the stored conversation. That code path executes on every question anyone asks. What is missing is (a) any way to create an `Experiment` row and (b) a ramp policy — health thresholds, a step schedule, an auto-rollback trigger.

So the console shows the controls that would drive it, real and disabled. I deliberately did **not** hand-insert an `Experiment` row to demo the bucketing, even though it is nearly free: it would genuinely split traffic, which would contaminate the "Activate changes behavior immediately" demo that matters far more. And a rollout without a ramp policy is a toy — the value was never in splitting traffic, it is in what signal tells you whether to keep going.

### Production traffic cannot be sliced by experiment tag

`GET /api/conversations` already accepts `?tag=` and `?arm=`, and `experiment_tag` is indexed. The query path exists and is what the new **Production** tab reads through. Not built on top of it: filtering and search by tag, a baseline-vs-candidate comparison of the two arms, promoting a production conversation into the golden dataset as a new case, and re-running the judge over a tagged slice on a schedule with a violation-rate threshold.

The tab is read-only real data rather than a placeholder, and the reason is that here there is something to show. "All of this is already being captured" told as a table with real rows in it is a different claim from the same sentence in prose, and it cost zero new backend.

### Production monitoring and alerting

[TO-15](ai-discussion/trade-offs.md). No scheduled jobs, no trend charts, no alert rules, no reports.

The argument, which is also why I am comfortable with the omission: **the hard part is producing structured, tagged, per-policy-judged data. The dashboard layer is a commodity.** Once every conversation carries its version, config hash, arm and tag, and every judge result is a per-policy verdict with a reason, pointing Superset or Grafana at the same table makes alerting a threshold rule. So I spent the time on the data model instead of reimplementing a reporting tool. The cost is that discovering a problem depends on someone going to look, and nobody manually triggers a judge run at 3am.

### Two levers, cut on purpose — and this one has a real cost

`temperature` and `max_loops` were versioned levers. They are now constants in the code ([TO-06](ai-discussion/trade-offs.md)).

The reason is attention budget, not that the levers were wrong. Five minutes has a hard ceiling, and the six levers were not equal per unit of screen space. The three node prompts earn theirs by making a diff attributable to a node. `tool_description` earns the most: it is the sharpest failure mode in the project, and the only lever that is about *tool usage* rather than prompt wording. What `temperature` and `max_loops` contributed was two number inputs demonstrating "numeric levers work too" — and the schema already says that, because `BehaviorConfig` is a single JSON column and adding a field does not change the table. Two controls repeating it were spending `tool_description`'s explanation time.

Here is what it costs, and it is worth stating plainly because **it retracts an argument I made earlier**: `max_loops` was how this design covered the cost/quality axis it gave up by fixing the model. Lower the cap and it is cheaper and faster but refuses more; raise it and recall improves while cost and latency climb linearly. That is a textbook judgement call a human has to make, and it was the answer to "you removed the model, so where is the cost/quality tradeoff?"

**That hole is open again.** All four remaining levers are text. The honest description is that this product now manages the class of change *expressed in words*; the class *tuned with numbers* is mechanically supported and has no entry point in the UI. Also, comparing temperature 0.2 against 0.7 now needs a code change and a deploy, which is precisely the workflow this thing exists to eliminate.

Deliberately **not** signposted in the UI, unlike the two above. Those are "not yet"; this is "decided against". Reserving screen space for something I have already concluded I do not want would be promising something I do not intend to deliver.

### Everything else

- **Multi-turn conversation** ([TO-01](ai-discussion/trade-offs.md)) — the biggest capability gap. Behavior drift across turns is invisible here. Single-turn keeps the evaluation unit trivially simple: one input, one decidable output.
- **RAG** ([TO-02](ai-discussion/trade-offs.md)), **auth / multi-tenancy / RBAC** ([TO-04](ai-discussion/trade-offs.md)), **model as a lever** ([TO-05](ai-discussion/trade-offs.md)), **unit tests and a frontend build chain** ([TO-22](ai-discussion/trade-offs.md)).
- **Side-by-side comparison against the active version** ([TO-25](ai-discussion/trade-offs.md)) — this one hurts, because it undercuts decision 2: "P3 *flipped* from pass to fail" is more actionable than "P3 is failing", and running alone only gives you the latter. Results are stored keyed by `config_hash`, so the view needs no data-model change. The shipped seed data already contains both runs.
- **Prompt injection through the data channel.** The jailbreak case covers a user demanding the model break its rules in their own turn. It does not cover a malicious instruction hidden in a retrieved document — testing that means planting poisoned text in `corpus/`, at which point the corpus stops being faithful to the source and `corpus_hash` stops meaning anything.

---

## What breaks first under pressure

Specific known failure points, in the order they would actually bite.

**1. The 15 requests/minute free tier.** This is the binding constraint on the entire design, not a footnote. One Simulation is 3 cases × (3–5 chatbot calls + 1 judge call) = 12–18 requests, which sits against the ceiling. The runner is serial and throttled 20 seconds between cases, so a run takes 50–80 seconds. **Two people clicking Run at the same time start colliding with 429s.** Concurrency would not help; it would spend the time in backoff. Mitigated by caching on `config_hash` + `dataset_hash` + `corpus_hash` + `case_id` — a repeat run is instant and free — but the cache does not help the first run of anything.

**2. Non-Gemini providers are wired but unverified** ([TO-31](ai-discussion/trade-offs.md)). The take-home provisions Anthropic and OpenAI keys; this was built on Gemini, which is not on that list. So `MODEL` now accepts `anthropic/…` and `openai/…`, with the price table and a startup key check to match — but **I had no key for either and never ran them**, which is why the README says "wired, not verified" instead of "supported".

The specific thing that would break is structured output. Decision 2's design assumes a real `responseSchema`, which is what removed format errors as a category; a provider that only emulates one in the prompt brings back `ValidationError`, and let-it-fail means that surfaces as a 502. If a run dies in `plan` or `reflect`, that is what happened. Claiming support for a path I never executed would be worse than not claiming it.

**3. Three golden cases is statistically meaningless** ([TO-13](ai-discussion/trade-offs.md)). The UI says `n=1` rather than pretending otherwise. The real fix is not more hand-written cases — it is growing the set from production traffic, which is what the Production tab is the first step toward. The interim answer is **more dimensions per case**: persona (blunt vs neutral) makes one case test behavioral correctness and tone resilience at once.

**4. Self-evaluation bias means semantic regressions can slip through.** Structurally contained — judge verdicts cannot turn a run green — but containment is not detection. A version that gets subtly worse in ways only the judge would notice passes.

**5. SQLite and a single process.** One process is what buys instant rollback (the console's cache invalidation reaches the exact cache the chatbot reads). The cost is no process-level isolation: the console taking the process down takes the chatbot with it. Splitting is a deployment change, not a code change — both entry points already exist.

**6. `cites_real_article` is O(titles × text length).** Fine at 39 articles; at a few thousand it wants Aho-Corasick ([TO-30](ai-discussion/trade-offs.md)).

**7. The seed fixture drifts from the code.** It is a snapshot of a real run, so editing a prompt constant leaves a seeded run whose `config_hash` matches no `Version`. That is exactly the invisible drift this product exists to surface, so `seed_demo.py load` compares hashes and says so out loud, and seeded rows are marked in the UI.

---

## What you'd build next

Ordered by what I would actually do, not by size.

1. **The rollout control surface, plus a ramp policy.** The runtime is done. What is missing is an endpoint to create an `Experiment`, and the part that is actually hard: which signal gates the next step. Concretely — error rate and `refused_out_of_scope` rate per arm, a threshold, and an auto-rollback that fires on it. Without that last piece, percentage rollout is a slider that makes you feel safe.
2. **Promote a production conversation into the golden dataset.** The Production tab puts the rows on screen; this turns "3 cases" into a set that grows from real traffic. It also makes the dataset represent what users ask rather than what I imagined they would.
3. **Side-by-side against the active version.** Recovers the "flipped from pass to fail" framing that [TO-25](ai-discussion/trade-offs.md) gave up. The data model already supports it and the seed data already contains both runs; it is one page that reads two results and diffs them.
4. **A judge from a different model family, with its version recorded in `BenchRun`.** Removes self-evaluation bias, and recording the version makes "these two runs are not comparable" a visible fact rather than a silent one. `BenchRun` does not store `model` today, which is a real gap.
5. **Multi-turn.** The largest gap and the largest amount of work, because it needs a different evaluation unit: assertions about whether context was correctly inherited across turns.
6. **Deploy it.**

---

## How I directed the AI

The prompt asks how I directed the tools and where I pushed back. Three moments actually shaped the result, and what they have in common is that **I stopped trusting my own design document and ran the thing.**

### I predicted five regressions. All five failed to reproduce.

The headline demo was supposed to be `tool_description`: narrow the tool's description, the model stops retrieving, it starts making things up. I designed the whole thing on that premise. Then I ran it.

| # | lever | change | result |
| --- | --- | --- | --- |
| 1 | `tool_description` | "Search for specific feature names." | still retrieved |
| 2 | `tool_description` | "only for numeric limits and pricing" | still retrieved |
| 3 | `tool_description` | "retrieval is slow and expensive, use sparingly" | still retrieved |
| 4 | `plan_prompt` | a direct instruction not to retrieve unless stuck | still retrieved |
| 5 | `reflect_prompt` | "prefer answering over searching again" | still ran all 3 rounds |

The root cause has two layers, and the second one is the interesting one. On the surface, the constitutional line at the top of `plan_prompt` outweighs a tool description. But attempt 4 was a *direct contrary instruction* and still lost — because **the model genuinely does not know Luma's products.** It is a small documentation site. Its judgement that it must look things up was factually correct. The model was not disobedient, it was well calibrated.

The change that worked goes **with** the model's grain instead of against it: tighten the scope rule so it over-refuses. That is decision 3 above, and it is a better demo than the one I designed, because its motivation is something a real person would actually do.

**The generalisable point is the product's own thesis: you cannot infer behavior change from a diff. You have to run it.** I proved that on myself, five times, before the tool existed to prove it for me.

### My golden dataset was all green and defending nothing

Once the benchmark ran, I pointed the known-bad config at it. **All three cases passed.** The regression walked straight past the entire dataset.

The `covered` case needs to satisfy two conditions that pull against each other: the baseline must reach `answered` *reliably*, and the tightened version must wrongly refuse it. My hand-written wording read perfectly — conceptual, no feature names — and satisfied only the first.

A fully-green dataset that catches nothing is **worse than no dataset**, because it manufactures confidence. I fixed it with two probe scripts: `probe_scope.py` calls only the plan node (2 requests per candidate instead of 8–12, which is what made trying 7 candidates possible on a 15 RPM budget) to find wordings the strict version refuses, and `probe_stability.py` samples repeatedly to eliminate ones where the baseline flakes. The surviving wording and the reasoning are in the YAML comments.

There is a pleasing circularity here: **I used the benchmark tool to select its own test cases.**

### A deterministic check that passed for the wrong reason

`cites_real_article` verifies the answer names a real article and nothing else. My first version split the `Source:` line on commas and "and", then looked each fragment up.

Real titles contain both separators — `Run, Edit and Share Skills`, `Character and Object Consistency`. Splitting shredded valid titles into fragments, and the fragments then matched by accident through substring containment. The first live run printed `cited ['Character', 'Object Consistency', ...]`. **Green, and indistinguishable from broken.**

The generalisable lesson, and the reason `scripts/check_assertions.py` exists: the dangerous failure mode of a deterministic check is not a false alarm, it is **passing for the wrong reason**. False alarms get looked at. This does not. So every check now has a companion input constructed to fail, verifying that it does.

### Where I pushed back on the AI, and where it pushed back on me

Two directions worth recording.

I told it to delete things repeatedly — a fail-open branch, a `reset-db` command, an unused endpoint, four separate trade-off entries that were one decision written four times. Left alone it accretes. Every removal above is a place where less code was the better answer.

It also stopped me once. Asked to reset the database after a `config_hash` change, the destructive path got blocked, and the alternative was strictly better: make `seed_baseline()` idempotent and self-healing instead. It now archives the stale active row and activates the one matching the code, never deleting. Which is the correct behavior on the merits — "the active version's hash matches no config in the source" is precisely the drift this product exists to remove, and deleting would have destroyed the conversation and benchmark history too.

---

## Deployment

Render free tier, Docker, one web service, auto-deployed from `main`. The service definition is in [`render.yaml`](render.yaml) rather than only in the dashboard, for the same reason prompts live in a database and not in the code: a setting that changes how the thing behaves should be reviewable in a diff.

Two costs came with picking the free tier, and both are visible to you rather than hidden:

**It sleeps after 15 minutes and takes about a minute to wake.** For a link someone opens once, that lands on exactly the wrong request. I kept it anyway because the alternatives were worse for this purpose: Fly.io and Railway no longer have a real free tier in 2026, Cloud Run wants a billing account attached, and an Oracle free VM means owning SSH, TLS and a reverse proxy. I did not add a cron job to ping it awake — the 750 monthly instance hours are priced on the assumption that free services sleep, and keeping one warm on purpose is using the tier against its own terms.

**A free instance loses its filesystem every time it sleeps**, and the free tier has no persistent disk, no shell, and no one-off jobs. So there is no way to re-seed by hand after a deploy — the demo data has to come back from the app's own startup, which is what `SEED_DEMO=1` does. That turned out better than the paid-disk version: every cold start gives a known-good state that nobody's clicking around can corrupt.

Deploying also created a real exposure I did not have locally: `/api/chat` is public and spends a metered key on every request. There is a `robots.txt` and a `noindex` meta tag, and it is worth being exact about what those buy — they are a voluntary convention that well-behaved crawlers honour, so they cut the "indexed, then found by a stranger" path and nothing else. They do nothing against a scanner or anyone holding the URL. **The actual cap on cost is that the key gets revoked when the review is over.** I chose that over adding rate limiting, because a limiter behind Render's proxy has to trust `X-Forwarded-For` to know who it is limiting, and shipping something that looks like protection while being trivially spoofable is worse than saying plainly that there is none.

`docker compose up --build` still gets you both surfaces on one port, with none of the above. Without a `.env` the container starts and then exits naming the environment variable it wants, because a missing credential should not present as a missing file.
