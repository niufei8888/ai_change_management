**Start with [APPROACH.md](APPROACH.md).** The live URL, the setup command and the decisions behind all of this are there — deliberately in one place rather than repeated here. Running it natively instead of in Docker is covered in [apps/chatbot/README.md](apps/chatbot/README.md).


# Ask Luma + Driftline

Two things in one repo, deliberately: an AI product, and the system that manages changes to its behavior.

- **Ask Luma** (`/`) — a Q&A assistant that answers questions about Luma AI products using only the official documentation. Internally a ReAct loop: decide scope, search, check whether the evidence is enough, search again (max 3 rounds), then answer — or say plainly that the docs do not cover it. [apps/chatbot/README.md](apps/chatbot/README.md)
- **Driftline** (`/console`) — the console that introduces, evaluates and manages changes to that behavior. Edit the four versioned levers, try them on a single conversation, run them against a golden dataset, save as a version, activate. [apps/console/README.md](apps/console/README.md)

The second one is the point. Ask Luma exists to be the thing under management.

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
ai-sessions/             the unedited AI coding sessions, redacted and rendered
```

`apps/chatbot` and `apps/console` never import each other. Both depend on `packages/agent`, which is what makes "the benchmark ran the same loop production runs" structurally true rather than a claim.

## Design record

Written in Chinese, and it is the honest version — it includes the approaches that did not work and the reasons.

- [ai-discussion/design_high_level.md](ai-discussion/design_high_level.md) — the whole product
- [ai-discussion/design_step1_ai_app.md](ai-discussion/design_step1_ai_app.md) — Ask Luma, including five attempts at a demo regression that all failed to reproduce
- [ai-discussion/design_step2_console_with_benchmark.md](ai-discussion/design_step2_console_with_benchmark.md) — Driftline
- [ai-discussion/design_step3_misc_and_wrap_up.md](ai-discussion/design_step3_misc_and_wrap_up.md) — the two signposted non-goals, and the delivery surface
- [ai-discussion/design_step4_deploy.md](ai-discussion/design_step4_deploy.md) — deployment, including the `$PORT` form that was measured to fail before it was relied on
- [ai-discussion/design_step5_prepare_for_submission.md](ai-discussion/design_step5_prepare_for_submission.md) — packaging, and a credential that a shape-based scan reported as clean
- [ai-discussion/trade-offs.md](ai-discussion/trade-offs.md) — 24 numbered decisions, each with what it costs and what would overturn it, and an index of the five that carry the argument

The **unedited AI coding sessions** are in [ai-sessions/](ai-sessions/) — start with its [README](ai-sessions/README.md), which translates the turns that changed the product and says where each one landed in the code.
