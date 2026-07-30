# 仓库约定

## `ai-discussion/` 不要动

`ai-discussion/` 存的是这个项目的全部设计过程文档（题面、总设计、分步设计、trade-off 记录）。

**写代码、重构目录、清理仓库的时候一律不要删除、移动或改写这个目录下的任何文件。** 它不是临时草稿，也不是可以被 README 取代的东西——`APPROACH.md` 只写给评审看的结论，完整的推演过程和被否掉的方案都在这里。

需要改设计的时候，改 `ai-discussion/` 里对应的文档，不要在代码目录里另起一份。

## 交流语言

设计文档和讨论用简体中文。代码、注释、commit message、`APPROACH.md` 用英文。

## 代码风格：let it fail

见 `ai-discussion/trade-offs.md` 的 TO-22。默认不接错误，让它带着完整 traceback 崩在原地。全项目只有两处错误处理：

1. `llm.py` 里 `tenacity` 对 429 / 超时 / 5xx 的退避重试
2. 路由边界那个「落一条带 `error` 的 Conversation 再返回 502」

不写 `except Exception` 兜底，不为「理论上可能为 None」加降级分支。唯一的例外是 Step 2 的 benchmark runner，批量跑 case 时需要按 case 隔离错误。

## 目录边界

```
apps/chatbot  ──▶ packages/behavior_core
apps/console  ──▶ packages/behavior_core
apps/chatbot  ──✗ apps/console          禁止
apps/console  ──✗ apps/chatbot          禁止
```

`apps/server/main.py` 是唯一允许同时 import 两个 app 的地方，且只做 mount。这条规则由 `apps/chatbot/tests/test_no_cross_app_imports.py` 守住。
