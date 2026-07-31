# AI session history

Two Cursor sessions, unedited, covering this project end to end. The brief says it
wants to see *how you direct the tools — how you plan, how you course-correct, what
you accept and what you push back on*. This directory is the primary evidence for
that, and [`APPROACH.md`](../APPROACH.md#how-i-directed-the-ai) is the three-page
version of the same story.

**Read this file first.** The transcripts themselves are long and one of them is in
a language you may not read.

---

## Before anything else: the sessions are half in Chinese

I work with the model in Chinese. So in the raw record **my instructions are in
Chinese and the model's replies are in English** — which means the half a reviewer
most wants to read is the half that needs translating.

I did not translate the transcripts. A translated instruction is my later account of
what I meant, not what I said, and evidence stops being evidence once I have rewritten
it. What I did instead is [§The moments that shaped it](#the-moments-that-shaped-it)
below: the instructions that actually changed the product, quoted in the original and
translated line by line, each with what it changed and where that landed in the code.
Roughly a dozen turns out of fifty-four, chosen for consequence.

One more thing that will otherwise read as incoherence: **the Chinese is dictated,
not typed.** Speech-to-text artifacts are all over it. `凸靠` is "toolcall", `Gadriel`
is "guardrail", `local fallacy team system` is "local file system", `pathon` is
"python", `Ermine` is "amend". I have left every one of them in place.

---

## The two sessions

| file | title | my turns | what it is |
| --- | --- | --- | --- |
| [`planning.md`](planning.md) | `planning` | 32 | The spine. Reading the brief, arguing about scope, then design and implementation of all five steps. |
| [`qq.md`](qq.md) | `qq` | 22 | The side channel. Questions about the brief's own vocabulary, then git setup, then the deployment research. |

Both sessions are titled by me, in Cursor. `qq` is where I went when I wanted an
answer rather than a change — it opens two minutes after the first design draft
existed, with a question about words in the brief I did not want to gloss over.

Each session ships twice:

- **`<title>.md`** — rendered for reading. Start here.
- **`raw/<title>.jsonl`** — what Cursor wrote, one JSON event per line.

The rendering is done by [`scripts/export_sessions.py`](../scripts/export_sessions.py),
which is committed **so that "nothing was cherry-picked" is checkable rather than
asserted** — run it against the raw files and diff. Its docstring lists every
transformation it performs; the only lossy one is credential redaction. Tool calls
appear as single lines naming the tool; results were never in the JSONL.

---

## The moments that shaped it

Ordered by when they happened.

### 1. Asking what the brief's own words mean, before writing any of it

> 这个里面的 model routing 和 post-processing 一般指什么？你给我几个例子。你不用写在 plan 里面，直接回答我就行。
>
> *"What do model routing and post-processing usually mean here? Give me a few examples. You don't need to put it in the plan, just answer me directly."*

`qq.md`, first turn. The brief lists seven levers of AI behavior. I could name five
of them cold. Rather than build around the five I knew, I asked about the two I did
not — and the answer is why the finished product treats behavior as a *configuration
of several levers* instead of a prompt with a version number.

### 2. "Tell me where the ambiguity is" — not "build me this"

> 你来读一下这个 README file，然后告诉我这道题应该怎么去想：它的 ambiguity 在什么地方？
>
> *"Read this README and tell me how I should think about this problem: where is its ambiguity?"*

`planning.md`, first turn. The first request of the project is an analysis of the
problem statement, not a line of code.

### 3. Pushing back on the model's first plan for being too narrow

> 我感觉你的 plan 主要是说做这个 prompt versioning […] 可是我看这个，它不止，可不止是 prompt。还有就是说，你觉得我要不要去和 Recruiter clarify 一下这个？[…] 你说 "that helps a team introduce bla bla bla"，你看第18行，那这个 team 做什么？一般工作中我先要 clarify，但是它这个没给
>
> *"Your plan is mostly about prompt versioning […] but reading this, it is more than that — it is definitely not just prompts. Also: do you think I should clarify this with the recruiter? […] It says 'that helps a team introduce blah blah blah' — look at line 18 — so what does this team do? At work I would clarify first, but this doesn't tell me."*

The model's first design was prompt-versioning-with-a-test-suite. I rejected the
framing, and the disagreement is what produced the four-lever `config_hash` in
[`packages/behavior_core/models.py`](../packages/behavior_core/models.py) — in
particular `tool_description`, the one lever that is about tool usage rather than
wording, and the one the headline demo turns on.

### 4. Deciding to assume rather than ask

> 我确认这个 A team 它就是一个故意 ambiguous 的，我们咱们可以 make assumption。我觉得这道题咱们就做，因为它的考点主要是在这个 evaluation、change safety system，所以说我们把这个产品做得简单一点。
>
> *"I've confirmed that 'a team' is deliberately ambiguous and we can make an assumption. I think we just do it, because what's really being tested is the evaluation and change-safety system — so let's keep the product itself simple."*

Same message goes on to specify the entire product: a Q&A bot over Luma's Learning
Center, articles downloaded to local files, **no RAG**, one search tool, single-turn,
every conversation persisted with its tag. The deliberate weakness of retrieval was
a decision made here, in one sentence, and it is load-bearing —
[`APPROACH.md`](../APPROACH.md#key-decisions-and-tradeoffs) decision 4 explains why
bad recall turned out to help twice.

A note to the recruiter asking exactly this did get drafted, in a session not
packaged here. But the decision above was made first and the work did not wait on
an answer, which is the part that matters: an ambiguity you have decided how to
resolve is no longer blocking.

### 5. The agent loop, the cap, and honesty as the default

> 我们限制这个 loop 不超过 3 次。如果要是超过 3 次的话，那就跟用户说："我不知道"，就是要诚实。[…] 我们要把这个在目录结构上面和之后要做的 evaluation system 要在目录结构上隔离开。
>
> *"Cap the loop at 3 rounds. If it goes past 3, tell the user 'I don't know' — be honest. […] And structurally isolate this from the evaluation system we'll build later, at the directory level."*

Two decisions in one turn. The cap and the refusal became `MAX_LOOPS` and the
`terminated_by` vocabulary in [`packages/agent/graph/runner.py`](../packages/agent/graph/runner.py) —
`exhausted` exists as a distinct outcome from `answered` because of this instruction,
and the golden dataset can assert on it. The isolation request became the
`apps/chatbot ──✗ apps/console` import boundary, which is what later forced
[`packages/behavior_core/seed.py`](../packages/behavior_core/seed.py) to exist rather
than letting the chatbot import the console's code.

### 6. "Let it fail"

> 我们的 coding 风格应该是那种"let it fail"模式。很多地方不要做过多的这种 try-catch […] 另外一方面，对于 LLM call，你是要做 try-catch 的。[…] 如果它是格式的 fail 掉的话，我们就 throw error，然后重新开始。[…] 总之，这个 trade-off 就是简洁，因为重点其实不是这个 Demo app，是后面的那个 evaluation 和这个 change safety system。
>
> *"Our coding style should be 'let it fail'. Don't put try/except everywhere […] LLM calls are the exception — retry those. If it fails on format, throw and start over. […] The tradeoff is simplicity, because the point isn't the demo app, it's the evaluation and change-safety system behind it."*

The whole project has three `try` sites. This instruction is why, and the last
sentence is why the console got the attention instead.

### 7. The distinction the whole product rests on

> 你的 test 是需要有一个定义的，就是说你的这个 simulation 的 user 是什么的 persona […] 这个 tag 的 call 就是 fix 的 observation；还有些就是那种 non fix observation，比如说语言温度什么的，就是 expectation。它应该是分这两种：一种是 fixed 的，一种是相当于是 dynamic 的。
>
> *"Your test needs a definition — what persona is the simulated user […] Whether the tool got called is a fixed observation; things that aren't fixed, like tone, are expectations. It should split into two kinds: fixed, and effectively dynamic."*

**This is the single most consequential turn in either session.** *Fixed observation*
versus *dynamic expectation* is mine, from this message, and it is the load-bearing
idea in the product: mechanical facts read off the trajectory are **blocking**, and
anything an LLM judged is **advisory**. It is enforced in code —
[`BenchResult.passed`](../packages/behavior_core/models.py) is computed from
`observations` alone and nothing ever reads `verdicts` — and
[`scripts/check_assertions.py`](../scripts/check_assertions.py) stubs the judge to
fail everything and asserts a run still passes.

The same turn also settled the `#search_docs` sigil (the model had flagged that `@`
collides with `str.format`, so I told it to pick something else) and accepted a real
compromise: the judge is the same cheap model as the system under test, which is
self-evaluation bias, taken knowingly for demo cost.

The `persona` half of it became the blunt-versus-neutral pair in
[`datasets/golden.yaml`](../datasets/golden.yaml), so one case tests behavioral
correctness and tone resilience at the same time.

### 8. Cutting scope twice, with the second cut against my own earlier argument

> 我们再 further reduce scope，我们把 temperature 的这个选项彻底拿掉了 […] 还有 max loops 也一样 […] 不用把这个 signpost 在这个 UI 上了。
>
> *"Reduce scope further — take the temperature option out entirely […] same for max loops […] and don't signpost it in the UI either."*

Six levers became four. This one cost something real and
[`APPROACH.md`](../APPROACH.md#two-levers-cut-on-purpose--and-this-one-has-a-real-cost)
says so plainly, because `max_loops` had been my answer to "you fixed the model, so
where is the cost/quality tradeoff?" — removing it reopened that hole.

Same turn, a smaller thing I like: rather than rename the version `label` field to
`name`, keep the name and **prefill the input with the current timestamp**, so the
field arrives with a usable default instead of empty.

### 9. Where the language boundary sits

> 这个里面把所有的中文都翻译成英语，因为这个地方以后是会在 UI 里面 show 出来的，所以我们不要用中文。
>
> *"Translate all the Chinese in here into English, because this gets shown in the UI later, so we shouldn't use Chinese."*

`qq.md`. The rule that came out of this: design notes in
[`ai-discussion/`](../ai-discussion/) stay Chinese because they are a working record;
**anything a user or reviewer sees is English.** Prompts, dataset, UI copy, code
comments, README. That is also why this file exists.

### 10. Checking whether a name was invented

> Driftline 这个是你自己给它起的名字吗？
>
> *"Driftline — is that a name you came up with yourself?"*

Small, and I am including it deliberately. The model had named the console
`Driftline` and I had used it for an hour before thinking to ask where it came from.
Anything the model produces that I then repeat as if it were mine is a thing I should
have checked. The name stayed; the habit of asking is the point.

### 11. Three UI bugs I found by using the thing

> 你看一下 product 那个地方，它返回那个 source 的时候，你要给链接 […] 你看，它那个地方的链接现在是失效的，点也点不上。还有就是，你这个里面好像有一些就是那种 markdown 的那个形式 […] 但是它并没有加粗；它把那个 markdown 直接显示出来了。
>
> *"Look at the product — when it returns a source, you need to link it […] see, the link there is dead, you can't even click it. Also, there's some markdown in here […] but it isn't bold; it's showing the raw markdown."*

The last substantive turn before submission, and it is three separate bugs found by
reading actual output rather than by testing. The fix had one root cause — `/chat` and
`/console` each had a private opinion about how an answer looked — so both now share
[`apps/chatbot/web/answer.js`](../apps/chatbot/web/answer.js). Chasing the citation
links also turned up that `How to Create Skills in Luma` lives at `/create-luma-skills`:
**title and slug disagree, so a URL guessed from a title 404s.** That is the reason
links are built from backend-resolved citations and not composed in the frontend.

---

## What is not here

- **A third session** (`demo`, 91 messages) worked out the five-minute video
  narrative. Not packaged, so the video's structure has no written source here.
- **Two more** — a one-line vocabulary question, and drafting a note to the
  recruiter — are omitted as noise and as off-topic respectively.
- **Tool results.** Cursor's JSONL records tool calls but not what they returned, so
  you can see that a command ran and not what it printed.
- **Credentials**, replaced with `<REDACTED>`. Absolute paths under my home
  directory are rewritten to `<repo>` and `<home>`.

This is a raw record. It contains reasoning I later abandoned, at least one design I
built on a premise that turned out to be false, and a bug I shipped and then found.
Those are the parts worth reading — [`APPROACH.md`](../APPROACH.md#how-i-directed-the-ai)
tells three of those stories, and this is where you can check them against what
actually happened.
