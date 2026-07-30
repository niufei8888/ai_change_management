# Step 4：部署到 Render（设计，未实施）

> 本篇只写计划，不动代码。前三步的约定不变：先对齐 plan，再实施。
>
> 平台已经定了（Render 免费层 Web Service，Docker），Gemini key 已经填进 Render 面板。所以这一篇不是「选平台」，而是**在这个已选定的平台上，把这个项目现有设计里会碎掉的地方找出来并修掉**。

---

## 0. 为什么需要这一步

前三步做完，项目在本机 `docker compose up` 是完整可用的。但提交物里有一条我一直没兑现的东西：**评审得自己 clone、自己弄 key、自己 build**。一个能直接点开的链接，价值不在于炫技，而在于它把「评审愿不愿意花 10 分钟装环境」这个变量从评估里拿掉了。

Step 3 明确把部署划成了单独一篇（§1「明确不做」第一条）。这就是那一篇。

**这一步的性质和前三步不同**：前三步是「做产品功能」，这一步是「把已有的东西搬到一个约束更硬的环境里」。所以它的产出主要是**修 bug 和补缺口**，不是加特性。下面每一条都是我实测出来的，不是照着文档猜的。

---

## 1. 本步的范围

**做：**

1. 修 `$PORT`——不修**部署会直接失败**（§3.1）
2. 把 demo 数据接进启动流程——不接 console 有两个 tab 是空的（§3.2）
3. `robots.txt`——拦住搜索引擎索引（§3.3）
4. Render 面板配置清单 + `render.yaml`（§4）
5. 文档收口：README 挂链接、说明冷启动和数据易失（§5）

**明确不做：**

- **限流 / 鉴权**。理由和替代方案见 §3.3，这是一个**知情的取舍**，不是遗漏。
- **持久化**。Render 免费层不允许挂盘（§2.2），换 Postgres 就得改一层存储，收益不抵成本。
- 自定义域名、CDN、多区域、蓝绿部署。
- 保活（定时 ping 防休眠）。理由见 §6.2。

---

## 2. 平台的硬约束（来自 Render 官方文档）

### 2.1 已核实的数字

全部来自 <https://render.com/docs/free> 和 <https://render.com/docs/web-services>，不是二手博客：

| 项 | 值 |
| --- | --- |
| 空闲多久休眠 | **15 分钟**无入站流量 |
| 冷启动 | **约 1 分钟**；期间 Render 给浏览器显示自己的 loading 页 |
| 实例时长 | 750 小时/月/workspace（单服务 24×7 约需 720 小时，够） |
| 内存 | 512MB |
| CPU | 0.1（共享） |
| 出网带宽 | 100GB/月 |
| 构建时长 | 500 分钟/月 |
| 是否要绑卡 | 不要 |
| HTTPS | 自带，自动签发 |

### 2.2 三条「免费层不支持」，其中两条改变了方案

官方列出免费层不支持的能力里，有三条和这个项目直接相关：

1. **不能挂持久盘**（persistent disk 是付费功能）。
2. **不支持 one-off jobs。**
3. **不支持 SSH / 面板 Shell。**

第 1 条我原本就知道。**第 2、3 条是这次查文档才发现的，而它们直接砍掉了一整条退路**：

> 「部署完之后，手动跑一次 `python scripts/seed_demo.py load` 就行」——**这条路在免费层上不存在**。没有 shell 可以进，也不能起一次性任务。

所以「demo 数据怎么进去」不再是一个偏好问题（自动 vs 手动），而是**只剩一个选项：写进应用自己的启动逻辑**。§3.2 就是这个结论的产物。

### 2.3 文件系统易失的确切语义

官方原文：文件系统的改动在**redeploy、restart、spin-down** 三种情况下都会丢。

也就是说不只是「重新部署会清空」，**闲置 15 分钟休眠一次就清空**。这比我在别处的表述更严厉，值得写准：`data/app.db` 的生命周期约等于「最后一次有人访问之后的 15 分钟」。

---

## 3. 这个项目在 Render 上会碎掉的地方

以下三条我都在本机用「模拟 Render 条件」的容器实测过：不挂卷、注入 `PORT`、只给面板级环境变量。

### 3.1 `$PORT`：不修则部署直接失败

**现状**：`Dockerfile` 最后一行硬编码 8000。

```29:29:Dockerfile
CMD ["uvicorn", "server.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**实测**：起一个容器，注入 `PORT=10000`，进程仍然只监听 8000，10000 端口连不上。也就是说 `PORT` 这个变量对当前代码**完全没有作用**。

**为什么这不是「可能有点慢」而是「会挂」**——Render 文档写得很直接：

> The default value of `PORT` is `10000` for all Render web services. […] If you bind your HTTP server to a different port, Render is *usually* able to detect and use it. **If Render fails to detect a bound port, your web service's deploy fails** and displays an error in your logs.

所以留着不改，等于把部署成功与否押在一次探测上，失败的后果是**整个部署失败**，不是降级。这条必须修。

#### 3.1.1 面板里已经填的那条命令有风险，实测过

Render 面板的 Docker Command 现在填的是：

```
uvicorn server.main:app --host 0.0.0.0 --port $PORT
```

**这条命令能不能工作，取决于 Render 把它当 shell form 还是 exec form 传给容器。如果是 exec form，`$PORT` 不会被展开，会以字面量传给 uvicorn。**

我把两种情况都在本机的同一个镜像上跑了一遍。exec form（把 `$PORT` 作为字面量 argv 元素传进去）：

```
Error: Invalid value for '--port': '$PORT' is not a valid integer.
```

容器直接退出。shell form（同一个字符串交给 `/bin/sh -c`）：

```
INFO:     Uvicorn running on http://0.0.0.0:10000 (Press CTRL+C to quit)
  reachable on 10000: 200
```

**倾向判断是 exec form，即面板里现在这条会挂**，两个依据：

1. Render 文档专门写了一句「To run multiple commands, provide them to `/bin/sh -c`」。如果这个字段本来就走 shell，`&&` 直接就能用，没必要专门说这句。
2. 他们自己给的示例里端口是**硬写 `10000`**，而不是用 `$PORT`——一个推荐用 `$PORT` 的平台在自己的示例里回避它，通常正是因为在那个位置它不展开。

但我没有 Render 环境可以直接验证这一步，所以**这是推断，不是实测结论**。实测的只有「字面量 `$PORT` 一定会挂」和「`/bin/sh -c` 一定能跑」。

#### 3.1.2 结论：修 Dockerfile，并把面板那栏清空

选一个**两种情况都对**的方案，而不是去赌 Render 用哪种 form。

```dockerfile
EXPOSE 8000
CMD uvicorn server.main:app --host 0.0.0.0 --port ${PORT:-8000}
```

这是 Dockerfile 的 **shell form**，展开由容器自己的 `/bin/sh` 完成，跟 Render 怎么传参数无关。改完之后**面板的 Docker Command 必须清空**——留着它就是拿一条我判断会挂的命令去覆盖一条已知能跑的 CMD。

如果你更想保留面板那栏，那它必须写成：

```
/bin/sh -c "uvicorn server.main:app --host 0.0.0.0 --port $PORT"
```

**但我不推荐**，两个理由：

- 它是一处**只存在于面板、不在仓库里**的配置。这个项目从 TO-07 开始的主张就是「行为不该藏在部署里」，一个决定服务能否启动的命令只存在于某人的浏览器里，正是那件事的部署版。
- 它没有本地默认值。`${PORT:-8000}` 让本地 `docker compose up`（不设 `PORT`）和 Render（设了 `PORT`）走**同一份定义**；面板那条在没有 `PORT` 的环境里直接坏掉。

**代价：exec form 变 shell form**，容器里的 uvicorn 会挂在 `/bin/sh` 下面，信号转发多一跳。对这个项目无影响（没有需要优雅退出的写入路径，SQLite 每个请求各自提交），但这是个真实的差别，写下来。

### 3.2 console 有两个 tab 是空的

**实测**（不挂卷的新容器，等价于 Render 每次冷启动后的状态）：

| console 的数据 | 新容器里的行数 |
| --- | --- |
| Versions | **1**（`seed_baseline()` 干的活，这部分本来就对） |
| Simulation 历史 | **0** |
| Production 流量 | **0** |

所以评审点开链接看到的是：版本表里孤零零一个 baseline，Simulation 没有任何跑过的记录，Production 一片空白。**Step 3 花了整节做的 `datasets/demo_seed.json` 在部署环境里等于不存在**，因为它只能手动 load，而 §2.2 说了免费层没有手动的入口。

这直接违背了 Step 3 里你亲自选的 `api_key: both`——「让没有 key 的评审也能看到一个有数据的 UI」。讽刺的是，部署本来是为了降低评审门槛，结果反而把这个决定作废了。

**方案**：把 fixture 的加载接进启动流程。但**这不是加一行**，有一个真实的结构障碍：

```200:202:scripts/seed_demo.py
    from driftline import dataset

    live = dataset.load().hash
```

`load()` 结尾无条件调 `_warn_if_stale()`，而它内部 import `driftline`（console 包）。从 chatbot 的 `lifespan` 调 `load()`，就会在运行时把 console 拉进 chatbot 的依赖里，**违反 `apps/chatbot ──✗ apps/console`**（`AGENTS.md` 的目录边界）。

三个候选方案：

| 方案 | 做法 | 评价 |
| --- | --- | --- |
| **A. 落到 `server/main.py`** | 在唯一允许同时 import 两个 app 的模块里做 seed | 边界上最干净，但那里现在只有 3 行「组装」逻辑，塞进一个有副作用的 DB 写入会让它不再是纯组装；而且 seed 必须发生在 `lifespan` 里（要在 `init_db()` 之后），从外部包装别人的 lifespan 很绕 |
| **B. 把 load 逻辑下沉成库** | `load()` 移到 `packages/behavior_core/seed.py`，`_warn_if_stale()` 留在 `scripts/seed_demo.py` 里当 CLI 的一部分 | **推荐**，见下面的具体形式 |
| **C. 不 seed，接受空 console** | 什么都不做 | 否决。它让 §3.2 开头那张表成为评审的第一印象 |

**选 B**，具体落法是：

- **`packages/behavior_core/seed.py`（新增）**：`load()` 搬到这里，纯函数，不 import `driftline`。放在 `behavior_core` 是因为 fixture 里全是 `behavior_core.models` 的行——**它是关于这一层自己的表的数据**，不属于上面任何一层。chatbot 本来就依赖 `behavior_core`，所以调它零边界成本。fixture 路径用 `parents[2]`，和 `db.py:10` 定位 `data/` 是同一个写法。
- **`scripts/seed_demo.py`（保留）**：继续当 CLI。`export()` 留在这里（它确实需要 `driftline.dataset` 算 dataset hash，而 `scripts/` 可以 import 任何东西），`load` 变成「调库 + 打印 + `_warn_if_stale()`」。

**为什么 staleness 警告留在 CLI 而不是跟着 `load()` 走**：它是给**敲命令的人**看的一句提示，不是 `load()` 的职责。而且在 Render 上它没有收件人——服务启动时打到日志里没人读。这不只是为了绕开边界，本来就该这么分。

附带一个必须显式决定的问题：**seed 应该默认开还是要开关？**

倾向是**加一个 `SEED_DEMO` 环境变量，默认关，Render 上打开**。理由：本机开发时每次起服务都往库里插 canned 数据是干扰（你分不清哪条是自己刚问的、哪条是种进去的——虽然 UI 有 `seeded` 标记，但认知负担是真的）；而在 Render 上，每次冷启动都重新 seed 恰好把「磁盘易失」从缺陷变成**特性**：评审拿到的永远是一个干净、已知、可复现的状态，别人乱点也污染不了。

### 3.3 公开 endpoint + 已生效的真 key

`/api/chat` 没有鉴权、没有限流。链接一旦流出，任何人（或任何扫描器）都能消耗你的 Gemini 配额。对一个**把成本作为一等指标**的项目来说，demo 自己因为公开暴露而失控烧钱，是个很难看的翻车点。

**决定（你定的）：**

1. **加 `robots.txt`，禁止爬取。**
2. **不做限流。**
3. **交付完成后立刻注销 key。**

**必须把 `robots.txt` 的实际效力说准，否则它会给人虚假的安全感：**

`robots.txt` 是一个**自愿遵守的约定**。它能拦住守规矩的搜索引擎爬虫，因此能有效降低「demo 被 Google 索引 → 被陌生人搜到」的概率——这个风险是真实的，值得挡。但它对以下情况**完全无效**：恶意抓取脚本、端口/URL 扫描器、以及任何拿到链接直接点的人。

所以**真正兜住成本的不是 `robots.txt`，是第 3 条「用完注销 key」**。`robots.txt` 只是把「被动被发现」的概率压下去，第 3 条才是那个封顶的机制。这一点要在 trade-off 里写清楚，不能让它读起来像「我们做了防护」。

方案：

```
# apps/chatbot/web/robots.txt  (served at /robots.txt)
User-agent: *
Disallow: /
```

外加一个 `<meta name="robots" content="noindex, nofollow">`，因为部分索引器只看页面 meta 不读 `robots.txt`。

**不做限流的理由（记录成一条 trade-off）**：进程内按 IP 计数的限流大约 20 行，但 Render 前面有代理，真实 IP 在 `X-Forwarded-For` 里，写对需要信任那个头——而在不知道代理层数的情况下信任它，本身是个可被伪造的判断。为一个即将注销 key 的临时 demo 引入一个「看起来在防护、实际可绕过」的机制，比明确不做更糟。**明确不做 + 说清替代机制**，比一个半对的限流诚实。

---

## 4. Render 侧配置

### 4.1 面板字段

| 字段 | 值 | 备注 |
| --- | --- | --- |
| 类型 | **Web Service** | 需要公网 HTTP 入口 |
| Environment | Docker | 仓库根有 `Dockerfile`，自动识别 |
| Branch | `main` | |
| Instance Type | Free | |
| Health Check Path | `/api/health` | 现成的端点，会检查语料是否加载、返回生效版本，比只看端口通不通准 |
| Docker Command | **必须清空** | 目前填的 `uvicorn … --port $PORT` 大概率会挂，见 §3.1.1 的实测；Dockerfile 改完之后不需要任何覆盖 |
| Pre-Deploy Command | **留空** | 它只在真正触发部署时跑，休眠唤醒不跑，解决不了 §3.2 |
| 环境变量 | `MODEL`、`GEMINI_API_KEY`、`SEED_DEMO=1` | key 已填 |

**不要用 Secret Files 上传整个 `.env`**：它默认挂到 `/etc/secrets/.env`，而代码里的 `load_dotenv()` 只找当前工作目录，等于白传。老实填环境变量表。

### 4.2 `render.yaml`

把上面这张表写进仓库，而不是只存在于面板里——和 §3.1 同一个理由：配置应该可 review、可 diff。

```yaml
services:
  - type: web
    name: ask-luma
    runtime: docker
    plan: free
    healthCheckPath: /api/health
    envVars:
      - key: MODEL
        value: gemini/gemini-3.1-flash-lite
      - key: SEED_DEMO
        value: "1"
      - key: GEMINI_API_KEY
        sync: false      # 不进仓库，面板里填
```

`sync: false` 是 Render 表示「这个值我不放在文件里」的写法，正好对应「key 只存在面板」。

---

## 5. 文档要改的地方

1. **`README.md`** 顶部加 live 链接，并且**紧挨着写清两件事**：第一次打开可能要等约 1 分钟（免费层冷启动，Render 会显示 loading 页）；以及数据会定期重置（易失文件系统），所以你看到的对话历史是 seed 出来的。**这两句必须在链接旁边，不能塞到最下面**——一个转圈 1 分钟又没解释的页面，读起来就是「他的东西是坏的」。
2. **`APPROACH.md`** 的开头目前第一句是「**Not deployed.**」，要改。
3. **`video.md`** 里可以录线上版本，省掉本地起服务的步骤。
4. **`apps/chatbot/README.md`** 补一节部署，说明 `SEED_DEMO` 和 `PORT` 这两个环境变量。

---

## 6. 风险与明确不处理的事

### 6.1 冷启动约 1 分钟，而且大概率正好砸在评审那一次点击上

评审是典型的「打开看一眼」访问模式，休眠后第一次访问撞上冷启动的概率很高。

缓解只有文档（§5.1）。**一个客观上不算太坏的事实**：Render 会在冷启动期间显示自己的 loading 页，所以看到的是「正在启动」而不是白屏或超时——这比我原先担心的情况轻。但一分钟仍然很长，这是选免费层的直接代价。

### 6.2 不做保活，理由

用外部定时 ping（cron-job.org / UptimeRobot / GitHub Actions）每 10 分钟打一次就能不休眠，且不用碰代码。**不做**，两个原因：一是 750 小时/月的额度就是按「不是 24×7」给的，主动保活等于故意贴着额度跑，Render 没有正式背书这种用法，理论上存在被判定为滥用的可能；二是它会让 §3.2 的自动 seed 几乎永不触发，反而**削弱了对那条路径的验证**。

### 6.3 内存和镜像大小（实测）

| 项 | 实测 | 免费层限制 | 判断 |
| --- | --- | --- | --- |
| 常驻内存 | **202MB** | 512MB | 够，余量约 2.5 倍 |
| 处理请求时峰值 | **203MB**（基本不涨） | 512MB | 够 |
| 镜像大小 | **865MB** | 500 构建分钟/月 | 不小（litellm 依赖重），单次构建几分钟，一个月十几次部署没问题 |

内存这条原本是我最担心的（0.1 CPU / 512MB 听起来很紧），实测下来余量充足。**CPU 0.1 才是没量到的那个**——本机测的延迟（一次问答约 3–4 秒）在共享 0.1 CPU 上会变慢，但瓶颈是等 Gemini 返回（网络 I/O），不是本地算力，所以影响应该有限。**这一条是推断，不是实测**，写下来以免被当成结论。

### 6.4 一个仍然没解决的老问题

`GET /api/conversations` 返回整行、包含完整 `trajectory`（Step 3 §13 记过）。在本机无所谓，在 100GB/月带宽下也无所谓，但 Production tab 一次拉 30 条对话会传不少 JSON。**不在本步修**，只是提一句它现在有了一个新的、真实的成本维度。

---

## 7. 验收清单

1. `docker compose up` 本地仍然工作，不设 `PORT` 时监听 8000
2. 注入 `PORT=10000` 起容器，**10000 端口可访问**（现在是不可访问）
3. `SEED_DEMO` 不设时，新库启动后 Simulation 历史为空（本机开发行为不变）
4. `SEED_DEMO=1` 时，新库启动后自动有 2 次 run、3 条 `seeded` 对话
5. `SEED_DEMO=1` 连续重启两次，数据**不翻倍**，且 **`status == "active"` 的版本恰好 1 条**（后半句是实施时踩到 §9.2 那个 bug 之后加严的）
6. `from ask_luma.main import app` 之后，`sys.modules` 里**没有** `driftline`（§3.2 的边界不能被 seed 破坏）
7. `check_assertions.py` 7/7、`smoke.py` 4/4
8. `/robots.txt` 返回 `Disallow: /`
9. Render 上部署成功，`/`、`/console`、`/api/health` 都是 200
10. 线上真问一个问题能答，且 console 的 Production tab 能看到它
11. `README.md` 的链接旁边有冷启动和数据重置的说明

---

## 8. 本步对 trade-offs 的改动

预留三条新编号（本步实施时写入）：

- **TO-32 部署选 Render 免费层**：为什么是它而不是 Fly.io / Railway（后两者 2026 年已无长期免费额度）/ Cloud Run（要绑 GCP 计费）/ Oracle 免费 VM（运维量最大）。代价：约 1 分钟冷启动 + 文件系统易失。
- **TO-33 `PORT` 写进 Dockerfile，不写进面板**：为什么配置要留在仓库里；代价是 exec form 变 shell form。
- **TO-34 公开 demo 不做限流，靠注销 key 封顶**：`robots.txt` 只降低被索引的概率，**不构成防护**；为什么一个可被 `X-Forwarded-For` 伪造绕过的半对限流比明确不做更糟。

另外要动的现有条目：

- **TO-16**（seed 用预计算结果直接入库）：补一段「Render 免费层没有 shell 也没有 one-off job，所以手动 load 这条路不存在，seed 必须进启动流程」。这是那条决定在新环境下的直接后果。
- **TO-22**（交付形态：能一口气读完、零构建跑起来）：补一句部署链接的存在改变了「跑起来」的门槛。

---

## 9. 实施结果

### 9.1 代码改动

| 文件 | 改了什么 |
| --- | --- |
| `Dockerfile` | `CMD` 换成 shell form `--port ${PORT:-8000}` |
| `packages/behavior_core/seed.py` | **新增**。`load()` / `_revive()` / `_annotations()` 从 `scripts/` 搬进来，不 import `driftline` |
| `scripts/seed_demo.py` | 收成 CLI：`export()` 和 `_warn_if_stale()` 留下，`load()` 变成「调库 + 打印」 |
| `apps/chatbot/src/ask_luma/main.py` | `lifespan` 里按 `SEED_DEMO` 调 `seed.load()`；新增 `GET /robots.txt` |
| `apps/chatbot/web/robots.txt` | **新增** |
| 两个 `web/index.html` | 加 `<meta name="robots" content="noindex, nofollow">` |
| `render.yaml` | **新增** |
| `README.md` / `APPROACH.md` / `apps/chatbot/README.md` / `.env.example` | 见 §5 |

### 9.2 实施时抓到的一个真 bug：两行同时 active

第一版把 seed 放在了 `init_db()` **之后**，实测结果是 **2 个版本、两行都是 `active`、label 都叫 `v1-baseline`**。

原因是 `seed_baseline()` 的提前返回条件是「存在一行 active 且 `config_hash` 等于代码里的值」：

```52:53:packages/behavior_core/db.py
        if existing is not None and existing.status == "active":
            return
```

于是 `init_db()` 先对着空表插了一行 active，`seed.load()` 又把 fixture 里那行（**同 hash、不同 id、也是 active**）插进来，第二次 `seed_baseline()` 一看条件满足就直接返回——两行都留下了。

**修法是把 seed 挪到 `init_db()` 之前**（`load()` 自带 `create_all`，本来就能独立跑）。CLI 那条路径一直是对的，正是因为它从来不调 `init_db()`。

**为什么这个 bug 值得单独写一段**：`seed.py` 里那段「Tables first, fixture second, seed_baseline last」的注释已经把这个陷阱描述得很准确了，我照样在**另一个调用点**上踩了进去。也就是说，注释警告的是「函数内部的顺序」，而漏洞出在「函数外部的调用顺序」。而且**「两行同时声称自己是 live」恰好是这个产品最不能进入的状态**——一个管理 AI 行为变更的系统，如果自己都说不清哪份配置在生效，那它讲的整个故事就没了。所以验收清单第 5 条从「数据不翻倍」加严成了「active 行必须恰好 1 条」。

### 9.3 验收结果

| # | 项 | 结果 |
| --- | --- | --- |
| 1 | 不设 `PORT` 仍监听 8000 | **通过** `:8000 → 200` |
| 2 | `PORT=10000` 时 10000 可访问 | **通过** `Uvicorn running on http://0.0.0.0:10000`，`:10000 → 200`（改动前不可访问） |
| 3 | `SEED_DEMO` 不设时 console 为空 | **通过** versions 1 / runs 0 / conversations 0 |
| 4 | `SEED_DEMO=1` 自动出数据 | **通过** versions 1 / runs 2（`baseline ea2580ac6b707853`、`bad-scope a206518b2f616f03`）/ conversations 3（三种终止态各一） |
| 5 | 连续重启两次不翻倍，且 active 恰好 1 条 | **通过**（第一版失败，见 §9.2） |
| 6 | import chatbot 后 `sys.modules` 无 `driftline` | **通过**。本机和镜像内都验了；`server.main` 里两个都在，那是它的职责 |
| 7 | `check_assertions.py` / `smoke.py` | **通过** 7/7、4/4（`bad-scope` 仍然抓到回归：refuse vs answer，19 倍便宜、6 倍快） |
| 8 | `/robots.txt` | **通过** `Disallow: /`，`content-type: text/plain` |
| 9 | Render 上三个端点 200 | **待 push 后在 Render 上验** |
| 10 | 线上真问一个问题，Production tab 能看到 | **待 push 后在 Render 上验** |
| 11 | README 链接旁有冷启动和重置说明 | **通过** |

顺带验了两件事：两个 `index.html` 抽出 `<script>` 后 `node --check` 通过（meta 标签没弄坏内联 JS）；容器实际返回的 HTML 与工作区文件 sha256 一致（`/` = `6656562500388cf8`，`/console` = `adc347f029ed8fb1`）。

### 9.4 push 之后还剩两件事要人做

1. **把 Render 面板的 Docker Command 清空**（§3.1.2）。不清的话，那条命令会覆盖已经修好的 `CMD`，而它大概率会让部署失败。
2. **把线上 URL 填进两个占位符**：`README.md` 和 `APPROACH.md` 里各有一处 `<!-- RENDER_URL -->`。`rg -n RENDER_URL` 能找到全部。
