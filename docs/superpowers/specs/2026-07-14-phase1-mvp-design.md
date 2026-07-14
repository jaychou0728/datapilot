# DataPilot Phase 1 MVP — 设计文档

> 日期：2026-07-14
> 状态：已确认

## 项目定位

上传 Excel/CSV → AI 自动完成数据清洗、SQL 查询、图表可视化、智能对话。

## 技术栈

| 模块 | 选型 |
|------|------|
| 后端框架 | Python + FastAPI |
| 数据分析 | Pandas |
| SQL 引擎 | DuckDB（持久化 .duckdb 文件） |
| AI | DeepSeek API（图表推荐、SQL 生成、对话） |
| 前端 | Vue 3 + Element Plus + ECharts |
| 状态管理 | Pinia |
| 部署 | Docker + Nginx（Phase 2） |

## 架构决策

**分层架构：API → Service → Data 三层。**

- `api/` — 路由，参数校验，调用 service
- `service/` — 业务逻辑，编排 data 和 ai
- `data/` — DuckDB 管理 + 文件存储
- `ai/` — DeepSeek API 封装
- `model/` — Pydantic 请求/响应模型

**数据持久化：**
- 上传文件存 `uploads/{dataset_id}/` 目录
- 每个数据集独立 `.duckdb` 文件，存 `duckdb_data/{dataset_id}.duckdb`
- 超过 7 天未访问的数据自动清理

**AI 调用：** Phase 1 同步调用（30s 超时），Phase 2 改后台任务队列。

## 后端目录结构

```
backend/
├── app/
│   ├── main.py              # FastAPI 入口 + 生命周期
│   ├── config.py            # 配置管理
│   ├── api/
│   │   ├── router.py        # 汇总路由
│   │   ├── datasets.py      # /api/datasets/*
│   │   ├── cleaning.py      # /api/cleaning/*
│   │   ├── query.py         # /api/query/*
│   │   ├── charts.py        # /api/charts/*
│   │   └── chat.py          # /api/chat/*
│   ├── service/
│   │   ├── dataset_service.py
│   │   ├── cleaning_service.py
│   │   ├── query_service.py
│   │   ├── chart_service.py
│   │   └── chat_service.py
│   ├── ai/
│   │   └── deepseek_client.py
│   ├── data/
│   │   ├── duckdb_manager.py
│   │   └── file_store.py
│   ├── model/
│   │   ├── dataset.py
│   │   ├── cleaning.py
│   │   ├── query.py
│   │   ├── chart.py
│   │   └── chat.py
│   └── utils/
│       ├── file_parser.py   # Excel/CSV 统一解析
│       └── response.py      # 统一响应格式
├── uploads/
├── duckdb_data/
├── requirements.txt
└── Dockerfile
```

## 前端目录结构

```
frontend/src/
├── main.ts
├── App.vue
├── router/index.ts
├── api/
│   ├── client.ts            # axios 实例
│   ├── datasets.ts
│   ├── cleaning.ts
│   ├── query.ts
│   ├── charts.ts
│   └── chat.ts
├── stores/
│   └── useDataset.ts        # Pinia store
├── views/
│   ├── Dashboard.vue        # 首页（数据集列表）
│   ├── DatasetDetail.vue    # 核心页面（5 个 Tab）
│   ├── Upload.vue           # 上传页面
│   └── History.vue          # 操作历史
├── components/
│   ├── DataTable.vue        # 复用表格
│   ├── ChartPanel.vue       # 复用图表
│   ├── DatasetSidebar.vue   # 字段信息侧栏
│   └── AiLoading.vue        # AI 加载动画
└── utils/
    └── format.ts
```

## 页面路由

- `/` → Dashboard（数据集列表）
- `/datasets/:id` → 数据详情页（5 个 Tab：预览/清洗/图表/SQL/AI 对话）
- `/upload` → 上传页面
- `/history` → 历史记录

## API 设计

### 统一响应格式

```json
{ "code": 0, "data": {...}, "message": "ok" }
```

### 数据集

- `POST /api/datasets/upload` — 上传文件（multipart），返回 `DatasetInfo`
- `GET /api/datasets` — 获取所有数据集列表
- `GET /api/datasets/{id}` — 获取单个数据集元信息
- `DELETE /api/datasets/{id}` — 删除数据集
- `GET /api/datasets/{id}/preview?page=1&page_size=50` — 分页预览数据

**DatasetInfo**: `{ id, name, rows, columns, fields: [{name, dtype, null_count, sample_values}], created_at }`

### 数据清洗

- `POST /api/cleaning/{dataset_id}/scan` — 扫描问题，返回 `CleaningIssue[]`
- `POST /api/cleaning/{dataset_id}/execute` — 执行清洗（传勾选的 actions），返回 `CleanResult`
- `POST /api/cleaning/{dataset_id}/undo` — 撤销清洗

**CleaningIssue**: `{ type, column, count, sample, severity }`
**CleanResult**: `{ rows_before, rows_after, changes[], can_undo }`

### SQL 查询

- `POST /api/query/execute` — 执行查询

**QueryRequest**: `{ dataset_id, sql?, natural_language? }`（二选一）
**QueryResult**: `{ columns[], rows[], row_count, executed_sql, ai_explanation? }`

安全规则：只读连接，禁止 INSERT/UPDATE/DELETE/DROP/ALTER，结果自动 LIMIT 1000。

### 图表

- `POST /api/charts/recommend` — AI 推荐图表

**ChartRecommendation**: `{ charts: [{ title, chart_type, echarts_option, reason }] }`

返回的 `echarts_option` 是直接可用的 ECharts 配置对象，前端拿到就能渲染。

### AI 对话

- `POST /api/chat` — 对话

**ChatRequest**: `{ dataset_id, message, history? }`
**ChatResponse**: `{ answer, sql_generated?, chart_suggestion? }`

AI 对话时可以顺带生成 SQL 或推荐图表。

## 数据流

### 上传链路
```
POST /api/datasets/upload (multipart)
→ datasets.py 校验文件类型和大小（≤50MB，仅 .xlsx/.xls/.csv）
→ dataset_service.py 调用 file_parser → Pandas DataFrame
→ file_store.py 保存原始文件到 uploads/{id}/
→ duckdb_manager.py 写入 .duckdb 持久化
→ 返回 DatasetInfo
```

### SQL 查询链路
```
POST /api/query/execute { dataset_id, sql / natural_language }
→ query_service.py:
  - 如果 sql 非空 → 校验 SQL 只读 → duckdb_manager 执行
  - 如果 natural_language 非空 → deepseek_client 生成 SQL → duckdb_manager 执行
→ 返回 QueryResult
```

### AI 对话链路
```
POST /api/chat { dataset_id, message, history }
→ chat_service.py 组装 prompt（含表结构上下文 + 历史消息）
→ deepseek_client.py 调用 API
→ 如果 AI 决定生成 SQL → 自动执行 → 结果注入回复
→ 返回 ChatResponse
```

## 错误处理

### 上传
- 超过 50MB → 拒绝
- 非 .xlsx/.xls/.csv → 拒绝
- Pandas 解析失败 → 提示文件损坏
- 空文件 → 提示无数据
- CSV 编码 → 自动检测 utf-8/gbk/gb2312

### SQL
- 语法错误 → 返回具体错误信息
- 写操作 → 拦截拒绝
- 结果超过 1000 行 → 截断并提示
- 执行超过 30s → 中断
- AI 生成 SQL 无效 → 重试一次，仍失败则提示换种方式描述

### AI 调用
- API Key 未配置 → 返回 "AI 服务未配置"
- 网络超时 → 返回 "AI 服务响应超时"
- 余额不足 (402) → 返回 "AI 服务账户余额不足"
- 返回格式异常 → 降级为纯文本
- 速率限制 (429) → 提示稍后再试

### 清洗
- 执行前自动备份 → 支持撤销
- 去重后数据为空 → 自动撤销并提示
- 全列空值 → 建议删除列而非填充

### 全局
- 数据集不存在 → 404，前端跳首页
- 网络错误 → axios 拦截器统一处理
- 7 天未访问 → 自动清理

## 测试策略

Phase 1 至少覆盖：

- **后端单元测试**（pytest）：dataset_service、cleaning_service、query_service 核心逻辑
- **API 集成测试**：上传 → 预览 → 清洗 → 查询 完整链路
- **前端不要求测试**（Phase 2 补充）

## 不在 MVP 范围

- 用户登录 / JWT 认证（Phase 2）
- PDF 报告导出（Phase 2）
- Dashboard 统计面板（Phase 2）
- 异步任务队列（Phase 2）
- 数据血缘追踪（Phase 3）
- Redis 缓存（Phase 3）
