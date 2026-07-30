# Repository conventions

## Leave `ai-discussion/` alone

`ai-discussion/` holds the entire design record for this project: the prompt, the overall design, the per-step designs, and the trade-off log.

**When writing code, restructuring directories, or cleaning up the repo, never delete, move or rewrite anything under it.** It is not scratch work and it is not superseded by a README — `APPROACH.md` carries only the conclusions a reviewer needs, while the reasoning and the rejected approaches live here.

To change a design, edit the document in `ai-discussion/`. Do not start a second copy somewhere in the code tree.

## Language

`ai-discussion/` is written in Simplified Chinese; it is a working record for the author. **Everything else is English** — code, comments, commit messages, READMEs, `APPROACH.md`, the golden dataset. A reviewer has to be able to run this and read how it works, and the setup instructions are part of what is being delivered.

## Code style: let it fail

See TO-22 in `ai-discussion/trade-offs.md`. Errors are not caught by default; a problem crashes where it happens with a full traceback. There are exactly **three** pieces of error handling in the project, and there should not be a fourth:

1. `llm.py` — `tenacity` retrying 429 / timeout / 5xx with backoff. Those are the provider's state, not our bug.
2. The route boundary in `apps/chatbot/src/ask_luma/main.py` — one `try` around the request that writes a `Conversation` carrying `error` and a partial `trajectory`, then returns 502. This is observability, not recovery: it does not rescue the request, it makes sure the failure is recorded.
3. `apps/console/src/driftline/bench.py` — per-case isolation. Running a batch of golden cases, one case blowing up must be recorded as that case's `BenchResult.error` and must not take the batch with it.

No `except Exception` catch-alls, and no fallback branch for a value that is "theoretically possibly None".

## Directory boundaries

```
packages/behavior_core                 contracts: config / models / db / config_client
packages/agent    ──▶ behavior_core    the reusable ReAct kernel + the tool registry
apps/chatbot      ──▶ agent, behavior_core
apps/console      ──▶ agent, behavior_core
apps/chatbot      ──✗ apps/console     forbidden
apps/console      ──✗ apps/chatbot     forbidden
behavior_core     ──✗ agent            forbidden (TOOL_REGISTRY needs search.TOOL_NAME; a
                                       contract layer importing the kernel would cycle)
```

`apps/server/src/server/main.py` is the only place allowed to import both apps, and it only mounts them. `scripts/check_assertions.py` enforces this.

**The rule is about Python imports, not about HTTP.** One process serves both apps on one origin, so the console's page fetching `/api/conversations` — an endpoint that belongs to the chatbot — has not crossed the boundary. Nothing in `apps/console/src/` imports `ask_luma`, and that is the invariant being protected.

The kernel lives in `packages/agent` rather than inside `apps/chatbot` because both apps must run **exactly the same loop**: the chatbot serves it to users, the console runs it against the golden dataset. If the console imported the chatbot, "the benchmark measures production behavior" would degrade from a structural fact into a claim.

## The tool name is defined once

`TOOL_NAME` in `packages/agent/search.py` is the only definition. Three things have to agree: the `#search_docs` mention in prompts, the `tool` field on the search node in the trajectory, and `tool_called.name` in `datasets/golden.yaml`. The assertion reads the `tool` field rather than the `node` name — reading the node name would make the assertion pass silently forever after a tool rename, which is worse than having no assertion at all.
