# APPROACH

## Where it runs, and how to run it

**Deployed on Render** — free tier, Docker, auto-deploys from `main` ([`render.yaml`](render.yaml)).

- Demo chatbot app: <https://ai-change-management.onrender.com>
- Change management console: <https://ai-change-management.onrender.com/console>

The first request after idle takes about a minute to wake, and a free instance loses its filesystem every time it sleeps, so the hosted console starts empty.

**Locally**, one command — no build step, the corpus is committed, nothing but the model API leaves the machine:

```bash
cp .env.example .env       # fill GEMINI_API_KEY; add SEED_DEMO=1 for a populated console
docker compose up --build  # http://localhost:8000 and /console
```

Built and measured on Gemini (`gemini/gemini-3.1-flash-lite`), which this take-home does not provision a key for. `MODEL` also accepts `anthropic/…` and `openai/…` — routing, key check and price table are in place, but I had neither key, so `.env.example` calls those "wired, not verified".

## What you built and why

There are 2 things in this repo, and the 2nd one is the point of the question #3.

- **Ask Luma** (`/`) is a Q&A assistant over the 39 articles on Luma AI Learning Center. Internally it is a ReAct loop — decide scope, plan a query, search in articles, check whether the evidence is enough, search again or answer. (The question prompt says "a team" and does not say which one. This Ask Luma is the "a team" example, which is the customer of the change management system)

- **Driftline** (`/console`) is the system that test ideas, quickly evaluates, and manages production changes to the Ask Luma app's behavior. Ask Luma is under its management.

A concrete Driftline customer is a PM or developer on Ask Luma team who is about to change the Ask Luma chatbot behavior and needs to know what the change does before real traffic finds out. Driftline is also in charge of the change rollout, monitoring, and rollback.

Driftline is a shared platform, and will have other customers similar to the Ask Luma product team.

## Key decisions and tradeoffs

Ask Luma app is intentionally made simple with 1-turn conversatio and 1 read-only toolcall ability (search from articles on local FS) as its not the focus of this exercise. The below tradeoff decisions are only for the "Driftline" change management system:

1. **2 major problems: quick testing out ideas and benchmarking.** Modern AI application includes:
- platform codes: orchestration engine and serving code
- Domain context: prompts, registered toolcalls, orchestration config
The platform ships on a code release cycle.
The domain context should have easy access for the domain team to test out ideas several times a day. Driftline focus on this part, where the 2 questions are *does my idea work* and *did it break something*. Handling these 2 questions are the 2 P0 goals. Faciliating context release and experiments are the P1 goals.

2. **Context is intentionally on the critical path to support experiments.** `config_client.resolve()` reads the active configuration, which includes prompts and registered toolcalls, from the database on every request, so a change can be edited, evaluated, activated and rolled back on the Driftline UI with. The tradeoff is real and deliberate: the control plane becomes a runtime dependency of the product on the critical path.

3. **The versioned unit are only context: prompt + toolcall for simplicity.** Driftline only manage prompt + toolcalls for simplicity. For a fully fledged solution, it should only version the orchestration, model, and data. I intentionally left those parts out due to demo time limits.

4. **Benchmarking needs both deterministic checks and LLM judge checks.** In the benchmark deterministic checks observations the "tags" generated from the AI app, while LLM jedge evaluates the languages of the conversations. The former is more stable but can't evaluate the converstaion tune, while the latter can check the converstaion language but can be instable and costly. We usually need both in a production system to fully cover the benchmark.


## What you intentionally left out

1. **Multi-tenancy.** One team, one dataset, no auth or role based access controle. Everything here assumes a single product team for simplicity.

2. **Agentic eval's Sandbox infra.** Ask Luma has one read only tool, so a benchmark run is safe to execute in-process. The moment a tool writes anything, evaluation needs isolated environments and seeded state, which is its own infrastructure.

3. **More managed components: orchestration DAG, model routing, or LLM failover strategy.** For simplicity, we only support 2 managed components: Prompts + toolcalls.

4. **Benchmark: Golden test set need to have a retrival pipeline.** In real production system, tests sets are mined from production traffic cases. I added a production tab to demo the idea but didn't add the mining and Golden tests set editing feature.

5. **Experiment: Traffic % based rollout.** Experiment related features like defining ramp up user group %, or ramp policy (which signal gates the next step and triggers auto-rollback).

6. **Observability infra and the feedback loop to the change management system.** Every conversation already carries its version, config hash, and tag. Observability infra can be built on top of them and provide gating signals for #5 above.

## What breaks first under pressure

1. **Infra-side: LLM benchmark scalability (the 1k golden dataset problem) and slow UI rendering.** Backend: The benchmark runner is serial. Parallel workers and fleet management are needed especially considering multi-tenancy. Frontend: The console UI renders every result row eagerly and stops being usable when editing features become more complicated, for example: Adding more features than only registering the toolcall.

2. **Product-side: Customization for different customers' (customers are product teams) use cases.** A 2nd product team beyond Ask Luma will require its own managed components, benchmarking policies, and observation types. Each new feature request will require balancing team-specific customization against platform fragmentation and long-term maintainability.

## What you'd build next

The strategy should be:
1. Successfully Support 1 customer product team
2. Expand to multi-tenancy with shared features

Multi-tenancy built before one team's loop is proven is a schema with no evidence behind it. So immediate next focus should be in order like:

1. Agentic eval's Sandbox infra.
2. Benchmark: Golden test set need to have a retrival pipeline.
3. Observability infra and the feedback loop to the change management system.
(Items are from the "What you intentionally left out" section)