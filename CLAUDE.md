# DataPilot — AI 驱动的数据分析平台

## 启动方式

```bash
# 后端 (terminal 1)
cd backend
cp .env.example .env   # 填入 DEEPSEEK_API_KEY
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000

# 前端 (terminal 2)
cd frontend
npm run dev             # → http://localhost:5173

# Docker 部署
cp .env.example .env    # 根目录 .env，填入 DEEPSEEK_API_KEY + JWT_SECRET
docker-compose up -d    # → http://localhost
```

## 技术栈

| 层 | 技术 |
|---|------|
| 后端 | Python FastAPI + DuckDB + SQLite + Pandas |
| AI | DeepSeek API（通过 BaseLLMClient 抽象） |
| 前端 | Vue 3 + Element Plus + ECharts + Pinia + mitt |
| 部署 | Docker Compose + Nginx |

## 架构约定

**后端三层**：`api/`（路由+参数校验）→ `service/`（业务逻辑）→ `data/`（存储）

**每条路由文件模式**：
```python
router = APIRouter(prefix="/api/xxx", tags=["xxx"])
svc = XxxService()  # 模块级单例

@router.post("/path")
def handler(req: RequestModel, user: dict = Depends(get_current_user)):
    try:
        result = svc.do_something(req)
        return success(data=result)
    except SomeError as e:
        return error(400, str(e))
```

**统一响应**：`{"code": 0, "data": ..., "message": "ok"}`。`code !== 0` 表示错误。前端 axios 拦截器自动解包 `data.data`。

**DuckDB**：每个数据集一个独立文件 `duckdb_data/{dataset_id}.duckdb`，表名固定为 `data`。写操作关键词被拦截。

**SQLite** (`data.db`)：存用户、操作日志、报告索引、任务队列、版本记录。连接通过 `get_db()` 创建，每次操作后关闭。

## 关键文件

```
backend/app/
├── main.py                    # FastAPI 入口、CORS、启动事件、全局异常处理
├── config.py                  # dotenv 加载所有环境变量
├── database.py                # SQLite 连接 + init_db() 建表
├── api/router.py              # 汇总所有子路由
├── ai/
│   ├── base.py                # BaseLLMClient 抽象类
│   └── deepseek_client.py     # DeepSeek 实现
├── prompts/                   # Prompt Registry（8 个 .txt 模板）
│   └── manager.py             # prompt("name", **vars) → str | (sys, user)
├── service/
│   ├── dataset_service.py     # 上传/预览/列表/删除
│   ├── cleaning_service.py    # 规则扫描 + AI 分析 + AI 执行（9 种操作）
│   ├── query_service.py       # SQL 执行 + NL→SQL
│   ├── chart_service.py       # 6 维数据画像 + 图表推荐
│   ├── chat_service.py        # 数据上下文 + AI 对话 + 自动执行 SQL
│   ├── report_service.py      # AI 报告生成 + PDF 导出（Playwright）
│   ├── agent_service.py       # 6 步流水线（画像→清洗→图表→洞察→报告→输出）
│   ├── version_service.py     # 数据版本快照/回滚/对比
│   ├── task_service.py        # 异步任务 CRUD
│   └── history_service.py     # 操作日志
└── data/
    ├── duckdb_manager.py      # DuckDB 连接/查询/安全检查
    └── file_store.py          # 文件存取/过期清理

frontend/src/
├── views/DatasetDetail.vue    # 核心页面（280 行，编排层）
├── components/
│   ├── CleaningPanel.vue      # 清洗面板（独立组件，崩了不影响页面）
│   ├── ChartPanel.vue         # ECharts 图表（自动 dispose）
│   ├── DataTable.vue          # 通用表格+分页
│   └── TaskProgress.vue       # 异步任务进度
├── stores/
│   ├── eventBus.ts            # mitt 事件总线
│   ├── useAuth.ts             # 认证状态
│   ├── useDataset.ts          # 数据集元数据
│   ├── useCleaning.ts         # 清洗流程（广播 dataset:cleaned / dataset:undo）
│   └── useChart.ts            # 图表推荐+数据填充
├── composables/useChart.ts    # ECharts 生命周期封装
└── api/                       # Axios API 模块（每个文件对应一组后端路由）
```

## 2026-07 本次会话改动

1. **Prompt Registry** — 所有 AI Prompt 从代码提取到 `backend/app/prompts/*.txt`，`---` 分隔 System/User
2. **LLM Adapter** — `BaseLLMClient` 抽象基类，`DeepSeekClient` 实现
3. **状态管理重构** — 引入 mitt Event Bus，拆分 Pinia Stores（useCleaning / useChart），提取 CleaningPanel 组件
4. **Dataset Versioning** — 每次清洗前自动创建 DuckDB 快照，撤销=回滚到最新版本
5. **Agent Pipeline 修复** — `BackgroundTasks.add_task()` 不支持 async 函数，改为 `threading.Thread` + 独立 event loop
6. **历史记录补全** — 删除操作、一键分析各步骤均记录历史；修复时间戳（`datetime.now().isoformat()` 替代 SQLite CURRENT_TIMESTAMP）
7. **图表黑屏修复** — AI 生成饼图可能不带 color 数组，ChartPanel 渲染前注入默认 9 色调色板
8. **撤销修复** — 从内存备份改为基于版本回滚
9. **数据血缘** — 后端存在但前端已移除（多次尝试仍无法正常显示）
10. **列语义配置** — 后端存在但前端已移除（用户不需要）

## 前端事件流

```
CleaningPanel 执行清洗
  → useCleaning.execute()
  → API 调用成功
  → bus.emit('dataset:cleaned')

DatasetDetail 监听
  → bus.on('dataset:cleaned', refreshAfterClean)
  → loadPreview() 局部刷新
```

## 避坑指南（本会话踩过的全部坑）

### 后端

| # | 问题 | 错误做法 | 正确做法 |
|---|------|---------|---------|
| 1 | **BackgroundTasks 不支持 async** | `background_tasks.add_task(async_func, ...)` — 函数永远不会执行 | 用 `threading.Thread(target=sync_wrapper, daemon=True).start()` + 线程内 `asyncio.new_event_loop()` |
| 2 | **撤销永远失败** | `CleaningService._backup_df` 存内存，HTTP 请求结束就没了 | 每次清洗前用 `VersionService.create()` 创建 DuckDB 快照；撤销 = `rollback()` 到最新版本 |
| 3 | **DuckDB Windows 文件锁** | 先开 DuckDB 连接，再 `shutil.copy2()` 覆盖同一文件 | 先 `mgr.query()` 拿到数据，`finally` 已关连接，再 `shutil.copy2()` |
| 4 | **SQLite 时间戳不一致** | INSERT 不写 `created_at`，靠 `DEFAULT CURRENT_TIMESTAMP` | INSERT 时显式传 `datetime.now().isoformat()`；`init_db()` 只建表，不依赖 DEFAULT |
| 5 | **Prompt 模板解包错误** | `sys_msg, user_msg = prompt("explain_sql", ...)` — 模板无 `---` 返回单个字符串，解包报 `too many values` | 先看 `.txt` 有没有 `---`：有→tuple 解包，没有→单变量接收 |
| 6 | **Agent Pipeline 不记历史** | Agent 直接调 `service` 层，绕过了 `api` 层的 `hist_svc.log()` | Agent 内部自己调 `hist_svc.log()` + `lineage_svc.log()` |
| 7 | **`asyncio.get_event_loop()` 废弃** | 在已有 event loop 的线程里调 `get_event_loop()` | 用 `asyncio.get_running_loop()`（Python 3.10+）；新线程用 `new_event_loop()` |
| 8 | **新增 SQLite 表不生效** | `init_db()` 用 `executescript()`，前一条失败后面全部跳过 | 关键表在 `lineage_service.py` 的 `_ensure_table()` 中独立 `CREATE TABLE IF NOT EXISTS` |

### 前端

| # | 问题 | 错误做法 | 正确做法 |
|---|------|---------|---------|
| 9 | **全页 `v-loading` 卡死所有 Tab** | `<div v-loading="store.loading">` 包裹整个页面 | 去掉顶级 v-loading；每个功能块独立管理自己的 loading ref |
| 10 | **`store.load()` 滥用** | 每次清洗/撤销后调 `store.load()` 全页重载 | 只调 `loadPreview()` 刷新数据表格；用 Event Bus 通知其他模块按需刷新 |
| 11 | **ElMessage 导入污染组件** | 在 DatasetDetail.vue 中 `import { ElMessage } from 'element-plus'` — 可能导致整个组件编译报错 | ElMessage 只在 `client.ts` 的 axios 拦截器中使用；页面组件通过 `try/catch` 处理错误 |
| 12 | **el-tab-pane 重复 name** | 两个 `<el-tab-pane name="lineage">` — Element Plus 渲染错乱 | 每个 tab pane 的 name 必须唯一；删除旧版再加新版 |
| 13 | **v-if 模板访问 undefined** | `metaForms[field.name].label` — `metaForms` 为空对象时抛 TypeError，整个组件崩溃 | 提供安全访问函数 `getMeta(col)` 返回默认值；或初始化时填充所有字段 |
| 14 | **ChartPanel composable 导致导出失效** | `useChart()` composable 内部 `instance` 变量闭包问题，`exportPng()` 静默失败 | ChartPanel 逻辑直接内联，不包装 composable；`doExport()` 用 `a.click()` 不需 `appendChild` |
| 15 | **ECharts 不 dispose 导致内存泄漏** | `onMounted` 里 `echarts.init()`，没有 `onUnmounted` 清理 | 必须 `onUnmounted(() => { chart?.dispose(); chart = null })` |
| 16 | **ECharts 饼图全黑** | AI 生成的 `echarts_option` 可能不带 `color` 数组 | 渲染前先 `chart.setOption({ color: [9色] }, false)` 设置默认色板，再叠加 AI 配置 |

---

## 开发规范

### 后端规范

1. **所有 INSERT 必须显式写 `created_at`**：`datetime.now().isoformat()`，不依赖 SQLite DEFAULT。
2. **新增 SQLite 表**：在 `database.py:init_db()` 加 `CREATE TABLE IF NOT EXISTS`；同时在对应 Service 的写方法里加 `_ensure_table()` 兜底。
3. **异步后台任务**：统一用 `threading.Thread(daemon=True)` + 线程内 `asyncio.new_event_loop()`。禁止 `BackgroundTasks.add_task()`。
4. **AI 调用必须 try/except**：DeepSeek API 可能超时/余额不足/限流。业务代码不能因 AI 不可用而崩溃。
5. **Prompt 修改**：只改 `prompts/*.txt`，Python 代码通过 `prompt("name", **vars)` 调用。改完 Prompt 必须检查调用方是 tuple 解包还是单变量。
6. **Route 文件保持薄**：只做参数校验 + 调 service + 调 `hist_svc.log()`。业务逻辑全在 service 层。
7. **DuckDB 操作前检查文件存在**：`os.path.exists(db_path)` 先判断，返回 404 而不是 500。
8. **非关键功能 silent fail**：lineage、metadata 写入失败不抛异常，`try/except: pass`。

### 前端规范

1. **页面组件不超过 300 行**：超过就提取子组件到 `components/`。
2. **禁止顶级 `v-loading`**：每个功能块自己管理 loading ref。
3. **状态跨组件通信用 Event Bus**：`bus.emit('xxx')` / `bus.on('xxx', handler)`。不在 A 组件里直接调 B 组件的方法。
4. **图表导出**：ChartPanel 逻辑全部内联，不包装 composable。`doExport()` 用 `a.click()`。
5. **Pinia Store 按功能拆分**：一个 store 只做一件事。不要在 store A 里 import store B。
6. **模板安全访问**：`v-for` 循环里访问嵌套对象，提供 `getXxx(key)` 安全访问函数，返回默认值。
7. **新增 Tab**：检查 `name` 不与其他 tab 重复；先删旧再添新。
8. **ECharts**：每个 ChartPanel 必须 `onUnmounted` 里 `dispose()`。渲染前先设默认色板。

### 通用规范

1. **改完代码重启服务**：后端改了 Python 文件需重启 uvicorn（或用 `--reload`）。
2. **前端改了 API 同步检查**：确认 `api/*.ts` 的路径和后端 `prefix` + 路由一致。
3. **数据操作前快照**：任何会修改 DuckDB 数据的操作，先调 `version_svc.create()` 创建版本。
4. **不要改 `CLAUDE.md` 的格式**：保持 Markdown，代码块用 ` ``` `，表格对齐。

---

## 功能状态矩阵

| 功能 | 后端 | 前端 | 状态 | 建议 |
|------|:--:|:--:|------|------|
| 数据上传/预览 | ✅ | ✅ | 完成 | — |
| 数据清洗 (规则+AI) | ✅ | ✅ | 完成 | — |
| 图表推荐 | ✅ | ✅ | 完成 | — |
| SQL 查询 (NL+手写) | ✅ | ✅ | 完成 | — |
| AI 对话 | ✅ | ✅ | 完成 | — |
| 一键分析 (Agent) | ✅ | ✅ | 完成 | — |
| 报告生成 + PDF | ✅ | ✅ | 完成 | — |
| 用户认证 + RBAC | ✅ | ✅ | 完成 | — |
| 操作历史 | ✅ | ✅ | 完成 | — |
| 数据版本 + 撤销 | ✅ | ✅ | 完成 | 只做 Undo，不做版本列表 UI |
| Prompt Registry | ✅ | — | 完成 | — |
| LLM Adapter | ✅ | — | 完成 | — |
| 数据血缘 | ✅ | ❌ | 后端保留，前端不展示 | 以后做 DAG 时再加 |
| 列语义 | ✅ | ❌ | 后端保留，前端不展示 | 以后 AI 自动生成建议 |
| useChart composable | ❌ | ❌ | 已回退 | 不需要，内联更稳 |
| 版本历史列表 | ✅ | ❌ | 已移除 | 浪费精力，Undo 就够了 |
| 血缘 DAG 图 | — | — | 未开始 | 等项目有多数据集时再做 |

---

## 开发路线图

### 第一优先 P0：稳定性 + 性能（现阶段重点）

| 任务 | 说明 | 为什么重要 |
|------|------|-----------|
| **Dataset Profile 缓存** | 上传时预计算画像（行数/列数/空值/分布/min/max），存到 SQLite 或 JSON。AI 分析时直接读，不再每次扫描 DuckDB | 一键分析速度提升 50%+，减少 DuckDB 查询次数 |
| **AI 结果缓存** | dataset hash + prompt → 缓存 AI 响应。同一数据同一问题不重复调 API | 省钱、快。DeepSeek API 按 token 计费 |
| **Task Queue 完善** | 所有 AI 操作统一走 Task（pending→running→done/failed），前端统一轮询 | 一键分析、报告生成、图表推荐都有进度反馈 |
| **修复已有 Bug** | 见上方避坑指南 | 不稳定的功能比没有更糟 |
| **交互打磨** | 加载状态、空状态、错误提示、按钮禁用逻辑 | 实习面试演示时第一印象 |

### 第二优先 P1：加分项（P0 完成后做）

| 任务 | 说明 |
|------|------|
| **Semantic Layer（AI 辅助）** | 后端保留，增加 AI 自动推断列含义（如 `amt`→"可能是金额"），用户一键确认 |
| **数据血缘记录** | 继续在关键操作点记录 lineage，不做前端 DAG |
| **Undo/Redo 完善** | 基于版本回滚，支持 Ctrl+Z 快捷键 |
| **Streaming AI 响应** | SSE 流式返回 AI 生成内容，改善长等待体验 |
| **前端 baseURL 环境变量** | `VITE_API_BASE_URL` 替换硬编码 localhost |

### 第三优先 P2：架构升级（工作后或大项目时做）

| 任务 | 说明 |
|------|------|
| Workflow Engine (DAG) | 替代线性 Pipeline，支持条件分支/并行/重试 |
| Plugin System | 异常检测/预测/聚类作为可插拔插件 |
| Execution Engine (Spark) | 10GB+ 数据场景 |
| 多数据集血缘 DAG | 跨数据集的字段级别血缘可视化 |

### 不建议继续投入

- **useChart() Composable** — 40 行逻辑，提取只会增加复杂度
- **版本历史列表 UI** — 用户只需要 Ctrl+Z，不需要看 v1/v2/v3
- **复杂血缘前端图** — 当前只有一个 dataset，画不出有意义的 DAG

---

## 项目定位（实习面试视角）

这是一个**大二学生的个人项目**，面向数据分析实习岗位。

**核心竞争力**：
- 全栈能力（FastAPI + Vue 3 + DuckDB + Docker）
- AI 集成（Prompt Engineering + LLM Adapter 抽象）
- 工程意识（状态管理重构、Event Bus 解耦、组件隔离、版本管理）
- 文档完整（CLAUDE.md + ARCHITECTURE.md）

**演示路径**（面试时 5 分钟走完）：
1. 上传一个 CSV → 看到数据预览
2. AI 分析数据质量 → 一键清洗
3. AI 推荐图表 → 展示交互式图表
4. 自然语言查询 → AI 生成 SQL 并解释结果
5. 一键分析 → 自动生成报告 → 导出 PDF

**加分展示**（如果面试官感兴趣）：
- 打开 `ARCHITECTURE.md` 展示架构设计
- 打开 `CLAUDE.md` 展示开发规范
- 打开 `prompts/` 目录展示 Prompt 工程
- 展示版本回滚（清洗后撤销）
