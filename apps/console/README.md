# Driftline

引入、评测、管理 Ask Luma 的行为变更的控制台。左边编辑六个被版本化的杠杆，右边两个 tab：**Conversation** 用草稿配置跑单轮对话并摊开全部中间状态，**Simulation** 用草稿配置跑 golden dataset。

设计文档：[ai-discussion/design_step2_console_with_benchmark.md](../../ai-discussion/design_step2_console_with_benchmark.md)

被管理的对象是 `apps/chatbot`。**本服务不 import 它**——两者都依赖 `packages/agent`（同一个 ReAct 内核）和 `packages/behavior_core`（配置、版本、表）。这不只是洁癖：console 跑 benchmark 用的必须是 chatbot 服务用户时跑的**同一份代码**，否则「benchmark 测的是 production 的行为」就从结构事实退化成一句声明。

所有命令都在**仓库根目录**执行。

---

## 启动

```bash
uv sync
uv run python -m ask_luma.cli init-db          # 建表 + 把当前 BASELINE_V1 设为 active
uv run uvicorn server.main:app --reload --port 8000
```

- 控制台 <http://localhost:8000/console>
- 被管理的 chatbot <http://localhost:8000/>

`server.main` 是唯一同时 import 两个 app 的模块（[TO-21](../../ai-discussion/trade-offs.md)）。**同进程有个实际好处**：`config_client` 那个 5 秒缓存在进程内存里，所以 console 里 Activate 之后 `invalidate()` 失效的正是 chatbot 读的那份缓存，下一个请求立刻拿到新版本。分成两个进程也能跑，只是最多滞后 5 秒。

## 两类断言

一条 golden case 分两半，这个区分是整套评测的骨架：

| | fixed observation | dynamic expectation |
| --- | --- | --- |
| 是什么 | 关于「实际发生了什么」的事实 | 关于「回答该是什么样」的判断 |
| 谁判 | 确定性检查，读轨迹和输出，零 LLM | LLM judge |
| 可复现 | 是 | 否，会抖（[TO-12](../../ai-discussion/trade-offs.md)） |
| 门禁性质 | **blocking** | **advisory**，UI 标注「单次采样」 |

`BenchResult.passed` **只由 fixed observation 决定，代码上根本不读 `verdicts`**。judge 用的是跟被评测对象同一个模型（[TO-28](../../ai-discussion/trade-offs.md)），既会抖又存在自我评价偏袒，这种信号不能有能力把一次 run 判成绿的。

judge **看得到**工具调用的 tag 和 `terminated_by`，但不由它出这两条判定——给它看是为了让语义判定有依据（能说出「这句话没出处，因为这一轮什么都没检索到」）。同一个事实，一处做门禁，一处做解释。

## 不开浏览器也能跑

```bash
uv run python -m driftline.cli dataset          # 解析并打印数据集，零 API 调用
uv run python -m driftline.cli bench            # 当前 active 版本
uv run python -m driftline.cli bench baseline   # 代码里的 BASELINE_V1
uv run python -m driftline.cli bench bad-scope  # BAD_SCOPE_V2，这个 benchmark 存在的理由
```

设计上的检查点：`bench.py` 和 `judge.py` **必须先在命令行跑通再做前端**，这样一个红色结果一定是 chatbot 的行为问题，不会是前端的取数 bug。

```bash
# 不花配额，验断言机制本身：改名会不会被抓、字面 { 会不会崩、
# passed 会不会被 verdict 污染、两个 app 有没有互相 import、单 case 报错会不会带走整批
uv run python scripts/check_assertions.py

# 走 HTTP 驱动 Simulation 跑那条回归（需要服务已启动）
uv run python scripts/regression_demo.py
```

## 配额是硬约束，不是优化项

免费额度 **15 次请求/分钟**。一次完整 Simulation = 3 条 case ×（3–5 次 chatbot 调用 + 1 次 judge 调用）= **12–18 次**，必然贴着上限。所以 runner 是**串行 + 节流**（case 之间等 20 秒），一次 run 约 50–80 秒。并发在这里不会更快，只会把时间花在退避上。

两个缓解手段：

- **结果缓存**，键是 `config_hash` + `dataset_hash` + `corpus_hash` + `case_id`。同一份配置重跑秒出、零成本。`corpus_hash` 必须在键里——重抓语料会改变检索结果，少了它，缓存会拿旧语料下的行为冒充现在的行为。
- **逐 case 错误隔离**。这是全项目第三处、也是最后一处错误处理（[TO-22](../../ai-discussion/trade-offs.md) 的明确例外）：一条 case 崩了记成那条的 `BenchResult.error`，不带走整批。第一条崩掉顺带藏掉后两条的结果，比一行红色糟得多。

## `#search_docs`

prompt 里引用工具写 `#search_docs`，由 `packages/agent/tools.py` 的 `expand_tools()` 展开成 `tool_description` 杠杆的当前值。编辑器里打 `#` 弹出补全，已输入的 mention 在下方预览里渲染成 chip 并显示它展开成什么。

它取代了原来的 `{tool_description}` 占位符：prompt 一旦是 UI 里的自由文本，作者打一个字面的 `{` 就会让 `str.format()` 在 `plan.run()` 里抛 `KeyError`——崩的地方跟他改的地方隔着好几层。详见 [TO-26](../../ai-discussion/trade-offs.md)。

工具名只有 `packages/agent/search.py` 的 `TOOL_NAME` 一处定义，三个地方必须对上：prompt 里的 mention、轨迹里 search 节点的 `tool` 字段、`datasets/golden.yaml` 里的 `tool_called.name`。断言读 `tool` 字段而**不是** `node` 名——读 node 名的话工具改名后断言会永远静默 pass，那比没有断言更糟，因为它制造虚假的安全感。

## 数据集

`datasets/golden.yaml`，YAML 而非入库（[TO-14](../../ai-discussion/trade-offs.md)）。数据集是**输入**：改一条断言就是改产品被held 的标准，必须走代码评审、必须能 diff。放数据库里就成了「谁在什么时候悄悄放松了一条检查」的藏身处。

解析器只认 7 个 observation key，**遇到不认识的直接抛**。拼错的 key 被静默忽略的话，那条断言就什么都不做了——「写了但不跑」比没写更危险。

`covered` 那条 case 的问法是用 `scripts/probe_scope.py` 和 `scripts/probe_stability.py` 筛出来的，不是想出来的。理由见 [TO-29](../../ai-discussion/trade-offs.md) 和 YAML 里的注释：第一版手写的问法让回归静默溜过了整个数据集。

## 接口

全部在 `/api/console` 下。

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `GET` | `/versions` | 版本列表（active / draft / archived），带整份 config |
| `POST` | `/versions` | 存草稿为一个新版本 |
| `POST` | `/versions/{id}/activate` | 100% 切换 + `config_client.invalidate()` |
| `GET` | `/tools` | `#` 补全菜单的数据源 |
| `GET` | `/dataset` | persona / case / observations / expectations 全文 |
| `POST` | `/playground/chat` | body 带整份 config，返回回答 + 完整轨迹 + 证据 + 展开后的 prompt |
| `POST` | `/simulate` | body 带整份 config，起 BackgroundTask，返回 `run_id` |
| `GET` | `/runs/{id}` | 一次 run 的状态 + 已完成的 BenchResult（前端轮询） |
| `GET` | `/runs` | 历史 run 列表 |
| `GET` | `/health` | model / `corpus_hash` / `dataset_hash` / case 数 / `TOOL_REGISTRY` |

**Playground 的对话不写 `Conversation` 表。** 那张表的语义是「真实流量」，把试验混进去，「这个版本在生产里表现如何」就再也答不清了。

轮询而不用 SSE：一次 run 每跑完一条 case 就落一行，轮询天然拿到逐 case 进度（[TO-17](../../ai-discussion/trade-offs.md) 对 `/chat` 是同样的判断）。

## 本步不做什么

**灰度放量和自动回滚不做**（Step 3）。Activate 是**整体 100% 切换**，不是按比例。`Experiment` 表和 `Conversation.arm` / `experiment_tag` 都留着不删——删掉意味着改 Step 1 已经跑通的代码，净增工作量。

**Simulation 只单跑，不并排对比基线**（[TO-25](../../ai-discussion/trade-offs.md)）。所以看不到「这条 case 从 pass 翻成 fail」，只能看到「这条 case 现在是 fail」。结果按 `config_hash` 落库，后面加对比视图不用改数据模型。

## 已知限制

- P6 只覆盖 **jailbreak**（用户在自己那一轮里要求模型违背指令），**未覆盖数据通道的 prompt injection**（恶意指令藏在被检索回来的文档里）。后者要求往 `corpus/` 里种投毒文本，语料就不再忠于原站，`corpus_hash` 的语义也跟着废掉。
- judge 用与被评测对象同一个模型：自我评价偏袒 + 模型一换历史 verdict 不可比。
- 3 条 case、每条单次采样，统计意义弱。UI 上明示 `n=1`。修这个的方向是**给每条 case 加维度**（persona 就是一个），而不是堆 case 数量。
