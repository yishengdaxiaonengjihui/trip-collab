# trip-collab 项目交接文档（HANDOVER）

> **给下一个会话的快速启动指引**：本文件是跨会话继续工作的唯一权威入口。
> 读完本文档后按「会话恢复指引」（§11）执行，即可无缝接续开发。

- 最后更新：2026-09-13（UI 升级已完成并推送，最新提交 `5ffa601`）
- 维护约定：**每个里程碑完成 / 每次会话结束前 / 需求或决策变化时，必须更新本文件**并提交推送。

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
| FastAPI 后端骨架 `backend/app/` | ✅ 完成（引擎集成 + SQLite 持久化 + 16 REST 路径 + 插件注册表） | **43 测试绿** + uvicorn 冒烟过 |
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
│   └── tests/             # 25 引擎 + 3 序列化 + 15 API = 43 测试
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
python -m pytest   # 43 passed
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
| 3 | 待审核卡片**预测性告警** | 引擎目前采纳时刻才检测冲突（last_report），前端待审核卡片无预先告警（与原型 mock 有差异）——扩展：create/submit 时预检并存 last_report；或等 UX 实测反馈再定 | UX 实测反馈 |
| 4 | 讨论区/评论 | API 未实现（原型有 mock 评论），MVP 后置项 | 后置 |
| 5 | ~~时间字段建模~~ | ✅ **已实现（2026-09-13）**：`Item.time`（展示时间，时间线排序/显示）+ `Item.tag`（类型） | — |
| 6 | 插件升级 | weather/poi 从 Mock 换真实供应商（保持 degraded 降级语义） | 阶段 2 |
| 7 | 许可证决策 | TripStar GPL-2.0 模块移植与否直接影响发布许可证（TBD） | 任何对外发布前 |

## 10. 产品决策点（待定记录）

- **待审核告警展示**：采纳时刻检测（当前）vs 提交时刻预检（原型 UX）。倾向：UX 实测里观察用户是否困惑于"采纳时才弹窗"。
- **emergency 语义**：提交即采纳、可 formalize/revoke（逆操作恢复采纳前快照），已定稿实现。
- **版本起始**：新行程 v0（空事件流）；首个采纳 → v1。前端显示 v0。
- **时间/类型字段**：✅ 已落地（2026-09-13）。`time` 存展示时间字符串（"HH:MM"，前端解析排序，无时间按 position 殿后）；`tag` 存中文类型值（景区/饭店/酒店/交通/购物/其他，空=其他），前端映射颜色。待议：是否引入枚举校验/多语言（MVP 暂用自由字符串）。
- **条目类型体系**：当前 6 类（景区/饭店/酒店/交通/购物/其他）由前端 `TripView.vue` 的 `TAG_CLASS` 映射颜色；新增类型只需加映射。是否支持自定义标签待 UX 反馈。
- **评论/投票**：需求 V1.3 后置；不阻塞 MVP 骨架。

## 11. 会话恢复指引（新会话第一件事）

1. 读本文件（`docs/HANDOVER.md`）→ 读 `docs/REQUIREMENTS.md` 对应章节。
2. 确认仓库状态：`git status -sb`（应干净）+ `git log --oneline`（对照 §4 提交历史）。
3. 跑基线验证：`python -m pytest`（应 43 passed）。
4. 若任务涉及前后端运行：按 §6 启动 + `python frontend/seed_demo.py` 播种。
5. 先处理 §9 清单顶部的任务；遇到环境问题查 §8。
6. **会话结束时**：把进展/决策/坑更新进本文件（更新日期与提交号），提交推送。
