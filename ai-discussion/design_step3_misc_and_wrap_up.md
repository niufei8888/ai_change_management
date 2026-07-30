# Step 3：收口、signpost 与交付

> 这一步**不加新的产品能力**。它做五件事：
>
> 1. 把两个已经决定不做的能力**明确地摆到 UI 上**，而不是留成一片空白
> 2. 把交付面修到「干净容器里陌生人能跑起来」，包括**没有 Gemini key 的人**
> 3. 语言收口：`ai-discussion/` 之外全英文
> 4. 补上题面要求的提交物结构（`APPROACH.md` + `video.md`）
> 5. 把 30 条 trade-off 压到能在五分钟里讲完（实际压到 21 条 + 10 行别名）
>
> 前两步的产出是[design_step1_ai_app.md](design_step1_ai_app.md)（Ask Luma，`/`）和[design_step2_console_with_benchmark.md](design_step2_console_with_benchmark.md)（Driftline，`/console`），都已实现并验收通过。
>
> **部署不在本步范围内**，会单独成篇。顺序是：本步收口 → 准备 demo → 视 demo 暴露的问题回头改 → 最后才谈部署。

---

## 0. 为什么需要这一步

前两步各自都是「做加法」，收尾时留下三类债，它们的共同点是**单独看每一条都不严重，加在一起会决定评审的第一印象**：

| 债 | 具体是什么 | 为什么现在还债 |
| --- | --- | --- |
| **说了不做，但 UI 上看不出来** | 灰度放量、按 tag 查生产对话，两个都在设计文档里明确写了「不做」，但界面上是**一片空白**，不是「一个标注了 coming next 的位置」 | 空白和「刻意不做」在评审眼里是同一个样子。而这两块的运行时其实**已经写完了**（§2.1、§3.1），不点出来等于白写 |
| **交付面没被陌生人跑过** | 我一直在自己机器上 `uv run`，Docker 只在 Step 1 建过一次就没再碰 | 题面明确要求「setup instructions that work in a fresh Linux container — we will run your code in one during review」 |
| **文档和代码开始互相说谎** | 数据集已经改成英文，但两份设计文档里的示例还是中文旧版；TO-14 选 YAML 的理由之一是「`expect` 的正文是一整句中文判据」，现在不成立了 | 这个项目整个主题就是「消灭行为和你以为的不一致」。文档和代码不一致是同一种病的另一种形态 |

---

## 1. 本步的范围

**做：**

1. 灰度放量 → **禁用状态的真实控件**（§2）
2. 按 tag 查生产对话 → **只读真实数据的 Production tab**（§3）
3. 让没有 Gemini key 的评审也能跑（§4）
4. 修 Docker 三处硬伤（§5）
5. 语言收口：`ai-discussion/` 之外全英文（§6）
6. 提交物结构：`APPROACH.md` + `video.md`（§7）
7. trade-offs 合并 + demo 主线索引（§8）
8. **杠杆从六个砍到四个**：`temperature` 和 `max_loops` 退回代码常量（§2.5）

**明确不做：**

- **部署**（另开一篇，见上面的顺序说明）
- 真的实现灰度放量的控制面
- 真的实现按 tag 的检索 / 切片 / 对比
- 定时 judge 复跑、告警、趋势图（TO-15 原样保留）
- 任何新的产品行为能力
- **给 `temperature` / `max_loops` 也做 signpost**——它们不是「以后要做」，是**决定不做**，见 §2.5

---

## 2. Signpost 一：灰度放量

### 2.1 现状核查：运行时其实已经通了

写这一节之前我先读了代码，结果和我原本准备写的「以后做起来很简单」**不一样**。灰度的运行时不是「路打通了」，是**已经在跑**：

```71:98:packages/behavior_core/config_client.py
def resolve(session_id: str) -> ResolvedConfig:
    active, experiment = _load_state()

    if experiment is None:
        return ResolvedConfig(..., experiment_tag=None, arm="default")

    in_candidate = _bucket(experiment.id, session_id) < experiment.rollout_pct
    wanted_id = experiment.candidate_version_id if in_candidate else experiment.baseline_version_id
```

逐条清点已经实现的部分：

| 部件 | 位置 | 状态 |
| --- | --- | --- |
| 「有没有正在跑的实验」查询 | `config_client._load_state()` | ✅ **每个线上请求都在走** |
| 加盐确定性分桶 | `config_client._bucket()` | ✅ 盐是 experiment id，为的是让连续两个实验重新洗牌，不让同一批人总落在同一侧 |
| `rollout_pct` 比较、选 candidate / baseline | `config_client.resolve()` | ✅ |
| `arm` / `experiment_tag` 打进响应 | `apps/chatbot/src/ask_luma/main.py:62-63` | ✅ |
| `arm` / `experiment_tag` 落进 `Conversation` 行 | `apps/chatbot/src/ask_luma/main.py:91-92` | ✅ `experiment_tag` 建了索引 |
| `Experiment` 表（`tag` / `rollout_pct` / candidate / baseline / status） | `packages/behavior_core/models.py` | ✅ |

本步在 Docker 容器里发的那次真实请求返回的是 `arm: default, tag: None`——**走的就是 `experiment is None` 这个分支**。这条路每秒都在被执行。

**缺的只有两样：**

1. 没有任何地方能**创建** `Experiment` 行。没有 endpoint、没有 CLI、没有 UI。所以 `rollout_pct` 这个字段永远用不上。
2. 没有放量**策略**：健康度阈值怎么定、多久 ramp 一档、什么条件触发自动回滚。这部分连设计都没有。

### 2.2 决定：禁用的真实控件，而不是一段静态文案

- **决定**：在 console 左栏版本列表下方加一个 **Rollout** 区块，里面是**真实的、但被禁用的控件**：一个 `rollout_pct` 滑块（固定在 100，灰态）、一个 candidate / baseline 版本选择器（灰态）、一个 tag 输入框（灰态），加一句说明。不是一段「Coming soon」的文字。

- **为什么是禁用控件而不是文案**：文案只能被读，控件能被**看懂形状**。评审看到滑块和两个版本选择器，立刻知道这个功能的输入是什么、粒度是什么；读一段「以后会支持按比例放量」什么都不知道。而且禁用控件把「缺的是控制面」这句话变成了**视觉上的字面事实**——控件在那儿，就是点不动。

- **说明文案要说的是运行时已通，不是「以后会做」**（这是 §2.1 那次核查的直接产出）。措辞方向：

  > Traffic is not split today: `Activate` is a 100% switch. The runtime for gradual rollout is already on the request path — `config_client` buckets every request by a salted hash of `session_id`, compares it against `rollout_pct`, and stamps `arm` and `experiment_tag` onto both the response and the stored conversation. What is missing is this control surface and a ramp policy (health thresholds, step schedule, auto-rollback trigger).

  这段话的每一个技术断言都能当场在代码里指出来。这是它和一句 marketing 式预告的区别。

- **代价**：禁用控件比一行文案花的前端时间多（滑块、灰态样式、tooltip）。而且有一类评审会去点它，点不动会有一瞬间的困惑——所以 tooltip 必须直接说明为什么禁用，不能只是灰着。

### 2.3 为什么不真的插一行 `Experiment` 演示分桶

这个诱惑很大：插一行 `Experiment` 就能真的看到流量分成两半，几乎零代码。**但不做**，三个理由，按重要性排：

1. **它会真的切流量。** 一旦有 `status="running"` 的行，`/chat` 的每个请求都开始分桶。demo 里演示「Activate 立即改变行为」时，会有一半的 session 落在 candidate 上——**这两个功能的演示会互相污染**，而「Activate 生效」是 Step 2 最核心的那个 demo。
2. **没有放量策略的灰度是个玩具。** 灰度的价值不在「能分流」，在「分流之后靠什么信号决定继续放还是回滚」。只演示分流会让人以为难的部分已经解决了，而难的部分恰恰是那个信号。这跟 TO-15 的论点是同一个：**难的是产出可判定的数据，不是画界面。**
3. **它会让 §2.2 那句话变成谎话。** 说「control surface is missing」的同时偷偷手插一行让它跑起来，是在演示一个没有产品支撑的能力。

### 2.4 新的 trade-off 归属

不新开编号。这条并进 **TO-09**（灰度按 session_id 确定性分桶），因为它就是那条决定的收尾：机制已实现，控制面明确不做，理由如上。TO-09 补一段「Step 3 收口」。

---

## 2.5 杠杆从六个砍到四个

> 编号用小数是故意的。这一节是本步后期加进来的，而 §3 以后的编号在别处被引用了——为了插一节去重排全文编号，正是这个项目在 TO 编号上明确拒绝的做法。

### 2.5.1 决定

`temperature` 和 `max_loops` **不再是版本化杠杆**，退回成代码里的常量：

| 原杠杆 | 新落点 | 值 |
| --- | --- | --- |
| `temperature` | `packages/agent/llm.py` 的 `TEMPERATURE` | 0.2 |
| `max_loops` | `packages/agent/graph/runner.py` 的 `MAX_LOOPS` | 3 |

`BehaviorConfig` 从六个字段变四个，全是文本：三个节点 prompt + `tool_description`。console 左栏那两个数字输入框整个删掉。

**不给它们做 signpost。** 这跟 §2 / §3 那两个是**性质不同**的两件事，混在一起会把话说糊：灰度和 tag 查询是「决定这次不做、以后要做」，所以摆在 UI 上预告；`temperature` 和 `max_loops` 是「决定不作为杠杆存在」。给一个已经想清楚不要的东西做预告位，等于承诺一件不打算兑现的事。

### 2.5.2 为什么砍

理由是 demo 的注意力预算，不是这两个杠杆不成立。

五分钟里能讲清楚的东西有硬上限，而这六个杠杆**不等价**：

- 三个 prompt 撑起「变更可归因到具体节点」——断言挂了能直接说改哪个节点。
- `tool_description` 是**整个项目最强的那个 demo**：改一行工具描述，模型不再检索、开始编，而 prompt 的 diff 是空的。它也是唯一一个不是「prompt 行为」而是「工具用法」的杠杆，是这个产品没退化成 prompt 管理工具的证据。
- `temperature` 和 `max_loops` 是两个数字输入框。它们在 demo 里能贡献的是「你看，数值型的杠杆也支持」——**而这句话是版本表的 schema 已经说过的话**，因为 `BehaviorConfig` 是一个 JSON 列，加字段不改表（TO-06）。用两个控件重复说一遍，占的是 `tool_description` 的讲解时间。

单位屏幕面积的说服力最低的两个，先砍。

### 2.5.3 砍掉之后失去了什么（这一条不能含糊）

**TO-06 里有一整句论证是靠 `max_loops` 立住的**，原文是「`max_loops` 补回了 TO-05 砍掉的成本/质量权衡轴」。TO-05 把 `model` 移出杠杆，代价是失去了最常见的那条成本/质量轴；`max_loops` 当时被拿来补这个洞——调低更便宜更快但 `exhausted` 率上升，调高召回更好但成本延迟线性涨。这是个教科书级的、必须由人判断的权衡。

**现在这个洞重新开着了。** 六个杠杆里再没有一个数值型的，四个全是文本。诚实的说法是：**这个产品现在管的是「用文字描述的行为」这一类变更**，而「用数字调的行为」这一类，机制上支持（加字段不改表）但界面上没有入口。

代价的另外两小条：

- **`temperature` 不能再按版本实验。** 想比较 0.2 和 0.7，得改代码重新部署——正是这个产品要消灭的那种流程。
- **失去一个「同一份配置跑两次结果不同」的现成解释入口。** 有 `temperature` 在版本里时，「为什么这次和上次不一样」有个可以直接指的地方；现在得靠文档说明它被 pin 在 0.2。

顺带一个不算理由但确实成立的观察：LiteLLM 已经在警告 Gemini 3+ 计划移除 `temperature` 参数。一个可能被上游拿掉的参数，本来就不适合当产品的核心杠杆——但**这是事后发现的巧合，不是当初砍它的原因**，不能拿来充当决策依据。

### 2.5.4 连带影响

1. **`config_hash` 变了**：baseline `c64bbc62a755c53d` → `ea2580ac6b707853`，bad-scope `78b09295ca8ea47a` → `a206518b2f616f03`。所以 §4.3 的 seed fixture 必须**重跑重导**，否则 seed 出来的 run 指向一个不存在的配置——那正是 TO-16 记的那种漂移。
2. **旧版本行不会坏**：Pydantic 默认忽略多余字段，所以数据库里带六个字段的历史 `Version` 照样能载入。它们存的 `config_hash` 是按六字段算的，跟现在算法的结果不同——这不是 bug，是「那一行记录的确实是当时那份配置」。`seed_baseline()` 的幂等自愈会把新的四字段 baseline 插进去并激活，旧的转 `archived`（TO-26 的行为，不用改）。
3. **judge 的 temperature 留着**。`JUDGE_TEMPERATURE = 0.0` 和 agent 的 0.2 是两个不同的、有理由的值，所以 `llm.call()` / `call_structured()` 保留 `temperature` 参数但给默认值，judge 继续显式传 0。
4. **文档要改的地方**：`AGENTS.md`、两份 README、`README.md`、`.env.example`、`APPROACH.md`、TO-06、TO-01、TO-05。凡是写「六个杠杆」的地方。

### 2.5.5 顺带修一处交互摩擦：version label 的 placeholder

`new version label` 那个输入框原来空着就弹 alert 拦住保存。改成：placeholder 显示一个按当前时间生成的建议名（`v-20260730-1345`），**留空保存就直接用它**，alert 删掉。

理由是这个摩擦出现的时机不对——你正在做实验，不是在做发布。逼人先想个名字才能存，最可能的结果是随手打一个比时间戳更没信息量的字符串。好名字仍然更好，所以这是建议而不是强制填入：预填的文字得先删掉才能打自己的。

`focus` 时重新生成一次，避免标签页开着放久了名字对不上实际保存时间。

### 3.1 现状核查：console 里一处 tag 都没有

你要我先查的这件事，答案是**一处都没有**。`apps/console/web/index.html` 全文 840 行，搜 `experiment_tag` / `arm` / `Experiment` / `rollout`：零命中。没有生产对话列表、没有 tag 输入、没有 arm 显示。

console 里唯一叫「tag」的东西是**工具名**——轨迹行里的 `tool: search_docs`，和 fixed observation 里的 `tool_called`。那是 TO-26 的 mention 语法，跟 experiment tag 没有关系。

但和 §2.1 同样的情况：往下一层，**后端是完整的**。

```108:128:apps/chatbot/src/ask_luma/main.py
@app.get("/api/conversations")
def conversations(session_id: str | None = None, tag: str | None = None,
                  arm: str | None = None, limit: int = 50, offset: int = 0) -> list[dict]:
    """History for the chat frontend (by session_id) and experiment slices for
    the step 2 console (by tag / arm). One endpoint, two consumers."""
```

按 tag 和 arm 过滤**已经能用了**，是 Step 1 就写好的（TO-17，原 TO-19 里那句「console 靠 `tag`/`arm` 做实验切片」）。`/chat` 自己的 trace 面板也已经在显示这三个值：

```267:267:apps/chatbot/web/index.html
["Version", `${data.version_label} · ${data.arm}${data.experiment_tag ? " · " + data.experiment_tag : ""}`],
```

所以缺的是**视图**，不是数据、不是端点、不是索引。

### 3.2 决定：只读真实数据的 Production tab

- **决定**：console 右栏加第三个 tab —— **Production**。它调已经存在的 `GET /api/conversations?limit=20`，把返回的真实行渲染成一张只读表：

  | 列 | 来源 |
  | --- | --- |
  | 时间 | `created_at` |
  | 问题（截断） | `question` |
  | `version_label` | 落库时那次请求解析到的版本 |
  | `config_hash` | 短 hash |
  | `arm` | `default` / `baseline` / `candidate` |
  | `experiment_tag` | 没有实验时是空 |
  | `terminated_by` | `answered` / `refused_out_of_scope` / `exhausted` |
  | 成本 / 延迟 | |

  点一行展开该次对话的完整轨迹（`trajectoryView()` 已经有了，直接复用）。

  表头上方一句说明：按 tag 检索、按 arm 切片对比、把生产对话一键加进 golden dataset —— 都不做，说明缺的是什么。

- **为什么是只读真实数据，而不是禁用控件**（和灰度的处理刻意不同）：**因为这里有真东西可以给你看。** 灰度那边没有 `Experiment` 行，除了插一行别无办法（§2.3 已否）；而生产对话是真的、每次 demo 都在增加、每一行都带着 `version_label` 和 `arm` 和 `config_hash`。

  「这些数据都已经存下来了，以后做起来很简单」这句话，用一张有真实行的表说出来，和用一段文案说出来，**说服力差一个量级**。而它的成本是**零新后端**：端点、过滤、索引全都在。

- **顺带补上一个真实的缺口**：现在 demo 里演示「Activate 改变行为」，靠的是同一个问题问两次、肉眼比较两次回答。有了 Production tab，两次请求会以两行的形式并列出现，`version_label` 和 `config_hash` 两列不一样，**同一个变更的前后对照变成表格里可以指的东西**。这不是新能力，是把已经落库的数据显示出来。

- **代价**：
  - `/api/conversations` 返回的是 `row.model_dump(mode="json")`，**整行都回来，包括完整 `trajectory`**。20 行的 trajectory 是个不小的 payload。本步不改端点（改了就是在动 Step 1 已验收的代码），前端只取需要的字段，把「该给列表页做一个精简投影」记进 §11 风险。
  - 只读表看久了会想点表头排序、想搜索。明确不做，说明文案要挡住这个预期。

### 3.3 为什么 console 前端调 `/api/conversations` 不算越界

第一眼像是违反了 `AGENTS.md` 里那条 `apps/console ──✗ apps/chatbot`。不是。

那条规则管的是 **Python import**：`apps/console` 的模块不许 `import ask_luma`。理由是依赖方向——控制台依赖服务端就把方向搞反了（TO-08）。

而这里是**浏览器发的一个 HTTP 请求**，两个 app 由同一个进程挂载在同一个 origin 下（TO-08，原 TO-21），`/console` 页面里 `fetch("/api/conversations")` 和它 fetch `/api/console/versions` 在架构上是同一件事：一个前端调它需要的 HTTP 端点。Python 侧一行代码都没有跨过边界。

`scripts/check_assertions.py` 扫的是 import，所以它不会误报，也不该被改。**但这个区分要写在 `AGENTS.md` 里**，否则下一次有人（包括未来的我）看到 console 页面调 chatbot 的端点，会以为规则已经烂了。

### 3.4 trade-off 归属

并进 **TO-15**（不做 production monitoring 和 alerting）。TO-15 原文写的是「只做『按 experiment tag 抽取生产对话 + 手动触发 judge 复跑』」——本步把这句**再往下砍一刀**：连「按 tag 抽取」都不做，只做一个不带筛选的只读视图。TO-15 补一段修正，并保留它最重要的那个论点（难的是产出结构化带 tag 的数据，报表层是商品化的）——现在这个论点有 Production tab 当证据了。

---

## 4. 交付可运行性：让没有 Gemini key 的评审也能跑

### 4.1 风险陈述

题面第 50 行：

> A `.env.example` is included with stub keys for providers we have accounts with (**Anthropic, OpenAI, ElevenLabs, Google Cloud, AWS**). Copy it to `.env`, use whichever keys your solution needs, and document any others.

我们用的是 **AI Studio 的 `GEMINI_API_KEY`**，不在这个名单里（名单里的 Google Cloud 是 Vertex AI，是另一套凭据）。TO-05 里我已经写下了这个风险：

> **对评审的影响**：题面预置的 `.env.example` 是 Anthropic/OpenAI 的 key，我们用 Gemini，所以 README 和 APPROACH.md 必须显著说明需要自备 Gemini key，否则对方跑不起来。

**写下来了，但一直没缓解。** 只在文档里写一句「请自备 Gemini key」，实际效果是：评审在容器里跑起来，界面打开了，问一个问题，拿到 502。这是最糟的一种失败——**看起来是我们的 bug**。

### 4.2 让 `MODEL` 真的跨 provider

- **决定**：`MODEL` 支持 `anthropic/…` 和 `openai/…`，README 和 `.env.example` 显式给出可用的取值。

- **工作量比看起来小得多**，因为抽象早就在了：

  ```19:19:packages/agent/llm.py
  MODEL = os.getenv("MODEL", "gemini/gemini-3.1-flash-lite")
  ```

  LiteLLM 按 provider 前缀自己去找对应的环境变量（`ANTHROPIC_API_KEY` / `OPENAI_API_KEY`），`litellm.drop_params = True` 会丢掉目标模型不支持的参数。**换 provider 这件事本身已经能用了。** 要补的是三处：

  1. **价格表**。这是唯一的真问题：
     ```25:30:packages/agent/llm.py
     PRICES = {
         "gemini-3.1-flash-lite": (0.25, 1.50),
         ...
     }
     DEFAULT_PRICE = (1.50, 9.00)  # assume expensive rather than free if the model is unknown
     ```
     补两三个 Anthropic / OpenAI 便宜型号的价格。`DEFAULT_PRICE` 的「宁可算贵不算免费」保持不动——它存在的理由（成本不许静默变成 0）跟换 provider 无关。
  2. **`responseSchema` 的等价性要实测**。这是**最需要验证的一点**，不能只靠 LiteLLM 声称支持。TO-20 的整个论证建立在「结构化输出删掉了格式错误这一整类失败」之上；如果换到 Anthropic 之后 schema 是靠 prompt 里塞 JSON 说明实现的，那 `ValidationError` 就会重新出现，而 TO-22 说了格式错误直接抛——**评审换个 model 就会撞 502**。所以验收里必须有「换一个 provider 跑通 `smoke.py`」这一条（§10）。
  3. **启动期检查 key**。现在 key 为空的话，第一次 LLM 调用才炸，表现是 502。改成启动时按 `MODEL` 的 provider 前缀检查对应的环境变量在不在，不在就**在启动期崩掉**，错误信息直接写「`MODEL` 是 `anthropic/…`，需要 `ANTHROPIC_API_KEY`」。这符合 TO-22 的取向：让它崩在原地，而且崩在离原因最近的地方。

- **这和 TO-05「模型不可配置」矛盾吗？不矛盾，但必须说清楚**，否则看起来像自己推翻自己。两件事一直是分开的：

  | | 是什么 | 本步有变化吗 |
  | --- | --- | --- |
  | `MODEL`（`.env`） | **部署级设置**。整个进程用哪个模型，从 Step 1 就是环境变量 | 只是让它跨 provider 也能工作 |
  | 六个版本化杠杆 | **产品级变更单位**。`config_hash` 覆盖的东西 | **没有变化，`model` 仍然不在里面** |

  TO-05 说的是后者：`model` 不进版本化配置，因为 judge 模型必须 pin 住，一换历史基线全部作废。本步动的是前者。**版本表的 schema 一个字段都不改，这是最直接的证据。**

- **代价**：新增的价格数字我没有实测过 token 计费（只是照官方价目表抄），成本数字的可信度在非 Gemini 模型上低一档。而且 `MODEL` 一换，**`BenchRun` 里的历史基线就不可比了**——这正是 TO-05 警告过的那件事。所以 `BenchRun` 应该把 `model` 记下来（现在没记），让不可比至少是**可见**的不可比。

- **归属**：新开 **TO-31**，放在 D 组（交付与运维）而不是 B 组（架构）。它存在的唯一理由是「陌生人能不能跑起来」，是交付决策，不是产品决策。

### 4.3 seed 数据：没有 key 也能看到完整界面

- **决定**：`scripts/seed_demo.py` 把一份**提交进 git 的 fixture** 灌进 SQLite：几条 `Conversation`（覆盖 `answered` / `refused_out_of_scope` / `exhausted` 三种终止态）、两个 `Version`（基线 + 那个坏版本）、一次完整的 `BenchRun` + 三条 `BenchResult`（含 judge verdicts）。

- **为什么必须是 fixture + 脚本，不能提交 `.db`**：`data/` 在 `.gitignore` 里（连带 `.env`、`.venv`）。这不是可以改的——`data/app.db` 会带着我 demo 时的全部对话历史一起进版本库，而且二进制文件在 git 里没法 review。所以形态只能是**可读、可 diff 的 JSON fixture + 一个灌库脚本**。

  这是对 **TO-16** 的补充（TO-16 定的是「预计算结果直接入库，不做 replay provider 层」，没说清怎么随仓库交付）。

- **顺带解决三个问题**：
  1. 无 key 的评审能看到**有内容**的界面，而不是三张空表。
  2. Production tab（§3.2）在 demo 开始前就有行可看，不用先手动问几个问题。
  3. Simulation tab 的历史下拉框里有一次真实 run，「回归被抓到」这个故事**不依赖当场跑一遍**（当场跑要 50–80 秒，还看 15 RPM 的脸色）。

- **代价**：fixture 是我某一次真实运行的快照，会和代码**漂移**——prompt 常量一改，fixture 里的 `config_hash` 就对不上任何现存 `Version`。这跟 TO-26 处理过的那个问题是同一类。缓解：seed 脚本**幂等**，且 UI 上 seed 出来的行要**可辨认**（比如 `session_id` 前缀 `seed-`），不能让人误以为是刚跑出来的。

### 4.4 `.env` 缺失时的行为

见 §5.1，是 Docker 那三处硬伤之一。

---

## 5. Docker：三处硬伤（本步已实测）

### 5.0 先说验收结果：能跑

本步实测记录，不是推断：

```
docker compose build        →  成功（重跑一次，见 §5.2）
docker compose up -d        →  容器 Up，0.0.0.0:8000->8000
/  /console  /api/health  /api/console/health   →  全部 200
```

`/api/console/health`：

```json
{"status":"ok","model":"gemini/gemini-3.1-flash-lite",
 "corpus_hash":"73224a81445a5258","dataset_hash":"1f7c2f65d6f95198",
 "case_count":3,"tool_registry":["search_docs"]}
```

**静态端点 200 不等于能跑**，所以又在容器里发了一次真实请求：

```
POST /api/chat  "How do I extend a video clip?"
  terminated_by : exhausted        loops/calls : 3/5        cost : $0.00254
  citations     : ['Luma Video Capabilities', 'Advanced Seedance 2.0 Workflows']
  version       : v1-baseline | arm: default | tag: None
```

LLM 调用、检索、成本记账、落库、`config_client` 解析全通。镜像 865MB。

### 5.1 缺 `.env` 时 `docker compose up` 硬失败（最严重的一处）

实测：把 `.env` 移开，`docker compose up -d` 直接报

```
env file /Users/fniu/Downloads/aicoding/.env not found: stat ...: no such file or directory
```

**容器根本不启动。** 这就是评审 clone 下来跑一条命令会看到的东西，而这条报错**完全没提「你缺的是一个 API key」**。

- **决定**：`docker-compose.yml` 里把 `env_file` 改成不强制存在，把需要的变量显式列进 `environment` 并从宿主环境透传。这样没有 `.env` 时容器**能起来**，然后在 §4.2 的启动期检查里以一条说人话的错误退出。
- **为什么这个顺序更好**：「容器起不来、报一个路径不存在」和「容器起来了、日志第一行告诉你缺哪个环境变量」，排查成本差一个量级。这跟 TO-22 是同一条原则——**崩要崩在离原因最近的地方**。

### 5.2 `uv:latest` 没有 pin —— 我违反了自己的 TO-05

第一次 `docker compose build` **失败了**：

```
#4 [internal] load metadata for ghcr.io/astral-sh/uv:latest
#4 ERROR: DeadlineExceeded: context deadline exceeded
failed to solve: DeadlineExceeded: context deadline exceeded
```

查了一下不是网络不通（`ghcr.io` 和 Docker Hub 都是 401 秒回，`docker pull` 单独跑 5 秒完成），是 buildkit 并发拉 metadata 时的偶发超时。重跑就过了。

但这暴露的问题比那次超时严重：

```6:6:Dockerfile
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
```

我在 TO-05 里花了一整段论证**不要用 `-latest` 别名**——「别名会漂，而漂移会伪装成『我的 prompt 改动导致了行为变化』，是所有风险里最难排查的一种」——然后在 Dockerfile 第 6 行用了 `uv:latest`。

- **决定**：按 digest pin（`docker pull` 已经拿到了：`sha256:606e70c71c852d03f611b1e56a195d08648507018a7057fab82c4974c4eae105`），并在旁边写一行注释说明为什么 pin。
- **为什么值得改这一行**：TO-05 那个论点如果只用在模型上、不用在构建上，它就只是一个论点，不是一条原则。**而且这一条是免费的。**

### 5.3 没有 `.dockerignore`

build context 是 179MB，其中 **176MB 是 `.venv`**，每次 build 都完整传给 daemon。加一个 `.dockerignore`（`.venv/`、`.git/`、`data/`、`__pycache__/`、`.env`）。

顺带是一层**安全兜底**：现在 `.env` 没被 COPY 进镜像纯粹因为 Dockerfile 是逐个目录 COPY 的（没有 `COPY . .`）。把 `.env` 写进 `.dockerignore`，这个保证就不再依赖「以后没人加一句 `COPY . .`」。

### 5.4 README 里的启动命令要复核

根 `README.md` 里写着 `uv run python -m ask_luma.cli init-db`，但 `init_db()` 在 app 的 lifespan 里就会跑。这一句是多余还是必要要确认（多一句无害，但一条不必要的步骤会让人怀疑其他步骤也可省）。同时 `.vscode/launch.json` 还指着 `ask_luma.main:app`，那个入口**只有 `/chat`，没有 `/console`**，改成 `server.main:app`。

---

## 6. 语言收口

### 6.1 扫描结果：代码是干净的

全仓扫 CJK（跳过 `.venv` / `.git` / `corpus` / `ai-discussion`）：

| 文件 | CJK 字数 |
| --- | --- |
| `apps/chatbot/README.md` | 1602 |
| `apps/console/README.md` | 1502 |
| `AGENTS.md` | 450 |

**`.py` / `.html` / `.yaml` / `.toml` / `.json` 里一个中文都没有。** `datasets/golden.yaml` 已经全英文（`dataset_hash` 从 `2ff1f9360032915f` 变成了 `1f7c2f65d6f95198`，改动已 commit）。

### 6.2 决定：`ai-discussion/` 之外全英文

- **决定**：上面三个文件全部翻成英文。`ai-discussion/` 下的设计文档保持简体中文。
- **为什么两个 app README 必须翻**：它们是题面那句「setup instructions that work in a fresh Linux container」的一部分。根 `README.md` 已经是英文，但它只给了一条 quickstart；真正把两个 app 各自怎么跑、端点是什么、边界在哪写清楚的是这两份。评审看不懂它们，就等于这两份不存在。
- **为什么 `AGENTS.md` 也翻**：它现在是**唯一一份自己就是规则、却违反规则**的文件——第 13 行写着「设计文档和讨论用简体中文。代码、注释、commit message、`APPROACH.md` 用英文」，而它自己是仓库约定不是设计文档。翻译时这条规则本身也要改成新的表述（`ai-discussion/` 中文，其余英文）。
- **`ai-discussion/` 为什么保持中文**：这是给你和我看的推演过程，不是交付物。根 README 已经明确标注了「Written in Chinese, and it is the honest version」，评审知道那里有什么、以及为什么不是英文。

### 6.3 翻译时连带要修的五处内容错误

这几处不是语言问题，是**内容已经过期**，借翻译一起修：

1. **`AGENTS.md` 自相矛盾的错误处理计数**。第 17 行「全项目只有两处错误处理」，第 22 行「全项目第三处、也是最后一处」。改成一处说三处，列全。
2. **TO-22 的标题**：「全程只有两处 try」，实际三处（Step 2 加了 `bench.py` 的逐 case 隔离，TO-22 正文的「边界」段已经预告了这一处）。标题跟着改。
3. **TO-14 选 YAML 的理由失效**：「`expect` 的正文是一整句**中文**判据，YAML 的 `|` 块标量比 XML 的单行挤压好读」。数据集已改英文。理由本身还成立（多行自然语言），但措辞要改。
4. **两份设计文档里的数据集示例是中文旧版**——精确位置已定位，一共 8 行：
   - `design_step2_console_with_benchmark.md` 第 248 / 250 / 252 / 264 / 266 / 279 / 281 行
   - `design_high_level.md` 第 155 行

   设计文档正文保持中文，但**引用的代码/数据必须和真实文件逐字一致**。这是根规则：中文是给人读的散文，不是给引用块用的。
5. **`design_high_level.md` 第 160 行的标题还写着「10 条 golden case 的覆盖设计」**，实际是 3 条（TO-13 里已经记了这次削减，但这个标题没跟着改）。

第 4、5 点值得单独说一句：一个主题是「消灭行为和你以为的不一致」的项目，文档里的示例和真实数据集不一致，是最不能留的一种瑕疵。它和代码里的行为漂移是同一种病——只是这次漂的是文档。

---

## 7. 提交物结构

### 7.1 题面要求逐条对表

| 题面要求（原文位置） | 现状 | 本步动作 |
| --- | --- | --- |
| Build your solution directly in this repo | ✅ 93 个文件已 commit，无未提交改动 | — |
| Setup instructions that work in a fresh Linux container | ⚠️ Docker 能跑，但缺 `.env` 硬失败、无 key 拿 502 | §4、§5 |
| If you use Docker, provide a `docker-compose.yml` for one-command setup | ✅ 存在且实测跑通 | §5.1 修硬伤 |
| `.env.example`，document any others | ⚠️ 存在，但只有 Gemini，没说明非 Gemini 怎么办 | §4.2 |
| **If your project is deployable, deploy it.** Include the URL in APPROACH.md | ❌ 未部署 | **明确不在本步**，另开一篇 |
| `APPROACH.md`（五个指定小节） | ❌ 不存在 | §7.2 |
| `video.md`（视频链接） | ❌ 不存在 | §7.3 |

### 7.2 `APPROACH.md` 的骨架

题面指定了五个小节，一个不能少、顺序照抄。英文。每一节列出要落进去的**具体内容**，避免写成空话：

**What you built and why**
- 一句话定位：一个 AI 产品 + 管理它行为变更的系统，后者才是主体，前者存在的意义是「被管理的那个东西」。
- 为什么把「变更单位」定成一份**六杠杆的行为配置**而不是一段 prompt（TO-06）。题面列了七个杠杆，那句话真正想说的是「变更不是单点的」。
- 为什么配置解析在 **critical path** 上（TO-07）——这是能回滚、能放量的唯一前提。

**Key decisions and tradeoffs**
- 只讲 §8.4 那 5 条主线，每条给出编号让人能自己去 `trade-offs.md` 查全部。
- **引用编号时用合并后的号**（§8.2）。别名行（§8.3）是为了让**历史文档**的引用不失效，不是给新写的文档用的——`APPROACH.md` 是这次交付的门面，里面的每个编号都该直接指向正文而不是一行转发。
- 必须包含 **fixed observation vs dynamic expectation**，并说明它是**代码上的事实**：`BenchResult.passed` 根本不读 `verdicts`。
- 必须包含 judge 用同一个模型这个**已知缺陷**及其两个独立后果（模型漂移作废历史基线、自我评价偏松），不能含糊成「为了简单」。

**What you intentionally left out**
- 灰度放量的控制面（§2）+ 按 tag 的检索切片（§3）——**并指出这两个在 UI 上都有 signpost，运行时已通**。
- production monitoring / alerting（TO-15），以及为什么这一层是商品化的、难的是产出结构化数据。
- 多轮对话（TO-01）、RAG（TO-02）、auth/RBAC（TO-04）、单元测试与前端构建链（TO-22）。
- 部署（另篇）。

**What breaks first under pressure**
不写空泛的「scale」，写**已经知道的具体断裂点**：
1. **15 RPM 的免费配额**。一次 Simulation 是 12–18 次调用；串行 + 20 秒节流之后一趟 50–80 秒。两个人同时点 Run 就开始撞 429。
2. **SQLite + 单进程**。TO-08 换来的是即时回滚，代价是没有进程级隔离。
3. **3 条 golden case 的统计意义**。TO-13 里已经承认了。真实的补法是从生产轨迹持续长测试集，不是一开始写一个大的——而 Production tab（§3）正是那条路的起点。
4. **judge 的自我评价偏袒**。已经用「advisory，代码上不读」挡住了，但它意味着**语义类回归有可能被放过去**。
5. **`cites_real_article` 的最长匹配是 O(标题数 × 文本长度)**。39 篇无所谓，几千篇要换 Aho-Corasick（TO-30）。

**What you'd build next**
按「我实际会照这个顺序做」排，而不是按功能大小：
1. 灰度控制面 + 健康度阈值 + 自动回滚（运行时已通，缺控制面和策略）
2. 从生产轨迹一键加 golden case（Production tab 已经把数据摆出来了）
3. 并排对比当前生效版本（TO-25 已经把数据模型留好了，只差一个读两次结果的页面）
4. judge 换一个不同家族的模型，并把它的版本号记进 `BenchRun`（TO-05 的推翻条件）
5. 部署

**外加一节（题面没要求，但这份提交最独特的东西在这里）——`How I directed the AI`**
题面第 34–38 行明确在看「how you directed them, where you pushed back」。有三个具体的、可验证的故事：
- **五次预测、五次全错**。Step 1 里我预测了五种「坏 prompt 会导致的回归」，实跑一条都没复现，最后那个高光 demo 是实测出来的，不是设计出来的（`design_step1_ai_app.md` §14.1）。
- **我的第一版 golden dataset 是全绿的，而它什么都没在防**。`BAD_SCOPE_V2` 三条全 pass，回归从整个数据集旁边走过去了。用两个只调单节点的探针脚本（省配额）重挑问法才修好（TO-29）。
- **引用检查因为错误的原因而通过**。按逗号切分把 `Run, Edit and Share Skills` 碎成片段，片段又碰巧子串匹配上，输出 `cited ['Character', 'Object Consistency']`：显示绿色，和坏掉没有区别（TO-30）。

这一节是**主动写进去的**，因为它回答的是题面真正在问的问题。前两个故事的共同点是：**我不相信自己的设计文档，去实跑了一遍，然后被证伪。** 这比任何一段架构描述都更能说明「AI 写代码、我负责决策」是什么意思。

### 7.3 `video.md`

按题面要求只放链接。脚本另开 `ai-discussion/video.md`（中文，给我自己用），**不进提交物**。5 分钟的分配草案：

| 时长 | 内容 |
| --- | --- |
| 0:00–0:30 | 一句话定位。指出 `/console` 才是主体 |
| 0:30–1:15 | `/chat` 问一个问题，展开轨迹：三轮检索、引用、成本、`terminated_by` |
| 1:15–2:45 | **高光**：改一行工具描述 → Simulation → 成本降了、延迟降了、答案更流畅 → 而它已经不检索了，在编。每个聚合指标都变好了，产品坏了 |
| 2:45–3:30 | Activate → 回到 `/chat` 同一个问题，行为变了，没重启没部署 → Activate 回去 |
| 3:30–4:15 | fixed vs dynamic：指代码，`passed` 不读 `verdicts`；judge 是同一个模型所以偏松 |
| 4:15–5:00 | 两个 signpost（运行时已通，缺控制面）+ 那个「全绿但什么都没防」的故事 |

### 7.4 交付前的检查清单

- [ ] **轮换 Gemini API key**（`.env` 已 gitignore、已确认 key 未进 git 历史，但仍要换）
- [ ] `git grep` 一遍确认没有任何凭据进版本库
- [ ] 干净 clone 到新目录，只按 `README.md` 的步骤走一遍，全程不看别的文档
- [ ] `docker compose up --build` 在**没有** `.env` 时给出说人话的错误
- [ ] 换一个非 Gemini 的 `MODEL` 跑通 `smoke.py`（§4.2 第 2 点）

---

## 8. trade-offs 收口

### 8.1 问题

30 条。demo 五分钟，讲不完，硬讲会变成念清单——而清单是**最不能体现判断力**的形式。

但直接删是错的：每一条都记录了一个真实的取舍，删掉就等于假装没做过这个决定。而且 `trade-offs.md` 第 3 行自己写了「plan 和最终的 `APPROACH.md` 都直接引用编号」，**编号是稳定编号**。

### 8.2 六组真合并（30 → 20）

有意思的是，六组里有**四组的正文自己就承认了**它是另一条的延伸——它们本来就是一条，只是分两次写下来的。这不是我事后归并，是当时写的时候就知道，只是没舍得合：

| 合并后 | 吸收 | 依据 |
| --- | --- | --- |
| **TO-22** 交付形态：能一口气读完、零构建跑起来 | TO-23（不写单测）、TO-24（`/chat` 无构建链）、TO-27（console 无构建链） | TO-27 正文第一句就是「沿用 TO-24 的路子」；四条的「为什么」是同一句话——能读懂比能扩展重要，而且干净容器里零构建更稳 |
| **TO-05** 模型这条轴整个不动 | TO-28（judge 用同一个模型） | TO-28 正文第一句就是「这是 TO-05 的延伸」 |
| **TO-08** 代码边界与进程边界是两件事 | TO-21（一个进程托两个 app） | TO-21 正文最后一句就是「修正了 TO-08 里『两个独立服务』的说法」 |
| **TO-10** 评测输出的形状 | TO-11（确定性优先）、TO-12（judge 会抖） | 同一个命题的三个面：输出逐条判定而非总分、blocking 的那部分必须确定性、judge 只做参考 |
| **TO-02** 语料与检索刻意做薄 | TO-03（静态快照） | 都是「检索质量不是本项目的题目」 |
| **TO-17** 只暴露结果，不暴露过程和素材 | TO-19（不开语料目录） | TO-19 正文写着「这跟 TO-17 是同一个取向」 |

合并省掉 10 条：30 → 20。加上本步新增的 TO-31（§4.2）= **21 条**。

**合并动作的具体规则**（避免合出一团糨糊）：

- 合并后的条目**保留全部子决定**，用小标题分节（比如 TO-22 下面四个小标题：错误处理 / 测试 / `/chat` 前端 / console 前端）。信息一条不丢，只是不再各占一个编号。
- **共同的「为什么」提到最前面写一次**，各自的「代价」留在自己的小节里。这才是合并的价值——四遍同样的理由压成一遍，读的人立刻看出这是一个取向而不是四个巧合。

### 8.3 编号是稳定编号：留别名，不删

被吸收的编号（TO-03、TO-11、TO-12、TO-14、TO-19、TO-21、TO-23、TO-24、TO-27、TO-28）**在原位置留一行**：

```markdown
### TO-27 console 前端同样不上构建链

> 已并入 [TO-22](#to-22-交付形态能一口气读完零构建跑起来)。编号保留，因为 design_step2 §15 引用了它。
```

- **为什么不直接删**——数过了，不是估的：仓库里（不含本文档）一共 **197 处** `TO-xx` 引用，其中指向这 10 个被吸收编号的有 **58 处**：

  | 编号 | 引用数 | | 编号 | 引用数 |
  | --- | --- | --- | --- | --- |
  | TO-12 | 9 | | TO-14 | 6 |
  | TO-21 | 8 | | TO-28 | 6 |
  | TO-23 | 8 | | TO-19 | 5 |
  | TO-11 | 4 | | TO-27 | 5 |
  | TO-24 | 4 | | TO-03 | 3 |

  删掉编号就是让这 58 处全部指向不存在的东西——而**「引用指向一个已经不在的东西」正是这个产品要消灭的那类问题**。留 10 行别名的成本是十行，收益是 58 处引用继续有效，并且**能看出合并这件事发生过**。
- 别名行的措辞要说明**为什么它曾经独立存在**（比如 TO-27 是 Step 2 时重新确认了一次 Step 1 的决定），否则合并会看起来像事后美化。

### 8.4 demo 主线：5 条

合并只解决文件清爽度，**不解决你的问题**——20 条在五分钟里还是说不完。真正解决的是在文件顶部加一层索引：**5 条主线，每条映射到它涵盖的编号。** demo 和 `APPROACH.md` 都只按主线讲，附录留给想深挖的人。

| 主线 | 涵盖 | demo 里怎么呈现 |
| --- | --- | --- |
| **1. 变更的单位是一份行为配置，而且它在 critical path 上** | TO-06, TO-07 | 改一个杠杆 → Save as version → Activate → 同一个问题行为变了。没重启、没部署、可回滚 |
| **2. blocking 的判定必须是确定性的，LLM judge 只能做参考** | TO-10（含 11/12）, TO-05（含 28） | 指代码：`BenchResult.passed` 根本不读 `verdicts`。judge 和被测是同一个模型，所以系统性偏松 |
| **3. 那次回归让每个聚合指标都变好了** | TO-05, TO-06, TO-02 | 改一行工具描述 → 成本降、延迟降、答案更流畅 → 而它已经不检索了，在编 |
| **4. 我的第一版数据集是全绿的，而它什么都没在防** | TO-29, TO-30, TO-13 | 探针脚本的故事 + `cited ['Character', 'Object Consistency']` 那个「因为错误的原因而通过」 |
| **5. 砍掉了什么，以及砍的理由** | TO-15（含 tag 查询）, TO-09（含灰度）, TO-22（含 23/24/27）, TO-01, TO-04 | 指 UI 上那两个 signpost：运行时已通，缺的是控制面和策略 |

主线 3 和主线 4 是这份提交里最独特的两段，**都不是设计出来的，是实跑出来被证伪之后剩下的东西**。它们应该占 demo 的最大比重。

---

## 9. 本步对 trade-offs 的改动汇总

| 条目 | 动作 |
| --- | --- |
| **TO-31**（新，D 组） | `MODEL` 跨 provider 可换，但仍不是版本化杠杆。含价格表、`responseSchema` 等价性待验、启动期 key 检查；说清和 TO-05 的分工（部署级设置 vs 产品级变更单位） |
| **TO-09** 补 | 灰度：分桶运行时已实现且每个请求都在走；控制面和放量策略明确不做，做成禁用控件；不插 `Experiment` 行的三个理由（§2.3） |
| **TO-15** 补 | 原文的「按 tag 抽取生产对话」再砍一刀，只做不带筛选的只读 Production tab；核心论点不变，且现在有证据 |
| **TO-16** 补 | seed 的交付形态：可提交的 JSON fixture + 幂等灌库脚本，不提交 `.db`（`data/` 已 gitignore） |
| **TO-05** 补 | 「评审跑不起来」这个风险的**实际缓解**（原文只写了要在文档里说明）；吸收 TO-28 |
| **TO-14** 修 | 选 YAML 的理由里「中文判据」失效，改措辞。随后并入 TO-13 |
| **TO-22** 修 + 合 | 标题「只有两处 try」改为三处；吸收 TO-23 / TO-24 / TO-27 |
| **TO-02 / TO-08 / TO-10 / TO-17** 合 | 按 §8.2 吸收各自的条目 |
| 被吸收的 10 个编号 | 原位留别名行（§8.3） |
| 文件顶部 | 加 §8.4 那张「demo 主线 5 条」索引表 |

---

## 10. 验收清单

每条都要有一个**能跑的命令或一个能看的东西**，不接受「看起来对了」。

**Signpost**

1. `/console` 左栏出现 Rollout 区块，滑块和两个选择器都是灰态，tooltip 说明「运行时已通、缺控制面」；点击无任何反应，控制台无报错。
2. `/console` 右栏出现 Production tab，展示**真实**对话行，`version_label` / `config_hash` / `arm` / `terminated_by` 四列有值；点一行能展开完整轨迹。
3. 在 `/chat` 问一个新问题，**刷新 Production tab 能看到新增的那一行**（证明它读的是真数据，不是 fixture）。
4. Activate 一个不同版本后再问同一个问题，Production tab 里两行的 `version_label` 和 `config_hash` **不同**。
5. `sqlite3 data/app.db "select count(*) from experiment"` 返回 **0**（证明 §2.3 那条没有被偷偷违反）。

**跨 provider**

6. `MODEL=<非 Gemini 型号>` 跑 `scripts/smoke.py`，4/4 通过，且**成本不是 0**。
7. 同样配置跑一次 Simulation，三条 case 有结果——重点看 `responseSchema` 的等价性，如果 `plan`/`reflect` 抛 `ValidationError`，TO-20 的论证在这个 provider 上不成立，必须写进 §11 而不是悄悄放过。
8. 清掉对应的 key，**启动期**就崩，错误信息里点名缺哪个环境变量。

**seed**

9. 删掉 `data/app.db`，跑 seed 脚本，`/console` 三个 tab 和 Production tab **都有内容**，Simulation 历史下拉框里有一次 run。
10. seed 脚本连跑两次，数据**不翻倍**（幂等）。
11. seed 出来的行在 UI 上可辨认，不会被误认为刚跑出来的。

**Docker**

12. 干净 clone 到新目录 → `docker compose up --build` → `/` 和 `/console` 都 200 → 在容器里问一个问题拿到真实回答。
13. **没有** `.env` 时容器**能起来**，并在日志里给出说人话的缺 key 错误。
14. `Dockerfile` 里 `uv` 按 digest pin；`.dockerignore` 存在，build context 从 179MB 降到 < 5MB。

**语言**

15. 全仓扫 CJK（跳过 `ai-discussion/`）→ **零命中**。
16. `rg 'expect: [^A-Za-z]' ai-discussion/` → **零命中**（现在有 8 处，§6.3 第 4 点）。两份文档的数据集示例与 `datasets/golden.yaml` 逐字一致。
17. `design_high_level.md` 里不再有「10 条 golden case」这个标题。
18. `rg -o 'TO-\d+'` 通扫全仓，每个被引用的编号在 `trade-offs.md` 里都能找到落点（别名行也算）。

**提交物**

19. `APPROACH.md` 存在，题面那五个小节标题**逐字对得上**，外加 `How I directed the AI`。
20. `video.md` 存在。
21. `git grep` 找不到任何凭据；key 已轮换。
22. `.vscode/launch.json` 指向 `server.main:app`（不是只有 `/chat` 的 `ask_luma.main:app`）。

---

## 11. 风险

| 风险 | 判断 |
| --- | --- |
| **换 provider 后 `responseSchema` 不等价** | **本步最大的技术未知数。** TO-20 的整个论证建立在「结构化输出删掉了格式错误这一整类失败」上；如果某个 provider 是靠 prompt 里塞 JSON 说明来模拟，格式错误会回来，而 TO-22 说了直接抛——评审换个 model 就撞 502。验收 7 就是为这条设的。如果实测不等价，**诚实的做法是在 README 里限定「已验证过的 model 列表」**，而不是声称支持所有 provider |
| **seed fixture 和代码漂移** | prompt 常量一改，fixture 里的 `config_hash` 就对不上任何 `Version`。跟 TO-26 处理过的是同一类问题。缓解：seed 幂等 + UI 上可辨认 + 交付前跑一次验收 9 |
| **Production tab 的 payload** | `/api/conversations` 返回整行含完整 `trajectory`。20 行就不小。本步不改端点（不动 Step 1 已验收的代码），只在前端取需要的字段，「该给列表页做精简投影」记在这里 |
| **禁用控件被点** | 一定有人点。tooltip 必须直接说明原因，不能只是灰着 |
| **合并 trade-off 引入交叉引用错误** | 20 条里每条都可能引用被吸收的编号。合并后要通扫一遍 `TO-\d+` 引用，确认每个指向的位置都还在 |
| **翻译 README 时把内容改坏** | 两份 README 有 3000 多字，翻译时容易顺手「优化」掉一些精确的技术表述。原则：**先直译，再单独修 §6.3 列出的四处内容错误**，两件事不要混在一次编辑里 |
| **ghcr.io 在评审机器上更慢** | 本机首次 build 就超时过一次。按 digest pin 不解决慢，只解决漂。如果这条风险要彻底消掉，就得改成 `pip install uv`（多一层但只依赖 PyPI）。**本步不改**，记在这里 |

---

## 12. 明确不做

- **部署**（另开一篇；顺序是收口 → demo → 改 → 部署）
- 灰度放量的控制面、健康度阈值、自动回滚**策略**
- 按 tag 的检索、切片、arm 对比视图
- 生产对话一键加进 golden dataset
- 定时 judge 复跑、告警、趋势图、报表（TO-15 原样保留）
- 并排对比当前生效版本（TO-25 原样保留）
- 换一个不同家族的模型当 judge（TO-05 的推翻条件，记在「What you'd build next」）
- 任何新的产品行为能力、任何新的杠杆

---

## 13. 实施结果（本节在实现之后补写）

计划和现实有四处不一样，都记在这里，因为「文档和代码互相说谎」正是 §0 列的第三笔债。

### 13.1 验收 6 和 7 没能做：手上没有 Anthropic / OpenAI 的 key

这是本步**唯一没做到的验收项**，而且恰好是 §11 列为「最大技术未知数」的那一条。环境里只有 `GEMINI_API_KEY`（`GOOGLE_CLOUD_*` 是 Vertex 的，不是同一套凭据），所以 `responseSchema` 跨 provider 是否等价**完全没有被验证过**。

按 §11 定的规则处理——「诚实的做法是在 README 里限定已验证过的 model 列表」。落地成三处措辞：`.env.example` 里三个型号分别标 `verified end to end` / `wired, not verified`，两份 README 和 `APPROACH.md` 一律写「wired, not verified」而**不是 supported**，并明确点出如果 `plan` / `reflect` 抛 `ValidationError` 就是这个原因。TO-31 的「代价」小节把它写成两条独立的代价（价格数字没实测 token 计费、这两条路一次都没跑过），不合并成一句含糊的「可能有问题」。

**声称一条没跑过的路可用，比不声称更糟**——这跟 TO-30 那个「因为错误的原因而通过」是同一类问题：看起来是绿的，而绿是假的。

### 13.2 实现时踩到的两个真 bug

两个都是「我以为对、跑一下发现不对」，和 §0 的主题同源。

1. **`Conversation` 没有 `version_label` 列。** Production tab 的第一版直接读 `row.version_label`，而这张表存的是 `version_id`——label 是 console 的说法、可以改名，id 才是实际发生的事。改成拿前端已经在内存里的版本列表反查，`config_hash` 无论如何都显示。**这个 bug 是靠把渲染器读的每个字段对着真实 API 响应逐个核对发现的**，不是靠读代码读出来的。
2. **seed 的 datetime 和加载顺序，两个叠在一起。** `model_dump_json()` 把 datetime 序列化成 ISO 字符串，而 SQLModel 的 `table=True` 类不做构造时校验，字符串一路怼到 DateTime 列、在离原因好几帧的地方炸；另外 `load()` 一开头就调 `init_db()`，于是 `seed_baseline()` 在空表上先插了一行同 hash 的 baseline，fixture 再插一行，**两行都声称 active**。改成「建表 → 灌 fixture → 最后跑 `seed_baseline()`」，让它认出 fixture 里那行就是代码持有的 hash。

还有一个设计层的错：`export()` 原本按「哪个 `dataset_hash` 的 run 最多」判断当前数据集，而**最旧的那代数据集 run 最多**——结果按 `dataset_hash` 缓存，不再变动的数据集反而攒得多。改成直接读 `dataset.load().hash`。

### 13.3 fixture 是重跑出来的，不是从旧数据里挑的

库里 5 次历史 run 没有一次的 `dataset_hash` 对得上当前数据集（数据集前后改过两轮：`7624dd56…` → `2ff1f936…` → `1f7c2f65…`）。所以先重跑 baseline 和 `bad-scope` 两趟，再导出。

顺带确认了一件事：**数据集改成英文没有削弱它**。`bad-scope` 依然是 2/3，`covered` 依然挂在 `terminated_by` 和 `cites_real_article` 上——因为 `passed` 只读 `observations`，而这次改动只碰了 judge 用的 `expect` 文本。这是 TO-10 那个两段式分离的直接证据。

### 13.4 实测数字

| 项 | 结果 |
| --- | --- |
| build context | 179MB → **4.85kB** |
| 无 `.env` 时 | 容器**能起**，退出码 3，日志末尾点名 `GEMINI_API_KEY` |
| 容器内真实提问 | `answered`，1 轮 3 次调用，$0.000772，2104ms |
| `experiment` 表 | **0 行**（§2.3 没被偷偷违反） |
| 全新库 + seed | 4 版本恰好 1 个 active、2 次 run 进历史下拉、3 条对话带 `seeded` 标记 |
| seed 连跑两次 | 全部 `+0`，不翻倍 |
| trade-offs | 30 → **21 条实质条目 + 10 行别名**；31 个编号全部可解析，21 个内部锚点全部命中 |
| CJK 扫描（跳过 `ai-discussion/`） | 零命中 |
| `check_assertions.py` | 7/7 |
| `launch.json` | 本来就已经指向 `server.main:app`，验收 22 无需改动 |

### 13.5 §2.5 的实施结果（杠杆六 → 四）

| 项 | 结果 |
| --- | --- |
| `config_hash` | baseline `c64bbc62a755c53d` → **`ea2580ac6b707853`**；bad-scope `78b09295ca8ea47a` → **`a206518b2f616f03`** |
| 四杠杆下重跑回归 | baseline **3/3** $0.002935、bad-scope **2/3** $0.002527 —— **回归照样被抓到**，说明这次砍的不是检测能力 |
| `check_assertions.py` | 7/7（`passed` 仍然只读 observations） |
| fixture 重导 | 1 版本 / 2 run / 3 对话 / 6 结果，全部在新 `config_hash` 下；连跑两次全 `+0` |
| judge temperature | `JUDGE_TEMPERATURE = 0.0` 保住了，和 agent 的 0.2 是两个不同的值 |

**踩到的三件事：**

1. **先改代码后重建容器会炸，顺序反了。** 我第一次想用还跑着旧代码的容器去生成新对话——旧的 `BehaviorConfig` 要求六个字段，而 `init_db()` 已经把 active 版本换成四字段的了，`BehaviorConfig(**active.config)` 直接 ValidationError。正确顺序是**先重建容器再生成数据**。（实际没炸，因为脚本先死在别的地方，见下条。）
2. **heredoc 里 `load_dotenv()` 会 AssertionError**（`find_dotenv` 要读调用栈的上一帧，stdin 里没有）。这个坑 Step 1 踩过一次，这次又踩了——所以这回落成了文件 `scripts/seed_conversations.py`，不再用 heredoc。
3. **`/api/chat` 的响应里没有 `config_hash`。** 它只往库里写，响应里给的是 `version_label`。写脚本时想当然了，`KeyError` 才发现。这不是 bug——`config_hash` 是行上的事实，而响应是给前端看的——但值得记一笔。

**export 顺手改了两处**（原来会把我攒的全部历史倒进 fixture）：只导每个 label **最新**的一次 run，只导被真正引用到的版本。改之前重导出来是 4 个版本 / 4 次 run，其中两次指向代码已经产不出来的六字段配置。
