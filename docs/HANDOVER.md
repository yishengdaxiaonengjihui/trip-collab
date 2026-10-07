# trip-collab 项目交接文档（HANDOVER）

> **给下一个会话的快速启动指引**：本文件是跨会话继续工作的唯一权威入口。
> 读完本文档后按「会话恢复指引」（§11）执行，即可无缝接续开发。

- 最后更新：2026-10-05（待审核卡片预测性告警已实现，48 测试绿）
- 维护约定：**每个里程碑完成 / 每次会话结束前 / 需求或决策变化时，必须更新本文件**并提交推送。

---

## ✅ 2026-10-05：待审核卡片预测性告警（HANDOVER §9 #3 落地）

**来源**：原型里待审核卡片会提前显示冲突/依赖告警，而实现里只有采纳时刻才检测（卡片上永远是空的）。

**做法（关键决策：预检实时计算，不落库）**

| 层 | 改动 |
|---|---|
| 引擎 `TripEngine.preview_report()` | 复用 adopt 的同一套 `detect_conflicts`，对「当前定稿 + 其它待审核提议」预检；多事件提议追加一条「包含 N 条改动，采纳时需人工确认」。**只读**，不推进版本、不写状态 |
| 服务 `_proposal_out(p, engine)` | 草稿/待审核 → 用实时预检；已采纳/已拒绝等终态 → 仍用采纳时刻留档的 `last_report`（历史事实不随后续定稿变化） |
| 前端 `ProposalsView.vue` | 待审核卡片新增「采纳前预检 · 预测此刻采纳的后果」区块：⛔ 硬冲突（会被拦下，需人工判定）/ ⚠️ 需二次确认 / ✔️ 预检通过；已采纳卡片仍显示「采纳时记录」 |
| 样式 `style.css` | 新增 `.precheck/.precheck-title/.ok-box` |
| 测试 | test_api.py +5：依赖告警提前可见、创建即返回预检、两条待审核并发改同条目双卡片硬冲突、多事件提示、采纳后仍保留采纳时刻报告 → **48 passed** |

**为什么不在 create/submit 时存 last_report**：定稿和其它待审核提议随时会变，存快照必然过期（卡片会显示错误告警）。实时计算永远与采纳行为一致，且不引入新的持久化字段（`last_report` 语义保持「采纳/紧急应用时刻的报告」不变）。

**验证**：`python -m pytest` 48 passed；`vue-tsc -b` 通过；`vite build` 通过；起服务后对演示行程实测 `GET /proposals` → 待审核卡片返回 `条目 d2_terra（秦始皇兵马俑）显式依赖被修改的条目 d1_train，请人工判断`。

---

## 🖥 2026-10-02 会话记录：新开发机接入（业务代码未改，仅环境 + .gitignore）

本次只做环境接入与基线验证，**没有修改任何业务代码**，等用户上线后再定开发方向。

| 项 | 本机取值 |
|---|---|
| 工作区 / 本地路径 | 工作区 `D:\dsh\trip project`，仓库 `D:\dsh\trip project\trip-collab` |
| 远程 | `https://github.com/yishengdaxiaonengjihui/trip-collab`（PRIVATE，HTTPS 方式克隆） |
| gh | `D:\apps\GitHub CLI\gh.exe`（**不在 PATH**，必须写全路径），登录账号 `szxdejieju`（对该仓库有 pull/push 权限） |
| git 提交身份 | 仓库级 `user.name=yishengdaxiaonengjihui` + GitHub noreply 邮箱（用户 2026-10-02 选定） |
| Python | `D:\apps\miniconda3\python.exe`（3.14）；依赖装在仓库内 `.pydeps/`（已 gitignore） |
| 后端依赖 | fastapi 0.142.2 / uvicorn 0.54.0 / httpx 0.28.1 / pytest 9.1.1 |
| 基线验证 | `python -m pytest` → **43 passed**（2026-10-02 实测） |

### 本机环境坑位（补充 §8，新机必读）

1. **git 的 schannel 后端在本机不可用**（`SEC_E_NO_CREDENTIALS`，curl.exe 同样报错；与 DSH 沙箱无关）→ 所有远程操作都要显式 `-c http.sslBackend=openssl`。
2. **`github.com` 的 443 被黑洞**（本机实测：`github.com` 解析到 `20.205.243.166` 时通常 TCP 443 超时，但个别 GitHub 边缘 IP 可用，且**可用 IP 会随时间变化**——2026-10-02 能用的 `140.82.112.3` 到 10-05 已失效）。`gh`（Go 走 api.github.com）不受影响，**只有 git 的 https 传输挂掉**。
   → 本机自带一个本地中继脚本绕过（把 `github.com:443` 转到可达的边缘 IP，纯本地、明文不落到第三方）。脚本会**用真实 TLS 请求探测候选 IP**（TCP 通但收连接后黑洞的 IP 会被跳过），并在一旁路失效时自动重选：
   ```powershell
   # 中继脚本：D:\dsh\trip project\.gh-relay.py（候选 IP 列表见 CANDIDATES，端口参数默认 8443）
   & 'D:\apps\miniconda3\python.exe' 'D:\dsh\trip project\.gh-relay.py' 8443   # 后台跑着即可
   $b64=[Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes("x-access-token:"+(& 'D:\apps\GitHub CLI\gh.exe' auth token)))
   git -c http.sslBackend=openssl -c http.proxy=http://127.0.0.1:8443 -c credential.helper= -c http.extraHeader="Authorization: Basic $b64" push origin main
   ```
   （`clone`/`pull`/`fetch` 同理，加上 `-c http.proxy=http://127.0.0.1:8443` 即可。若哪天 `github.com:443` 恢复直连，去掉 proxy 参数即可。**不要再**用旧版 HANDOVER 里的 `core.sshCommand` / `gh-proxy` 改写：`gh-proxy` 是第三方，会把 token 交给别人。）
3. **`pip install` 必须提权**（`sandbox_permissions=danger-full-access`）：普通权限下 pip 在工作区内建临时目录会被沙箱拒绝。
4. **提权运行产生的目录，普通权限的后续命令读不到**（`.pydeps/`、`.tmp/` 实测 Permission denied）→ 跑测试/起服务都要带同等级提权：
   ```powershell
   $env:PYTHONPATH='D:\dsh\trip project\trip-collab\.pydeps'; & 'D:\apps\miniconda3\python.exe' -m pytest -q
   ```
5. 前端 `node_modules/` **已装好**（2026-10-05 实测 `vue-tsc -b`、`vite build`、vite dev 均可用；构建类命令按 §8 第 2 条需提权）。
6. 用户明确选择：**沙箱保持现状，按需逐条申请提权**（不切完全权限）。
7. 工作区根目录 ACL 曾被修复过（DSH 沙箱无法为 `D:\dsh\trip project` 授权），恢复脚本在 `D:\dsh\acl-recovery-trip\`。

### 明天上线后的待办（用户验收后再定）

| # | 事项 | 说明 |
|---|---|---|
| 1 | 用户验收 UI（`5ffa601` 的垂直时间线 + 暖橙配色 + 类型色卡） | 需先起后端 8000 + 前端 5173 + `python frontend/seed_demo.py` |
| 2 | 二选一开工：**MVP 业务功能**（AI 生成提议草稿、通知/邀请） 或 **待审核卡片预测性告警**（HANDOVER §9 #2/#3） | 用户 2026-10-02 表示"明天上线再过" |

---

## ✅ 最近完成（2026-09-13）：UI 升级 —— 配色 + 垂直时间线 + 类型色卡（提交 `5ffa601`）

**来源**：用户试用后反馈 ① 配色丑；② 行程页希望"竖着的轴按时间线展示"，不同颜色卡片标注「景区/饭店/酒店/交通」等类型。

**状态：已提交推送**（`5ffa601`，11 文件 +312/-55，43 测试绿、vite build 通过）。

### 已完成（全部验证过）

| 改动 | 文件 | 验证 |
|---|---|---|
| 引擎 `Item` 新增 `time`（展示时间）+ `tag`（类型）字段 | `backend/engine/state.py`、`engine.py`（`_ITEM_FIELDS`）、`backend/app/schemas.py` | 43 测试全绿 |
| 修复 `get_trip` 手工构造字典漏掉新字段（改用 `item_to_dict`） | `backend/app/services/trip_service.py` | 同上 |
| 新增 API 全链路测试（created 带 time/tag → adopt → TripOut 保留） | `backend/tests/test_api.py`、`conftest.py` | ✅ |
| 前端类型对齐 | `frontend/src/types.ts` | vue-tsc 通过 |
| **TripView 重写为垂直时间线**：竖向渐变轴 + 类型色圆点 + 左色条卡片，天内按 `HH:MM` 排序（无时间按 position 殿后） | `frontend/src/views/TripView.vue` | obscura 渲染验证 ✅ |
| **全局配色换暖橙旅行主题**：主色 `#f97316`；类型色 = 景区绿 `#10b981` / 饭店橙 / 酒店紫 `#8b5cf6` / 交通蓝 / 购物粉 / 其他灰；顶栏橙渐变、背景暖米白 | `frontend/src/style.css` | 同上 |
| 新建提议支持编辑时间/类型（created 必填、updated 可选） | `frontend/src/views/NewProposalView.vue` | vue-tsc 通过 |
| 演示数据升级为 3 天 12 条（带时间/类型/依赖） | `frontend/seed_demo.py` | 播种成功（v12） |
| 生产构建 | — | vite build ✅（PWA 9 项预缓存） |

### 收尾状态

1. ✅ 代码已提交推送：`5ffa601`（引擎 time/tag + 前端时间线/配色 + 43 测试）。
2. ⏳ **待用户验收渲染效果**；若有微调（颜色/布局）在此提交后追加提交。
3. ⏳ 可选：交互原型 `frontend/prototype/`（UX 实测版）尚未同步新配色/时间线——**待用户确认是否需要同步**。

### 现场环境（会话若中断，重启方法见 §6）

- 后端 uvicorn `:8000`（演示数据已播种：行程 `10e28618183d4e02877d02a3f396c150`，v12，3 天 12 条 + 1 条待审核提议，trip id 已写入 `frontend/.trip_id.txt`）
- 前端 vite dev `:5173`（HMR 已生效）

---

## 1. 项目一句话

**trip-collab —— AI 多人版本化旅行协作规划系统**：面向朋友/家庭/小队结伴出游的行程方案协作工具（移动端 PWA 优先）。
核心价值：*"大家随便提方案，定稿统一合并，全程可追溯、可回滚、无争吵"*。
用户只感知【定稿行程、提议、采纳、拒绝、回滚、临时备选】，完全隐藏事件溯源/版本控制等术语。

## 2. 仓库与访问

| 项 | 值 |
|---|---|
| 远程仓库 | `git@github.com:yishengdaxiaonengjihui/trip-collab.git`（**PRIVATE**，勿公开） |
| 本地路径 | `D:\dsh\tour\trip-collab`（工作区 `D:\dsh\tour` 下，另有 TREK-main/TripStar-main/voyago-main 三个参考源码，勿混淆） |
| 分支 | `main`（唯一分支） |
| git 身份 | 账号 `yishengdaxiaonengjihui`，gh 已登录 |
| **SSH 关键配置** | 沙箱里 msys ssh 不可用，**仓库级** `core.sshCommand='"C:/Windows/System32/OpenSSH/ssh.exe"'` 已配置；全局 gitconfig 含 `url.https://v4.gh-proxy.org/...insteadof=https://github.com/` 改写，SSH 不受影响 |

推送命令：`git push`（走 SSH，无需其他配置）。

## 3. 决策链（为什么是现在这个样子——改前必读）

1. **不 fork 任何开源项目**，新建仓库 + 模块级移植：
   - TripStar（GPL-2.0）：只移植 AI 多智能体/小红书解析**模块**（GPL 传染，若不想以 GPL 发布需自行重写 AI 编排层，许可证仍 TBD）
   - Voyago（MIT）：12306/高德/酒店数据封装——按 MIT 直接借鉴
   - TREK（AGPL-3.0）：时间线/地图 UI 设计**思路**——只看不抄代码
2. **第 0 周 Spike 是项目生死验证**：① 事件溯源引擎技术可行性 → ✅ 已证明；② UX 实测（真实用户反馈"不如微信群"则改交互或终止）→ ⏳ **待执行，MVP 开工的闸门**。
3. **MVP 砍功能**：评论/投票/预算/爬虫全部后置；AI/数据源全部做成**可降级插件**（核心协作不依赖任何第三方）。
4. 冲突检测语义：**发生在采纳时刻**（基于当前回放定稿），非提交时刻；回滚 = 追加补偿事件，历史 append-only。
5. 语言约定：全程中文（代码注释、文档、错误消息、UI）。

## 4. 当前状态总览

| 模块 | 状态 | 验证 |
|---|---|---|
| 事件溯源引擎 `backend/engine/` | ✅ 完成（提议/采纳/回滚/冲突三型/临时备选/序列化） | 25 单测绿 |
| 交互原型 `frontend/prototype/`（纯静态） | ✅ 完成（8 项交互断言） | 8/8 绿 |
| **UX 实测** | ⏳ **待执行（需真人）** | 脚本见 `docs/UX_TEST.md` |
| FastAPI 后端骨架 `backend/app/` | ✅ 完成（引擎集成 + SQLite 持久化 + 16 REST 路径 + 插件注册表） | **48 测试绿** + uvicorn 冒烟过 |
| Vue3+Vite+PWA 前端 `frontend/src/` | ✅ 五视图 + 旅途应急 + PWA + **垂直时间线/类型色卡/暖橙配色** | 类型检查 + 生产构建 + 端到端验证过 |
| 文档 | ✅ REQUIREMENTS(V1.3) / SPIKE / UX_TEST / HANDOVER | — |

提交历史（main）：`28e1e38` 骨架 → `0b4b9eb` 引擎 → `5dc8ff3` gitignore → `1d53a88` 原型+UX脚本 → `9e85a1a` 后端 → `6d597b6` 前端 → `bb3715b` HANDOVER → `b245489` HANDOVER 更新 → `5ffa601` UI 升级。

## 5. 架构与代码地图

```
trip-collab/
├── backend/
│   ├── engine/            # 事件溯源引擎（纯逻辑，零依赖）
│   │   ├── events.py      #   ChangeEvent(提议内) / StreamEvent(定稿流)，append-only
│   │   ├── state.py       #   Item{id,day,position,title,refs,amount,note,time,tag} / TripState / apply_event
│   │   ├── conflicts.py   #   detect_conflicts：硬冲突(并发改同条目/目标失效)、软冲突告警、隐性依赖告警
│   │   ├── engine.py      #   TripEngine：提议状态机、adopt/rollback/emergency/formalize/revoke、
│   │   │                  #   to_dict/from_dict 序列化（持久化边界）
│   │   └── errors.py      #   TripCollabError 等 5 异常
│   ├── app/               # FastAPI 应用（骨架）
│   │   ├── main.py        #   create_app() 工厂；模块级 app=create_app()（会建默认 db）
│   │   ├── config.py      #   Settings（env 覆盖：TRIP_DB/TRIP_CORS_ORIGINS/TRIP_DEFAULT_USER）
│   │   ├── db.py          #   SQLite：trips/members 结构化 + trip_state.state_json 整包存引擎状态
│   │   ├── schemas.py     #   Pydantic v2 请求/响应模型
│   │   ├── services/trip_service.py  # 业务编排：加载引擎→动作→保存；TripNotFoundError
│   │   ├── routers/       #   trips/proposals/versions/members/plugins + deps.py(错误映射)
│   │   └── plugins/registry.py  # 插件降级注册表雏形（weather/poi Mock，degraded 标记）
│   └── tests/             # 25 引擎 + 3 序列化 + 20 API = 48 测试
│       └── .testdbs/      #   沙箱兼容：测试 db 固定目录（勿删，gitignore）
├── frontend/
│   ├── prototype/         # 第 0 周交互原型（纯静态，UX 实测用它）
│   ├── src/               # Vue3 正式前端
│   │   ├── api.ts         #   fetch 封装 + HttpError(携带 code/message)
│   │   ├── types.ts       #   与 OpenAPI 对齐的类型
│   │   ├── router.ts      #   / → trips; /trips/:id → trip|proposals|new|history|notify
│   │   ├── App.vue        #   顶栏+底部导航壳
│   │   ├── store.ts       #   appState + toast
│   │   └── views/         #   Trips/Trip/Proposals/NewProposal/History/Notify
│   ├── vite.config.ts     #   /api 代理 → 127.0.0.1:8000；vite-plugin-pwa
│   ├── seed_demo.py       #   演示数据播种（后端起来后运行）
│   └── cdp_adopt_test.mjs #   CDP 端到端采纳流程测试（需 obscura serve）
└── docs/
    ├── REQUIREMENTS.md    # 需求 V1.3（权威）
    ├── SPIKE.md           # 引擎设计：7 不变量 + 冲突规则表 + 已知限制
    ├── UX_TEST.md         # UX 实测脚本（场景 A-D、判据、观察清单）
    └── HANDOVER.md        # 本文件
```

## 6. 运行 / 测试手册

```bash
# 后端（仓库根目录）
python -m uvicorn backend.app.main:app --reload --port 8000
# 前端（frontend/ 下）
npm run dev        # http://localhost:5173（/api 自动代理到 8000）
# 演示数据（后端起来后，frontend/ 下）
python seed_demo.py
# 后端全量测试（仓库根目录）
python -m pytest   # 48 passed
# 前端类型检查 + 生产构建（frontend/ 下）
node node_modules/vue-tsc/bin/vue-tsc.js -b && node node_modules/vite/bin/vite.js build
```

API 速查（16 路径，前缀 `/api`）：`POST /trips`、`GET /trips[/{id}]`、`GET|POST /trips/{id}/proposals`、
`POST .../proposals/{pid}/submit|adopt|reject|emergency|formalize|revoke`、`GET .../versions`、`POST .../rollback`、
`GET .../notifications`、`GET|POST|PUT .../members`、`GET /plugins`、`GET /health`。
身份占位：请求头 `X-User-Id`。错误体 `{code, message, detail}`，HTTP 映射：硬冲突 409 / 需确认 422 / 状态错误 409 / 未找到 404。

## 7. 无头浏览器验证链（DSH 环境）

- 渲染验证：`obscura fetch http://localhost:5173/... --allow-private-network --dump markdown|html`（**必须用 localhost 而非 127.0.0.1**，vite 绑 IPv6）
- 截图：`--screenshot out.png`（但 `image_understand`/`show_image` 只读 `c:\users\13701`，沙箱写不进去，视觉验证不可用 → 用 DOM 断言代替）
- 交互点击流：`obscura serve --port 9222 --stealth --allow-private-network` + `node frontend/cdp_adopt_test.mjs <trip_id>`（验证采纳→依赖告警弹窗→确认→adopted）
- 静态页自测 runner 模式：写独立 html 加载被测 JS，`window.load` 里跑 try/catch 断言写进 `<pre id=results>`，再 fetch --dump 提取（规避 `-e` eval 时序竞态）

## 8. 环境约束（DSH Windows 沙箱，防踩坑清单——新手必读）

1. **python 不能递归删目录**（`shutil.rmtree` 报 WinError 5）：pytest 勿用 `tmp_path`/`--basetemp`，测试写固定预建目录（已适配）。
2. **node 不能 spawn 子进程**（命名管道 EPERM）：
   - `npm install` 必须 `--ignore-scripts` + `--cache <工作区内路径>`（默认缓存 C:\Users\... 被拦）
   - 不要用 `npm run`，直接 `node node_modules/<bin>` 执行
   - `vite build` / `vite dev` 依赖 esbuild spawn，**必须** `sandbox_permissions=danger-full-access` 升级重试（有正当拒绝依据）
3. python 建的临时目录可能变成**幽灵目录**（cmd 看不见、谁都删不掉）——不要再临时 mkdtemp 探测；已知残留：`backend/tests/tmpyjm0n5m9`、`pytest-cache-files-*`（已 gitignore，勿尝试删除）。
4. `System.Drawing.Bitmap.Save` 报 GDI+ 错误 → 生成图片用 **Pillow**（Anaconda 自带）。
5. 后台任务（run_in_background）**必须显式传 workdir**，否则 import/脚本路径错。
6. PowerShell 内联 `python -c` 的 f-string 转义（`p[\"id\"]`）极易被吞 → 多行逻辑写 .py 文件。
7. PowerShell `ConvertTo-Json` 中文/含 $null 的 body 提交 FastAPI 会 422 → 用 python httpx 脚本播种。
8. CDP（obscura serve）扁平模式：`sessionId` 放消息**顶层** `{id, sessionId, method, params}`，放 params 里报 "No page for session"。
9. 身份/权限：工作区 `D:\dsh\tour` 可写；`C:\Users\13701` 被沙箱拦（需升级）；gh 推送走 SSH（仓库级配置已就位）。

## 9. 下一步任务（交接清单，按优先级）

| # | 任务 | 说明 | 前置 |
|---|---|---|---|
| 1 | **UX 实测（唯一需真人）** | 按 `docs/UX_TEST.md` 招募 3~5 名真实出行群体，用 `frontend/prototype/index.html` 走场景 A-D，按判据判定（**注意**：原型尚未同步新配色/时间线，是否同步待用户确认） | 无（用户本人参与） |
| 2 | MVP 业务功能（实测通过后） | 邀请/角色权限落地、**最简 AI 生成提议到草稿**（LLM 把口语描述转引擎事件）、离线只读（PWA SW 已有雏形）、通知通道 | UX 实测通过 |
| 3 | ~~待审核卡片**预测性告警**~~ | ✅ **已实现（2026-10-05）**：`TripEngine.preview_report()` 实时预检，待审核卡片提前显示硬冲突/依赖告警（见文首当日记录） | — |
| 4 | 讨论区/评论 | API 未实现（原型有 mock 评论），MVP 后置项 | 后置 |
| 5 | ~~时间字段建模~~ | ✅ **已实现（2026-09-13）**：`Item.time`（展示时间，时间线排序/显示）+ `Item.tag`（类型） | — |
| 6 | 插件升级 | weather/poi 从 Mock 换真实供应商（保持 degraded 降级语义） | 阶段 2 |
| 7 | 许可证决策 | TripStar GPL-2.0 模块移植与否直接影响发布许可证（TBD） | 任何对外发布前 |

## 10. 产品决策点（待定记录）

- **待审核告警展示**：✅ **已定（2026-10-05）**：实时预检（`preview_report`），不落库、不存快照——避免卡片显示过期告警；采纳时刻的 `last_report` 仅作历史留档。
- **emergency 语义**：提交即采纳、可 formalize/revoke（逆操作恢复采纳前快照），已定稿实现。
- **版本起始**：新行程 v0（空事件流）；首个采纳 → v1。前端显示 v0。
- **时间/类型字段**：✅ 已落地（2026-09-13）。`time` 存展示时间字符串（"HH:MM"，前端解析排序，无时间按 position 殿后）；`tag` 存中文类型值（景区/饭店/酒店/交通/购物/其他，空=其他），前端映射颜色。待议：是否引入枚举校验/多语言（MVP 暂用自由字符串）。
- **条目类型体系**：当前 6 类（景区/饭店/酒店/交通/购物/其他）由前端 `TripView.vue` 的 `TAG_CLASS` 映射颜色；新增类型只需加映射。是否支持自定义标签待 UX 反馈。
- **评论/投票**：需求 V1.3 后置；不阻塞 MVP 骨架。

## 11. 会话恢复指引（新会话第一件事）

1. 读本文件（`docs/HANDOVER.md`）→ 读 `docs/REQUIREMENTS.md` 对应章节。
2. 确认仓库状态：`git status -sb`（应干净）+ `git log --oneline`（对照 §4 提交历史）。
3. 跑基线验证：`python -m pytest`（应 48 passed）。
4. 若任务涉及前后端运行：按 §6 启动 + `python frontend/seed_demo.py` 播种。
5. 先处理 §9 清单顶部的任务；遇到环境问题查 §8。
6. **会话结束时**：把进展/决策/坑更新进本文件（更新日期与提交号），提交推送。

## 12. Cloudflare Workers 公网部署（2026-10-05 起）

目标地址：**https://app.trip-collab.workers.dev**（账号 `18916498879@163.com`，workers.dev 子域已注册为 `trip-collab`）。

### 部署形态

一个 Worker 同时承担两件事，前后端同源，前端代码零改动：

- 静态页面 → Cloudflare assets（`not_found_handling = "single-page-application"`，深链接刷新不 404）
- `/api/*` → 同源反代到本机隧道（不需要 CORS，也不用构建期写死后端地址）

相关文件：`frontend/wrangler.toml`（`main`/`assets`/`vars.API_ORIGIN`）、`frontend/worker/index.js`（12 行，assets + api 分流）。

### 命令（两条都有坑，务必照抄）

```powershell
# 1) 安装（已装好，仅在重装/换机时执行；必须 --ignore-scripts，否则 npm 生命周期脚本 spawn EPERM）
#    注意前缀是【仓库内】的 .tools，不是工作区根目录的 .tools —— 两个目录同名，容易搞混
$env:npm_config_cache = "D:\dsh\trip project\.npm-cache"
npm install --prefix "D:\dsh\trip project\trip-collab\.tools\wrangler" wrangler --no-audit --no-fund --ignore-scripts

# 2) 部署（必须提权 danger-full-access，原因见下）
cd frontend
& 'D:\apps\nodejs\node.exe' '..\.tools\wrangler\node_modules\wrangler\wrangler-dist\cli.js' deploy
```

- **⚠️ `wrangler deploy` 必须提权（danger-full-access）。** esbuild 以管道 stdio 启动服务子进程，工作区沙箱会拦截（`spawn EPERM`，栈指向 `esbuild/lib/main.js: ensureServiceIsRunning`）。**同一原因导致 `wrangler whoami` 会永久挂起**（esbuild 在模块加载期就 spawn）——不要用 `whoami` 判断登录状态，直接 deploy 看报错。
- 登录凭证已存在：`C:\Users\86189\AppData\Roaming\xdg.config\.wrangler\config\default.toml`。**不要设 `WRANGLER_HOME`**，设了反而读不到 token。
- esbuild 打包失败时 `Total Upload: 0.42 KiB` 仍会打印，属正常（worker 本身很小）。

### 当前阻塞（2026-10-05）

**邮箱未验证 → Cloudflare 拒绝绑定 workers.dev 子域路由**：

```
A request to the Cloudflare API (/accounts/<id>/workers/scripts/app/subdomain) failed.
You need to verify your email address to use Workers. [code: 10034]
```

此时**资源和 Worker 脚本都已上传成功**（`Uploaded app (9.84 sec)`），只差最后一步路由绑定。验证邮箱后**重跑一次 `deploy` 即可**，无需改动任何配置。验证入口：https://dash.cloudflare.com/profile （Resend verification email）。

### 已知限制

- **后端仍跑在本机**：Cloudflare 托管不了 Python/FastAPI。本机关机、或本机隧道进程停掉，页面能开但接口不通。
- **隧道地址写死在 `vars.API_ORIGIN`**：隧道重启换新地址后，要改 `wrangler.toml` 重新 deploy（或用命名隧道 + 自有域名固化）。
- 临时隧道（`trycloudflare.com`）与 Workers 是两套独立通路，可同时使用。

### 推送代码也要提权（2026-10-05 更正）

```powershell
git -c http.sslBackend=openssl push origin main   # 必须提权 danger-full-access
```

沙箱下直接 push 会失败于 `could not read Username`，根因是 `credential.helper = manager` 需要启动子进程，而 MSYS `sh.exe`/`bash.exe` 在沙箱里创建信号管道被拒（`fatal error - couldn't create signal pipe, Win32 error 5`）。**不是网络问题，也不是凭据失效**——提权后立刻成功。

另：**github.com 直连目前是通的**（`20.205.243.166:443` TLS 握手正常，本次推送未走代理），早前记录的中继（`.gh-relay.py`）本轮实测全部候选 IP 均不可达；该脚本留作备用，判断依据是「直连失败时先重试一次」——本轮首次 push 的 21 秒连接超时属瞬时抖动，重试即可。

### ✅ 部署已上线（2026-10-05）

```
Deployed app triggers (2.66 sec)
  https://app.trip-collab.workers.dev
Current Version ID: 6c37c9bc-0b5c-406c-80d4-7578d9b9b56c
```

邮箱验证通过后一次成功（`exit=0`）。注意 `deploy` 必须用**仓库内**的 CLI 路径：

```powershell
& 'D:\apps\nodejs\node.exe' 'D:\dsh\trip project\trip-collab\.tools\wrangler\node_modules\wrangler\wrangler-dist\cli.js' deploy
```

### ⚠️ 但 `*.workers.dev` 在本地网络被 DNS 污染

实测同一时刻、三个解析器对同一域名给出**三个互相矛盾的假 IP**，而对照组解析完全正常——这是典型的投毒特征：

| 域名 | @223.5.5.5 | @8.8.8.8 | @119.29.29.29 |
|---|---|---|---|
| `app.trip-collab.workers.dev` | `154.85.102.30` ❌ | `204.79.197.217` ❌ | `31.13.94.37` ❌ |
| `…trycloudflare.com`（对照） | `104.16.231.132` ✅ | `104.16.231.132` ✅ | `104.16.230.132` ✅ |
| `github.com`（对照） | `20.205.243.166` ✅ | 同左 ✅ | 同左 ✅ |

**结论：站点部署成功、全球可达，但本机所在网络打不开 `workers.dev`。** 绕开办法是给 Worker 绑**自有域名**（Cloudflare 自定义域名走 anycast，对照组证明该网络能正常解析并连通 Cloudflare IP），或访问时走代理。

另注：本机网络本身也不稳定——排查期间 `github.com` 的 HTTPS 在 20 分钟内从 200 变成连接超时，tunnel 从 200 变成 ECONNRESET。**验证线上站点时若失败，先隔几分钟重试再下结论。**

## 14. 上线方案变更：改用 Hugging Face Spaces（2026-10-06 决策，**已作废 → 见 §15**）

### 为什么改

用户目标收窄为：**中国高中研究性报告演示，让别人能通过互联网打开**，明确接受「会休眠」「数据不持久」。

- Cloudflare Workers 那条路已打通但 `workers.dev` 被 DNS 污染（§12），且后端仍跑在本机 → 关机即不可用
- 买域名 + VPS 对「一次性演示」成本过高
- **Hugging Face Spaces（Docker SDK，免费档 2 vCPU / 16GB）** 免备案、免信用卡、有公开 HTTPS 域名

### 可行性实测（2026-10-06）

```
hf.space 应用域：12 个真实 Space 逐一请求 → 11 个响应（200/404/503），零超时零重置 ✅
huggingface.co 管理站：hosts 文件 127.0.0.1 + DNS 投毒（162.125.80.3 / 104.244.43.182）❌
```

**结论：别人访问应用不需要代理；只有「创建/上传 Space」这一步需要一次性代理。**

### 关键技术判断（省掉大量工作）

前端调 API 用的是**相对路径 `/api/...`**（`worker/index.js` 只是同源反代）。因此把**前端构建产物和后端塞进同一个容器**即可：

> Worker、`API_ORIGIN`、Cloudflare 隧道、CORS、地址漂移 —— 五个麻烦全部消失。

而「数据不持久」在本场景是**优点**：容器启动时用已有的 `frontend/seed_demo.py` 灌演示数据 → 每次唤醒都是干净、满数据的演示环境。

### 已产出文件（2026-10-07 完成）

| 文件 | 内容 |
|---|---|
| `Dockerfile`（新增） | 两阶段：`node:22-slim` 跑 `npm ci && npm run build` → `python:3.12-slim` 装后端依赖、COPY `dist`、非 root（uid 1000）、`EXPOSE 7860` |
| `.dockerignore`（新增） | 排除 `node_modules`/`dist`/`.pydeps`/`.tmp` 等。**必须排除 `frontend/node_modules`**，否则 `COPY frontend/` 会覆盖 `npm ci` 的结果 |
| `docker/entrypoint.sh`（新增） | 起 uvicorn → 轮询 `/health` → `TRIP_DB` 不存在时跑 `seed_demo.py` → `wait`；LF 行尾，`trap` 转发 TERM |
| `README.md` | 顶部加 HF front matter：`sdk: docker` + `app_port: 7860` |
| `backend/app/main.py` | `SPAStaticFiles` 挂到 `/`；`/api` 前缀不回落 |
| `frontend/seed_demo.py` | `BASE` 改为读 `TRIP_API_BASE`（默认值不变，向后兼容） |

### 本地验收（2026-10-07 通过）

本机**没装 Docker**，改为「不用 Docker 跑同一条链路」：`npm run build` 产出 `dist/` → uvicorn 起在 **7860** → curl 打真实 HTTP。

```
health                 : 200
index  /               : 200   （含 <div id="app">）
deeplink /trips/x      : 200   （回落内容与 index 逐字节相同）
api/nope (期望 404)    : 404   （JSON，未回落成 HTML）
sw.js / assets js      : 200
真实深链接 /trips/<id> : 200
seed 后 api/trips      : 1 条  （12 条目 / v12 / 1 条待审提议）
```

**过程中修掉一个真 bug**：`StaticFiles` 抛的是 `starlette.exceptions.HTTPException`，而 `fastapi.exceptions.HTTPException` 是它的**子类**——最初 `except fastapi.HTTPException` 接不住，深链接刷新直接 404（首轮实测已复现）。现改为捕获 starlette 版本。

### 遗留环境问题（与 HF 方案无关，但会挡路）

- 工作区 `.pydeps/`、`.tmp/`、`.piptmp/` **权限异常**：`Get-Content` 报 Access denied，pip 无法清理自己的临时目录。本机跑后端/测试要读 `.pydeps` → **目前必须提权（danger-full-access）**。属工作区 ACL 问题，未修复。
- `%TEMP%\dsh-*` 不可写 → pip 必须先把 `$env:TMP` 指向工作区内目录。
- `vite build` 需提权（esbuild spawn EPERM，同 §13）。
- 本机 PowerShell 不支持 `Invoke-WebRequest -SkipHttpErrorCheck`，探测 HTTP 一律用 `curl.exe`。

### 用户侧三步（只有这三步做不了，必须用户本人）

1. 注册 HF 账号 —— **需要代理**（`huggingface.co` 被墙）
2. New Space → SDK 选 **Docker** → 命名 `trip-collab` → 得到 `https://<用户名>-trip-collab.hf.space`
3. 上传项目（网页拖拽或 `git push`）

### 已知代价（已与用户确认接受）

- 休眠后冷启动 1–2 分钟 → **演示前先访问一次预热**
- 容器重启数据清零；上传的图片同理 → 若演示需传图，先改成内置示例图
- 首次构建可能排队

### 定论

Cloudflare Workers 那份（§12）保留不动，作为冗余入口。**域名不必买**，VPS 方案搁置。

## 15. 方案再变更：回到隧道直出完整应用（2026-10-07）

### 为什么推翻 §14

用户否决 HF Spaces：**创建/上传 Space 需要一次性代理**，对研究性报告场景不合适——演示当天同学老师不需要代理，但「必须翻墙才能维护」这一点已足以否定它，且现场若需重启或改配置就会卡住。

复核时又发现一个更硬的问题：**原版 Worker 方案的门面地址已经不可用**。

```
app.trip-collab.workers.dev    HTTP  → http=000（20s 超时）
                               DNS   → @223.5.5.5 返回 192.133.77.197（假 IP）
```

即 §12 记录的 workers.dev DNS 污染已从「本机打不开」恶化到彻底不可用。**所以「回到原版隧道」不能是「Worker + workers.dev」，否则演示当场打不开。**

### 新拓扑：隧道直出完整应用

```
老师/同学 → https://<随机>.trycloudflare.com
                     ↓ cloudflared
               127.0.0.1:8000
               ├─ /       前端 frontend/dist（SPAStaticFiles，深链接回落 index.html）
               └─ /api/*  FastAPI
```

- **同源** → 无需 CORS、无需 Worker、无需 `vars.API_ORIGIN`
- 不买域名、不用梯子、不用 Cloudflare 账号
- 依据：§12 对照实验证明该网络能正确解析并连通 trycloudflare 的 Cloudflare IP（`104.16.231.132` 等）

### 保留 / 撤除

| 文件 | 处置 | 原因 |
|---|---|---|
| `backend/app/main.py`（`SPAStaticFiles`） | **保留** | 隧道直出完整应用的开关；`dist` 不存在时自动跳过，向后兼容 |
| `frontend/seed_demo.py`（`TRIP_API_BASE`） | **保留** | 默认值不变，向后兼容 |
| `.gitignore`（`.vdeps/.piptmp/.verify`） | **保留** | 本地缓存忽略，与部署形态无关 |
| `Dockerfile`、`docker/entrypoint.sh`、`.dockerignore`、`.gitattributes` | **撤除** | 纯 HF 打包产物 |
| `README.md` 顶部 HF front matter | **撤除** | HF 专用元数据 |

HF 那套的文件与验收记录仍留在提交 `e6f63a0` / `1f3b44d` 中；将来若要重走 HF 路线，`git cherry-pick` 即可恢复。

### 代价（已与用户确认接受）

- **笔记本必须保持唤醒 + 联网 + `cloudflared` 存活**，否则页面能开、接口不通
- **临时隧道地址每次重启都变** → 每次演示前重新分享新网址（需固定地址则走 §12 的「命名隧道 + 自有域名」）
- trycloudflare 偶发 ECONNRESET（§12 已记录）→ 隔几分钟重试即可

### 演示操作手册

```powershell
# 0) 前置：frontend/dist 必须已构建（npm run build；vite build 需提权，见 §13）

# 1) 起后端（同时托管 frontend/dist 与 /api）
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000

# 2) 播种演示数据（幂等，每次新建一个行程）
python frontend/seed_demo.py

# 3) 起隧道 → 在输出里找 https://<随机>.trycloudflare.com，分享给老师同学
& 'D:\dsh\trip project\.tools\cloudflared-windows-amd64.exe' tunnel --url http://127.0.0.1:8000
```
