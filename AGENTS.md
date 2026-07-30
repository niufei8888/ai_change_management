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

不写 `except Exception` 兜底，不为「理论上可能为 None」加降级分支。全项目第三处、也是最后一处错误处理是 `apps/console/src/driftline/bench.py` 里逐 case 的 `try`：批量跑 golden case 时，一条崩了必须记成那条 case 的 `BenchResult.error`，不能带走整批。

## 目录边界

```
packages/behavior_core        契约层：config / models / db / config_client
packages/agent    ──▶ behavior_core       可复用的 ReAct 内核 + tools 注册表
apps/chatbot      ──▶ agent, behavior_core
apps/console      ──▶ agent, behavior_core
apps/chatbot      ──✗ apps/console        禁止
apps/console      ──✗ apps/chatbot        禁止
behavior_core     ──✗ agent               禁止（TOOL_REGISTRY 要引 search.TOOL_NAME，放 core 会成环）
```

`apps/server/src/server/main.py` 是唯一允许同时 import 两个 app 的地方，且只做 mount。这条规则由 `scripts/check_assertions.py` 守住。

Agent 内核在 `packages/agent` 而不在 `apps/chatbot` 里，是因为两个 app 必须跑**完全同一个循环**：chatbot 把它服务给用户，console 拿它跑 golden dataset。console 要是 import chatbot，「benchmark 测的就是 production 的行为」就从结构事实退化成一句声明。

## 工具名只有一处定义

`packages/agent/search.py` 的 `TOOL_NAME` 是唯一定义。三个地方必须对上：prompt 里的 `#search_docs`、轨迹里 search 节点的 `tool` 字段、`datasets/golden.yaml` 里的 `tool_called.name`。断言读 `tool` 字段而不是 `node` 名——读 node 名的话，工具改名后断言会**永远静默 pass**，那比没有断言更糟。
