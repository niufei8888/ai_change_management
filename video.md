# Video walkthrough

<!-- Paste the link here before submitting. -->

**Link:** _(pending)_

---

Roughly five minutes, covering:

| | |
| --- | --- |
| 0:00 | What this is: an AI product, and the system that manages changes to its behavior. `/console` is the point. |
| 0:30 | `/chat` answers a question. Expand the trajectory: search rounds, citations, cost, `terminated_by`. |
| 1:15 | **The headline.** Tighten one scope rule, run the golden dataset. Cost down, latency down, fewer calls, crisper answer — every aggregate metric improved, and the product is broken. One deterministic assertion catches it. |
| 2:45 | Activate it, ask the same question at `/chat`, watch the behavior change. No restart, no deploy. Activate back. |
| 3:30 | Fixed observations versus dynamic expectations. `BenchResult.passed` never reads the judge's verdicts, in the code. The judge is the same model, so it is systematically lenient. |
| 4:15 | The two signposted non-goals: the rollout runtime already runs on every request, what is missing is the control surface. Then the story of the first golden dataset — all green, defending nothing. |
