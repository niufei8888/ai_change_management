# Ask Luma

一个只回答 Luma AI 产品文档问题的问答服务。内部是一个 ReAct 循环：先判断问题是否在范围内、要不要检索并规划检索词，检索本地文档，再判断证据是否足够，不够就再检索一轮（最多 3 轮），够了才作答；三轮都不够就诚实说不知道。

设计文档：[ai-discussion/design_step1_ai_app.md](../../ai-discussion/design_step1_ai_app.md)

这个服务是被管理的对象。管理它的变更安全系统在 `apps/console/`（Step 2，尚未实现）。**本服务不依赖 `apps/console`**，两者只通过 `packages/behavior_core` 共享契约。

所有命令都在**仓库根目录**执行，不是这个文件夹。整个 monorepo 只有根上一份 `pyproject.toml` 和一个 `.venv`。

---

## 前置条件

- [uv](https://docs.astral.sh/uv/)（它会自己准备 Python 3.12+，不碰你系统的 Python）
- 一个 Gemini API key（[Google AI Studio](https://aistudio.google.com/apikey) 免费额度够用）

> 注意：本项目用的是 **Gemini**，不是仓库题面 `.env.example` 里预置的 Anthropic / OpenAI。

前端是一个静态文件，**没有构建步骤**，所以不需要 Node（[TO-24](../../ai-discussion/trade-offs.md)）。

## 语料必须先就位

服务启动时会把 `corpus/` 载入内存，**语料缺失会直接启动失败**。这是有意的：带着空索引启动的症状是「模型对所有问题都说不知道」，那看起来像 prompt 或模型的问题，排查方向会完全跑偏。

仓库里已经提交了抓好的语料（39 篇）。要重抓：

```bash
uv run python scripts/fetch_corpus.py            # 只抓缺的
uv run python scripts/fetch_corpus.py --force    # 全部重抓
```

抓取是**构建期的一次性动作**，服务运行时只读本地文件，不会访问 lumalabs.ai。

---

## 方式一：Native Python（推荐用于调试）

```bash
uv sync                                  # 建 .venv 并装依赖
cp .env.example .env                     # 然后填 GEMINI_API_KEY

uv run python -m ask_luma.cli init-db    # 建表 + 写入 v1 baseline 版本
uv run uvicorn ask_luma.main:app --reload --port 8000
```

打开 http://localhost:8000

改前端直接改 `apps/chatbot/web/index.html` 然后刷新浏览器就行。视觉 token 是文件顶部那段 `:root` CSS 变量，风格参照 Anthropic Claude：暖白纸感背景、衬线标题配无衬线正文、陶土橙作唯一强调色，自动跟随系统深色模式。

等待期间只显示一个统一的 thinking 指示，**不显示每一步在做什么**（[TO-17](../../ai-discussion/trade-offs.md)）。完整轨迹在答案返回后通过折叠面板查看。

### 调试用的几个入口

```bash
# 不开浏览器，直接问一句并打印完整轨迹
uv run python -m ask_luma.cli ask "What is a Skill in Luma?"

# 只测检索，不花 API 配额
uv run python -m ask_luma.cli search "share a skill with teammates"

# 列出这个 key 实际能用的模型，用来给 MODEL 挑一个具体版本
uv run python -m ask_luma.cli models

# 逐节点详细日志
LOG_LEVEL=debug uv run uvicorn ask_luma.main:app --reload --port 8000
```

### 唯一的测试

```bash
uv run python scripts/smoke.py
```

**没有单元测试**（[TO-23](../../ai-discussion/trade-offs.md)）。这是 demo 不是 production system，而且这个项目的主题恰恰是「用 Step 2 的 benchmark 防 AI 行为回归」——golden dataset 加 judge 就是本项目版本的回归测试。

`smoke.py` 跑四条真实路径并把轨迹打出来：文档覆盖的问题、文档没覆盖的问题、跟 Luma 无关的问题，以及**收紧 `in_scope` 规则之后合法问题被拒答**的那条。最后一条是 Step 2 整个高光 demo 的前提，所以在 Step 1 就要验证它走得通——**原定用 `tool_description` 做这个 demo，实测五种改法全都不成立**，详见 [design_step1_ai_app.md §14.1](../../ai-discussion/design_step1_ai_app.md)。

只跑最后一条（省配额）：`uv run python scripts/smoke.py regression`

### 断点调试

`--reload` 模式下可以直接用编辑器的 debugger attach。想看 ReAct 循环的行为，断点打在这三个地方最有用：

- `apps/chatbot/src/ask_luma/graph/runner.py` — 循环的进出条件和上限判断
- `apps/chatbot/src/ask_luma/graph/reflect.py` — `resolved` 的判定，这里决定了会不会再来一轮
- `apps/chatbot/src/ask_luma/search.py` — 打分与「返回空结果」的门槛

代码是 **let-it-fail 风格**（[TO-22](../../ai-discussion/trade-offs.md)）：默认不接错误，出问题就带着完整 traceback 崩在原地。全项目只有两处有错误处理——`llm.py` 里对 429 / 超时 / 5xx 的 `tenacity` 重试，以及 `main.py` 路由边界那个「落一条带 `error` 的 Conversation 再返回 502」。**调试时不用去找哪里把异常吞了，因为没有任何地方吞异常。**

---

## 方式二：Docker Compose（推荐用于部署）

```bash
cp .env.example .env                     # 然后填 GEMINI_API_KEY
docker compose up --build
```

打开 http://localhost:8000

单阶段纯 Python 镜像，**单进程 uvicorn**。前端没有构建步骤所以没有 Node 阶段，语料直接烤进镜像所以容器运行时不需要任何外网访问。首次启动自动建表并写入 v1 baseline 版本。

`./data` 挂进容器作为 SQLite 目录，数据在容器重建后保留。

```bash
docker compose logs -f      # 看日志
docker compose down         # 停止（数据保留在 ./data）
```

---

## 配置

`.env` 里的键分两类，区别很重要。

### 系统层设置（所有版本共享，改它等于换掉整个基线）

| 键 | 说明 |
| --- | --- |
| `GEMINI_API_KEY` | 必填。不要提交。 |
| `MODEL` | 填**具体版本号**，不要用 `gemini-flash-latest` 这类别名——别名会漂移，而漂移会伪装成「我改的 prompt 导致了行为变化」。 |
| `DB_PATH` | 默认 `./data/app.db`。 |
| `LOG_LEVEL` | `info` / `debug`。 |

### 行为配置（被版本化的六个杠杆，**不在 `.env` 里**）

`plan_prompt`、`reflect_prompt`、`synthesize_prompt`、`tool_description`、`temperature`、`max_loops`

这些存在数据库的 `Version` 表里，通过 `packages/behavior_core` 的 `config_client` 在**每次请求时**解析。这样才能不重新部署就切换版本、按比例灰度放量、以及即时回滚——这是 Step 2 的整套能力赖以存在的前提。

想改行为，改数据库里的版本记录（Step 2 会给这件事一个界面），**不要把 prompt 写死进代码**。`packages/behavior_core/config.py` 里的 `BASELINE_V1` 只是首次启动时写进数据库的种子，不是运行时读的东西。

---

## 接口

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `POST` | `/api/chat` | `{session_id, question}` → 回答 + 引用 + 完整轨迹元数据 |
| `GET` | `/api/conversations` | 按 `session_id`（前端恢复历史）或 `tag` / `arm`（Step 2 切片）过滤 |
| `GET` | `/api/health` | 含 `corpus_hash`、`article_count`、当前生效版本 |

一共就这三个，没有 debug 端点。**语料目录不对外暴露**——检索到的文章是喂给模型的上下文，不是给用户浏览的目录；引用信息跟着 `/api/chat` 的响应一起回来（[TO-19](../../ai-discussion/trade-offs.md)）。

`POST /api/chat` 的响应里带 `terminated_by`（`answered` / `exhausted` / `refused_out_of_scope`）、`loop_count`、`llm_call_count` 和逐节点的 `trajectory`。前端那个「这个回答是怎么产生的」折叠面板就是在渲染它。

## 常见问题

**启动报语料缺失** — 跑 `uv run python scripts/fetch_corpus.py`。

**回答里带 `Source:` 但文章名对不上** — 检查 `corpus/index.json` 是否和 `corpus/*.md` 一致；`index.json` 是「合法文章标题」的唯一权威来源。

**大量 429** — 免费额度限流。ReAct 循环每个问题要 3–5 次 LLM 调用，比一般单次问答费配额。等额度恢复，或用 `cli ask` 单条测试而不是跑整个 smoke。

**回答总是「我不知道」** — 先看 `/api/health` 的 `article_count` 是否为 0（语料没载入）；再看轨迹里的 `terminated_by`，如果一直是 `exhausted`，说明检索门槛偏严或 `reflect` 判定过于严格。

**`MODEL` 该填什么** — 跑 `uv run python -m ask_luma.cli models` 看这个 key 实际能用哪些。
