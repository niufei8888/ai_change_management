# Design Step 5：Prepare for submission

> 本步不改产品行为。全部改动落在交付物上：AI session history 的打包、`APPROACH.md` 的收口、以及一份提交前必须逐条走完的清单。

---

## 0. 为什么需要单独一步

前四步做完之后，很容易以为「代码写完了就等于可以提交了」。不是。题面（`question.md`）的交付要求有三项，其中两项现在还不成立：

| 交付项 | 题面原话 | 现状 |
| --- | --- | --- |
| Working software | 要能在 fresh Linux container 里跑，有 `docker-compose.yml` | **成立** |
| 部署 | 「If your project is deployable, deploy it… **Include the URL in your APPROACH.md**」 | **不成立**——`APPROACH.md` 和 `README.md` 里还是 `<!-- RENDER_URL -->` 占位符 |
| APPROACH.md | 五个小标题 | 结构齐了，但**有几处数字已经过期**，而且「What you'd build next」的第 6 条还写着「Deploy it.」 |
| Video walkthrough | ~5 分钟，链接放 `video.md` | 待录（你自己准备），`video.md` 里的时间轴已经写好 |

再加一件题面**没有**要求、但要一起交的东西：**AI session history**。这一项的处理方式需要单独设计，因为它不是「把文件复制过去」那么简单——见 §2 和 §3。

---

## 1. 本步的范围

**做：**

1. **打包 AI session history**：脱敏、渲染成人能读的形式、配一份英文导读。
2. **收口 `APPROACH.md`**：填线上链接、修过期数字、删掉已经做完的「下一步」、把 session history 接进「How I directed the AI」。
3. **清掉 `<!-- RENDER_URL -->`**（两个文件）。
4. **写一份提交前清单**，包括**必须由你手动做**的那几件。

**明确不做：**

- **不运行 `ai-discussion/submit.sh`。** 你说了它只是 context。而且它本身只是个 bootstrap——真正的打包逻辑是从 `take-home-service.lumalabs-ext.workers.dev` 下载下来再执行的，脚本里看不到它会收集什么。这条限制直接影响 §2 的结论。
- 不动任何产品代码、prompt、dataset。这一步如果改了行为，前面所有 hash 和验收结论都要重跑。

---

## 2. 一个必须先解决的问题：真 key 在 transcript 里

**这是本步最重要的发现，而且它改变了 [TO-34](trade-offs.md) 的结论。**

### 2.1 事实

主 conversation 的 transcript 里**存在一个可用的 Gemini API key**。它出现在一条我自己跑过的 `curl` 命令里（`-H 'X-goog-api-key: AQ.…'`）。

**它的前缀是 `AQ.`，不是 `AIza`。** 这一点很要紧：`AIza…` 是 Google API key 的经典形状，几乎所有现成的 secret 扫描规则、包括我第一次自己写的检查，认的都是它。我第一遍用 `AIza[0-9A-Za-z_-]{20,}` 扫了全部 6 份 transcript，结果是 **0 命中**，一度以为是干净的。是改用「endpoint 出现位置的上下文」再看一遍才发现的。

**结论：一个只认 `AIza` 的脱敏规则会把这个 key 原样发出去，并且脱敏脚本会打印「0 secrets found」向你确认它是安全的。** 这跟 [TO-30](trade-offs.md) 记录的那件事是同一类错误——**检查因为错误的原因通过**，而这种失败不会被看见。

### 2.2 为什么「我们自己脱敏」不足以解决它

我们能控制的只有**我们放进仓库的那一份**。但 `submit.sh` 的真实逻辑是远端下载的，我看不到它收集什么。现在的 take-home 提交工具**普遍会自动抓取 AI 编码工具的会话记录**（`~/.cursor/`、`~/.claude/` 之类），这也正好解释了你为什么会提到「AI session history」这件事。

也就是说：**很可能有一份我们没有经手、也没有脱敏的 transcript 副本会被一起打包上传。** 在那种情况下，仓库里那份脱敏得再干净也没用。

### 2.3 我建议提交前轮换；**已决定不轮换**

我原本的建议是**在提交前就轮换 key**：在 AI Studio 里废掉旧的、生成新的、填进 Render 和本地 `.env`，评审结束后再注销新的那一个。这样「可能泄露的那个」和「评审要用的那个」是两个不同的字符串，我们控制不到的那份 transcript 副本也一起失效。代价只是多轮换一次、多等一次重新部署。

**决定是不轮换**，维持 [TO-34](trade-offs.md) 原来的做法：评审结束后一次性注销。

按项目惯例把被否决的论证留在这里，而不是删掉重写。这条决定意味着：

- **我们脱敏的这一份，是唯一在我们控制之内的防线。** 所以 §3.4 的脱敏不是「顺手做一下」，它是这一条风险的**全部**处理措施，必须做实、并且在产物上验证。
- **仍然存在一份我们碰不到的副本的可能性**（§2.2）。如果 `submit.sh` 的远端逻辑真的会自动抓 `~/.cursor/`，那么在 key 被注销之前，它是有效的。这一点被明确接受了，写在这里是为了它是一个**已知**风险而不是一个被忽略的风险。
- **注销这一步的优先级因此变高了。** 原来它只是「省钱」，现在它同时是那份凭据的唯一失效途径。评审一结束就做，不要拖。

---

## 3. AI session history 怎么打包

### 3.1 有哪些 conversation

这台机器上一共 5 个（外加 1 个我在本轮启动的子 agent）：

| id 前缀 | 行数 | 时间 | 内容 |
| --- | --- | --- | --- |
| `e8826cd9` | 1138 | 7/28–7/30 | **主线**。从读题、定 scope，到 step 1–4 的全部设计与实现 |
| `165b1b39` | 171 | 7/28 | 澄清题面（`model routing` / `post-processing` 指什么）→ 后来变成部署平台的调研 |
| `d8060b68` | 44 | 7/30 | 5 分钟 demo 的讲法，最后产出英文 transcript |
| `c5563573` | 12 | 7/28 | 一句话提问：「灰度」的英文是什么 |
| `406c5ba3` | 8 | 7/28 | 起草一封给 recruiter 的邮件 |

### 3.1.1 会话标题在哪、以及「QQ」是哪个

`agent-transcripts/` 目录里只有 uuid 命名的 jsonl，**没有任何 title 元数据**，所以光看这个目录认不出「叫 QQ 的那个」。标题实际存在

```
~/Library/Application Support/Cursor/User/globalStorage/state.vscdb
```

的 `cursorDiskKV` 表里，key 形如 `composerData:<uuid>`，value 是 JSON，`name` 字段就是标题。查出来是：

| 标题 | id | 消息数 |
| --- | --- | --- |
| `planning` | `e8826cd9` | 1859 |
| **`qq`** | **`165b1b39`** | 270 |
| `demo` | `d8060b68` | 91 |
| `灰度含义与英文` | `c5563573` | 15 |
| `Recruiter email confirmation` | `406c5ba3` | 10 |

所以「planning」和「QQ」就是这两个标题的字面意思。（给出的 `48cc7e0e-…` 是一条消息的 bubble id，DB 里没有以它命名的会话；它被引用在 `165b1b39` 内部，与结论一致。）

### 3.1.2 决定的范围：只放这两个

**只打包 `planning` + `qq`。** `demo`、`灰度含义与英文`、`Recruiter email confirmation` 都不放。

我原本建议把 `demo`（demo 叙事的推敲过程）和 `qq` 一起放——后者恰好就是被选中的那个。留下这句是为了说明**被舍掉的是什么**：`demo` 那个会话显示 5 分钟的讲法不是随手定的；不放它，视频的叙事在书面材料里就没有来源。这是一个已知的、接受了的缺口。`Recruiter email confirmation` 讲的是怎么跟 recruiter 沟通、不是这个产品，本来就不该放。

### 3.2 形态：原始 + 渲染 + 英文导读，三样都要

**问题**：主 transcript 是 1.9MB / 1138 行 JSONL，其中有单行极长。**没有人会读它。** 而这份东西存在的意义恰恰是当证据用的——题面的评分点第二条是 *how you directed them, where you pushed back*。**没人读的证据不是证据。**

| 方案 | 优点 | 缺点 |
| --- | --- | --- |
| A. 只交原始 JSONL | 完整、可核验、无剪裁嫌疑 | 实际不可读，等于没交 |
| B. 只交整理好的 Markdown | 可读 | **是我挑的**，天然招来「你只挑了好看的部分」 |
| C. 原始 + 机械渲染 + 英文导读 | 兼顾 | 仓库里多几 MB |

**选 C**，但关键在一个细节上：**渲染必须是机械的，而且渲染脚本要一起提交**（`scripts/export_sessions.py`）。这一条不是为了工程整洁，是为了让「我没有挑选」变成一句**可被检验**的话——对方可以拿脚本对着原始 jsonl 重跑一遍，比对输出。一份手工整理的 Markdown 做不到这件事，而这个项目从头到尾在讲的就是「别相信声明，去跑一遍」。

### 3.3 语言问题，这条必须正面处理

**整个 planning conversation 的 user 那一侧是中文的**（因为你的语言偏好），assistant 那一侧是英文。

这意味着：一个只读英文的评审，从这份记录里能看到我的回答，**看不到你的指令**——而正在被评分的恰好是后者。「how you directed the tools」这条评分点，证据全在中文那一侧。

三个选择：

| 方案 | 判断 |
| --- | --- |
| 原样交，不解释 | 否决。等于交了一份对方读不了的东西还不说明 |
| 原样交 + **英文导读** | **推荐** |
| 全文翻译 | 否决。量大，而且**翻译过的证据就不是证据了**——它变成了我的转述 |

**英文导读**（`ai-sessions/README.md`）要做三件事：

1. 说清每个 conversation 是什么、什么时间、多长。
2. **把真正起作用的那十来条中文指令逐条摘出来，原文 + 英译并列**，每条注明它改变了什么。比如「工具轮次的边界要 align 一下……我们限制这个 loop 不超过 3 次……就是要诚实」这一条，直接决定了 ReAct 循环的形态和 `terminated_by` 的语义。
3. **坦率说明这是原始记录，包含走错的路。** `APPROACH.md` 第 41 行对 `ai-discussion/` 已经是这个口径（"a working record rather than a deliverable, and it is honest in a way a polished writeup is not"），这里保持一致。

### 3.4 脱敏：按形状 + 按真值，双管

脚本要做的替换，按重要性排：

1. **`.env` 里每个值的字面量**——运行时读 `.env`，把里面出现的每个值替换掉。这是唯一能保证「这台机器上的真凭据」都被覆盖的做法，不依赖我猜对形状。
2. **形状匹配兜底**：`AQ\.[\w.-]{20,}`、`AIza[\w-]{20,}`、`sk-[\w-]{20,}`、`ghp_\w+`，以及 `submit.sh` 里那个 token。兜底是为了防「曾经用过、现在已经不在 `.env` 里」的旧值。
3. **绝对路径** `/Users/fniu/…` → `<repo>/…`。不是安全问题，是别把本机目录结构和用户名一起交出去。

**验证必须在产物上做，不在输入上做。** 脚本跑完之后，对**输出文件**再扫一遍上面所有规则，命中数必须为 0，否则非零退出。§2.1 那个教训就是这么来的：在输入上「找不到」不等于安全，只等于我的规则不对。

### 3.5 一处得承认的张力

`APPROACH.md` 有一节叫「Small enough to read in one sitting」。往仓库里塞几 MB 的 transcript，跟这句话是有点冲的。

**处理方式是分区而不是辩解**：session history 单独一个顶层目录 `ai-sessions/`，`README.md` 第一句就说明这不在阅读路径上。「小到能一口气读完」说的是**产品代码**；交付证据不受这条约束，但也不该混进去。

---

## 4. `APPROACH.md` 要改的地方

结构上五个小标题都齐（还多一节 "How I directed the AI"，正好对着题面的第二条评分点）。要改的是内容：

### 4.1 过期的数字

| 位置 | 现在写的 | 实际 |
| --- | --- | --- |
| 「What working software means here」 | 2,983 lines of Python | **3,151** |
| 同上 | 1,340 lines of hand-written frontend | **1,542** |
| 「Key decisions and tradeoffs」开头 | There are 21 numbered decisions | **24**（34 个标题减去 10 条并入别处的别名） |

这三处单独看都是小事，但**它们是最容易被抓到的一类错误**——一个说自己「用可验证的断言代替文档声明」的项目，正文里的数字对不上，读起来就是没走完最后一遍。

### 4.2 「What you'd build next」的第 6 条是「Deploy it.」

已经做完了。留着直接自相矛盾：文档第一行写着 live 链接，最后又把部署列为「接下来要做的」。删掉。

### 4.3 线上链接

`APPROACH.md:3` 和 `README.md` 的 Live 段落各有一处 `<!-- RENDER_URL -->`。`rg -n RENDER_URL` 能找全。

### 4.4 接进 session history

「How I directed the AI」现在讲了三个故事（五次预测全部没复现、golden dataset 全绿却什么都拦不住、引用检查因为错误的原因通过）。这三个故事**在 transcript 里都有对应的原始过程**。加一句指向 `ai-sessions/`，让读者可以从结论走到证据。

---

## 5. 其他文件

- **`video.md`**：链接位留着，你录完填。时间轴已经写好，**但它现在没提部署**。5 分钟很紧，我倾向不加——线上链接在 `APPROACH.md` 第一行，不需要占视频时间。
- **`README.md`**：除了 `RENDER_URL`，其余不动。
- **`ai-discussion/submit.sh`**：留在仓库里当记录，不动、不跑。
- **`ai-discussion/Untitled`**：一个 1 行的空文件，看着像误建的。建议删。

---

## 6. 提交前清单

分成两半：**我能做的**和**必须你做的**。

### 6.1 我做（已完成，见 §8）

1. `scripts/export_sessions.py`：读 jsonl → 脱敏 → 渲染 Markdown → 在产物上验证 0 命中
2. `ai-sessions/`：原始（脱敏后）jsonl + 渲染出的 Markdown + 英文 `README.md` 导读
3. `APPROACH.md`：§4 的四项
4. `README.md`：布局、设计记录索引、条数
5. 删 `ai-discussion/Untitled`
6. [TO-34](trade-offs.md) 补这条新暴露；新增 TO-35 记 session history 的形态选择
7. 全仓再扫一遍凭据形状，必须 0 命中

### 6.2 你做

1. ~~轮换 Gemini key~~ —— 已决定不做（§2.3），改为评审结束后立刻注销
2. ~~清空 Render 面板的 Docker Command~~ —— **已完成**
3. ~~把线上 URL 给我~~ —— **已完成**，<https://ai-change-management.onrender.com>，两处占位符已填
4. **面板 Environment 里加 `SEED_DEMO=1`** —— 新增的一条，理由见 §8.4。**不做的话文档里有两句话是假的**
5. 录视频，链接填 `video.md`
6. 评审结束后注销 Gemini key（优先级见 [TO-34](trade-offs.md) 的 Step 5 补充）

### 6.3 提交前最后一次自检（建议按顺序）

| # | 项 | 怎么验 |
| --- | --- | --- |
| 1 | 干净克隆能跑起来 | `git clone` 到新目录 → 填 `.env` → `docker compose up --build` |
| 2 | 交付物里没有凭据 | 对 `ai-sessions/` 和全仓跑 §3.4 的全部规则，0 命中 |
| 3 | 没有占位符残留 | `rg -n 'RENDER_URL\|_\(pending\)_'` 应为空 |
| 4 | 线上活着 | 三个端点 200，且真问一个问题能答 |
| 5 | 断言与冒烟仍然绿 | `check_assertions.py` 7/7、`smoke.py` 4/4 |
| 6 | 文档内部引用不断 | 全部 `TO-\d+` 有对应标题、锚点可达 |
| 7 | 视频链接在 `video.md` 里 | 肉眼 |

---

## 7. 本步对 trade-offs 的改动

- **[TO-34](trade-offs.md) 补一段**：原文的封顶机制是「评审结束后注销 key」。现在要加上**交付物本身会带着 key 离开这台机器**这条新暴露，所以顺序变成「**提交前轮换，评审后注销**」。同时记下 §2.1 那个教训：`AQ.` 前缀让只认 `AIza` 的规则静默失效，而它失效的方式是**报告安全**。
- **新增 TO-35**：交付 AI session history 的形态——为什么是「原始 + 机械渲染 + 英文导读」而不是只交一种；为什么渲染脚本必须一起提交（让「没有剪裁」可被检验）；为什么**不翻译全文**（翻译过的证据是转述）；以及承认它和「小到能一口气读完」之间的张力，用分目录而不是辩解来处理。

---

## 8. 实施结果

### 8.1 文件

| 文件 | 动作 | 说明 |
| --- | --- | --- |
| `scripts/export_sessions.py` | 新增 | 220 行。docstring 穷举了它做的每一种变换 |
| `ai-sessions/README.md` | 新增 | 英文导读，11 条关键指令原文 + 英译 + 落点 |
| `ai-sessions/planning.md` | 生成 | 616 KB，27 条我的指令 |
| `ai-sessions/qq.md` | 生成 | 112 KB，21 条 |
| `ai-sessions/raw/*.jsonl` | 生成 | 脱敏后仍是合法 JSONL（1138 / 171 行，0 条解析失败） |
| `APPROACH.md` | 改 | 三处过期数字、删掉「Deploy it.」、接进 `ai-sessions/` |
| `README.md` | 改 | 布局加 `ai-sessions/`、设计记录补 step4/step5、21→24 |
| `ai-discussion/trade-offs.md` | 改 | TO-34 补一段、新增 TO-35、索引 21→24 |
| `ai-discussion/Untitled` | — | 已经不在了，无需删 |

### 8.2 渲染出来之后才发现的两件事

**一、user turn 有重复。** Cursor 会把同一条 user 消息写两遍（一次纯文本、一次带附件）。第一版渲染出来 `planning` 有 61 条「我的」发言，里面 8 对是重复的。

**二、约三分之一的「user turn」不是我说的话。** `Briefly inform the user about the task result and perform any follow-up actions (if needed).` 这一句在 `planning` 里出现了 20 多次——它是 harness 在后台任务结束后塞进 user 槽位、让 agent 继续跑的提示。原样交出去，读者会以为我在反复说一句莫名其妙的英文。

两条都按**显式清单**处理（`BOILERPLATE` 常量 + 相邻去重），而不是靠启发式判断，理由和 §3.2 一样：变换必须可被检验。清理后 `planning` 27 条、`qq` 21 条，合计 **48 条真实指令**——逐条核对过，没有实质内容被误删。

### 8.3 验收

| # | 项 | 结果 |
| --- | --- | --- |
| 1 | 脱敏在产物上验证 | **0 命中**（2 个 `.env` 真值 + 6 条形状规则） |
| 2 | 脱敏**确实触发过**（反向检查） | planning 36 处、qq 5 处 `<REDACTED>`；key 所在的 `X-goog-api-key:` 位置已替换 |
| 3 | `$GEMINI_API_KEY` 这类**引用**未被误伤 | 是，只有字面量被换 |
| 4 | 脱敏后 raw 仍是合法 JSONL | 1138 / 171 行，0 条解析失败 |
| 5 | 全仓无凭据形状 | 0 命中（`.env` 自身除外，已 gitignore） |
| 6 | `ai-sessions/` 无本机绝对路径 | 0 命中 |
| 7 | 35 个 `TO-xx` 引用全部有定义 | 35/35 |
| 8 | 新脚本无 lint / 无未用 import | 干净 |
| 9 | 占位符只剩该剩的 | `RENDER_URL` 两处 + `video.md` 一处，都等外部输入 |

第 2 条是这一步里最该有的一条检查。**「0 命中」单独看是不可信的**——它既可能意味着脱敏成功，也可能意味着脱敏根本没跑。只有再证明它确实替换过东西，两条合起来才说明问题。这跟 [TO-30](trade-offs.md) 是同一个道理。

### 8.4 线上验收：[design_step4](design_step4_deploy.md) 遗留的第 9、10 条，以及一个新问题

URL 到手、面板的 Docker Command 清空之后，step 4 里那两条只能在线上验的项目补完了。地址 <https://ai-change-management.onrender.com>。

| # | 项 | 结果 |
| --- | --- | --- |
| 9 | 三个端点在 Render 上 200 | `/api/health` `/console` `/` 全 200，都在 0.2s 内（实例已醒） |
| — | `corpus_hash` 与本地一致 | `73224a81445a5258`，39 篇 / 406 chunk ✓ |
| — | **恰好一条 active version** | 1 条，`v1-baseline` / `ea2580ac6b707853` ✓ |
| 10 | 真问一个问题、并出现在 Production tab | `terminated_by=answered`、2246ms、$0.00089、两条真引用；Production tab 里能看到，带 version / arm / `terminated_by` ✓ |
| — | **seed 的 demo 数据在不在** | **不在。runs 为空。** |

顺手一个小坑：`/api/console/versions` 返回的字段是 `status: "active"`，不是 `is_active`。我第一次按 `is_active` 判断，得到「0 active」并据此报了 FAIL——**判据写错，结论是假警报**。和 [TO-30](trade-offs.md) 是同一类，只是这次错向安全的一侧。

**最后一行才是真问题，而它的成因值得完整写下来。**

不是代码问题：fixture 在镜像里（`docker run --entrypoint ls` 确认 `/app/datasets/demo_seed.json` 存在，44795 字节），`seed.load()` 的代码路径实测正常（1 version / 3 conversations / 2 runs / 6 results，恰好一个 active）。成因是 **`render.yaml` 只对 Render 以 Blueprint 方式托管的 service 生效**。线上这个 service 是在面板里手工创建的，所以那份 yaml 在仓库里，**线上没有任何东西读它**，`SEED_DEMO` 从来没被设上。

**这件事撞在这个产品自己的主题上**：仓库里躺着一份 `SEED_DEMO: "1"`，看起来权威、进 diff、可 review；运行中的服务不同意；而**没有任何东西把这个分歧显示出来**。健康检查绿的，三个端点全 200，连模型名都是对的——因为它恰好等于 `packages/agent/llm.py:19` 的代码默认值，所以即使环境变量全没生效，那一栏也照样显示正确。**要发现它只能去看后果**：runs 是空的。这正是 [TO-07](trade-offs.md) 那段论证的现实版本，我在自己的部署上踩了一次。已写进 [TO-33](trade-offs.md) 和 `render.yaml` 的头注释。

**修法**：面板 Environment 里手工加 `SEED_DEMO=1`（会触发一次重新部署）。不改成 Blueprint——Render 不能把已有 service 转成 Blueprint 托管，那要新建，会换掉已经写进 `README.md` 和 `APPROACH.md` 的 URL。

**在它被设上之前，文档里有两句话是假的**，这一点必须点明而不是默认它会被修好：

- `README.md` 的 Live 段落：「the conversation history and benchmark runs you see are re-seeded from `datasets/demo_seed.json` on each cold start」
- `APPROACH.md` 的 §Deployment：「the demo data has to come back from the app's own startup, which is what `SEED_DEMO=1` does」

两句在环境变量设上之后即为真。设不上就必须改文案——**给评审看一份说了会有数据、点进去却是空的 console，比明说没有数据更糟**。
