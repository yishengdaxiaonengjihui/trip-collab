# trip-collab — AI 多人提议式旅行协作规划系统

面向朋友、家庭、小队长途结伴出游的**行程方案协作工具**（移动端 PWA 优先）。

> 别人是"大家随便改行程"，本项目是"大家随便提方案，定稿统一合并，全程可追溯、可回滚、无争吵"。

## 核心机制

- 每个旅行 = 一个独立项目，内含一份**定稿行程**（团队认可的基准方案）。
- 任意成员可提交**提议**（一组行程增/删/改操作 + 理由），团队可评论讨论，管理员/投票采纳或拒绝。
- 所有变更永久留痕，支持回看历史快照、一键回滚。
- 底层采用**事件溯源模型**（定稿 = 已采纳事件顺序回放结果），天然支持版本、回滚、临时变更。
- 上层界面完全隐藏分支/PR/Git 术语，用户仅感知【定稿行程、提议、采纳、拒绝、回滚】。
- 支持出发前规划 + 旅途中现场应急调整（景区临时关闭、游玩超时、临时换路线等）。
- AI、爬虫、OTA 查询全部为**可降级插件**：核心协作模块不依赖任何第三方接口，插件失效主系统依旧完整可用。
- 仅做信息查询展示，预订跳转官方平台，不实现购票、支付。

## 技术栈

- 后端：FastAPI（Python）
- 前端：Vue 3 + Vite + PWA（移动端优先）
- 数据库：SQLite（轻量部署，后续可换 MySQL）
- AI 层：本地/在线大模型 + RAG 检索
- 协作核心：自研事件溯源 diff / 提议 / 合并引擎

## 当前状态

1. ✅ **事件溯源引擎原型**：`backend/engine/`（提议/采纳/回滚/冲突判定/临时备选/序列化），25 个单元测试全绿，设计决策见 [docs/SPIKE.md](docs/SPIKE.md)。
2. ✅ **移动端交互原型**：`frontend/prototype/index.html`（纯静态，双击即开），8 项自动化交互断言全绿。
3. ⏳ **UX 实测（待执行）**：按 [docs/UX_TEST.md](docs/UX_TEST.md) 招募 3~5 名真实出行群体测试「提议-采纳-回滚」与旅途应急场景。
4. ✅ **MVP 工程骨架**：FastAPI 后端（引擎集成 + SQLite 持久化 + 核心 REST API + 插件注册表雏形，42 测试全绿）+ Vue3/Vite/PWA 前端（五个视图对接 API，生产构建通过，端到端联调验证含依赖告警采纳流程）。

详细需求见 [docs/REQUIREMENTS.md](docs/REQUIREMENTS.md)。

> 🔄 **跨会话交接**：新会话请先读 [docs/HANDOVER.md](docs/HANDOVER.md)（项目状态、代码地图、运行手册、环境坑位、下一步任务）。每个里程碑/会话结束需更新它。

## 本地运行（MVP 骨架）

```bash
# 1. 后端（8000 端口）
cd backend
pip install -r requirements.txt        # fastapi / uvicorn / httpx / pytest
uvicorn app.main:app --reload --port 8000
# 或：python -m uvicorn backend.app.main:app --reload --port 8000（仓库根目录）

# 2. 前端（5173 端口，/api 自动代理到 8000）
cd frontend
npm install
npm run dev
# 浏览器打开 http://localhost:5173
```

- 演示数据：后端起来后执行 `python frontend/seed_demo.py`（建行程 + 基线条目 + 一条带依赖告警的待审核提议）。
- 后端测试：仓库根目录 `python -m pytest`（42 个用例）；前端构建 `cd frontend && npm run build`。
- 身份占位：请求头 `X-User-Id`（MVP 无登录系统），前端默认 `u_demo`。

## 架构速览

```
frontend/  Vue3 + Vite + PWA（移动端优先，五个视图：行程/提议/新建/版本/通知 + 旅途应急）
backend/
  engine/  事件溯源引擎（纯逻辑，与持久化无关，to_dict/from_dict 序列化）
  app/
    routers/  REST 路由（trips/proposals/versions/members/plugins）
    services/ 业务编排：加载/保存引擎、翻译 API 动作为引擎操作
    db.py     SQLite：trips/members 结构化，引擎状态整包 JSON（升级路径见文件头）
    plugins/  数据源插件注册表雏形（weather/poi Mock，均标记 degraded 可降级）
```

### 沙箱/无头环境注意事项（DSH 开发机）

- 沙箱禁止 python 递归删目录：pytest 依赖 `tmp_path` 的用例改为写 `backend/tests/.testdbs/` 固定目录（已适配）。
- npm 安装需 `--ignore-scripts`（沙箱拦截 postinstall 的 spawn/命名管道）；构建与 dev 需完整权限（esbuild 以命名管道 spawn 子进程）。
- 无头浏览器验证前端用 obscura：`obscura fetch http://localhost:5173/... --allow-private-network`；交互点击流走 `obscura serve`（CDP）+ `frontend/cdp_adopt_test.mjs`。

## 路线图

| 阶段 | 内容 | 状态 |
|---|---|---|
| 第 0 周 | Spike：事件溯源引擎原型 + UX 验证 | 引擎✅ 原型✅ UX 实测⏳ |
| MVP | 核心协作闭环：项目/邀请/角色、定稿时间线、提议全流程、快照回滚、应用内通知、旅途快速提议、最简 AI 生成到草稿、离线只读、预算预留字段、插件 Mock 接口 | 骨架✅（待 UX 实测通过后开工） |
| 阶段 2 | 12306/酒店数据插件（可降级）、短途交通插件、完整预算模块 | 未开始 |
| 阶段 3 | 小红书攻略插件 + AI 摘要、RAG 知识库、AI 时间线连锁推演/冲突检测、景区公告预警 | 未开始 |
| 阶段 4 | 行李清单、天气联动、PWA 推送、离线草稿、投票评论、图片附件 | 未开始 |

## 开源复用参考（仅模块级移植，不 fork 整仓）

- **TripStar**（GPL-2.0）：AI 多智能体行程生成、小红书解析——按模块移植。
- **Voyago**（MIT）：12306/高德/酒店数据封装——按 MIT 直接借鉴。
- **TREK**（AGPL-3.0）：时间线/地图 UI 设计思路——只看不抄代码。

## 许可证

未定（TBD）。注意：若移植 TripStar 的 GPL-2.0 代码，本项目需以 GPL-2.0 发布；若想要宽松许可证，需自行重写 AI 编排层。
