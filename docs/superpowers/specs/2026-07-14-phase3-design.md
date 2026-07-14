# DataPilot Phase 3 · 企业级升级 · 设计文档

> **目标：** 在 MVP 基础上添加 RBAC 权限、异步任务队列、AI Agent 一键自动化、数据血缘追踪、Docker 部署，使 DataPilot 具备企业级交付能力。

**架构：** 5 个子系统分层叠加。RBAC 是横切安全层，异步任务队列是基础设施，AI Agent 复用全部现有 Service 编排流水线，数据血缘在操作点旁路记录，Docker 统一打包。

**技术栈：** FastAPI BackgroundTasks + SQLite（异步队列），不引入 Celery/Redis。Docker Compose 前后端一体部署。

---

## 子系统一：RBAC 权限控制

### 数据模型

users 表新增 role 字段：

```sql
ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'user';
-- role ∈ {'admin', 'user'}
```

### 权限矩阵

| 操作 | admin | user |
|------|-------|------|
| 查看/操作自己的数据 | ✅ | ✅ |
| 查看所有人的数据和操作记录 | ✅ | ❌ |
| 上传/清洗/查询/图表/报告 | ✅ | ✅ |
| 查看用户列表 | ✅ | ❌ |
| 修改用户角色 | ✅ | ❌ |

### 中间件改造

`get_current_user_id` → `get_current_user`，返回 `{id, username, role}` 供所有路由使用。下游 API 根据 `role` 做数据过滤。

### 现有 API 权限改造点

- `GET /api/dashboard/stats` — admin 统计全量，user 只统计自己
- `GET /api/history` — admin 看全量，user 看自己
- `GET /api/reports` — 同上

### 新增 API

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/auth/users` | admin 查看用户列表 |
| PUT | `/api/auth/role` | admin 修改用户角色 |

### 前端

- App.vue 导航菜单：admin 可见"用户管理"入口
- Dashboard/History/Reports 页面自动按当前用户过滤（现有逻辑基本已是按 user_id 过滤，无需大改）

---

## 子系统二：异步任务队列

### 数据模型

```sql
CREATE TABLE task_queue (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    type TEXT NOT NULL,           -- 'agent_pipeline' | 'report_generate' | 'export'
    status TEXT DEFAULT 'pending', -- pending → running → done / failed
    progress INTEGER DEFAULT 0,   -- 0-100
    input JSON,                   -- 入参
    output JSON,                  -- 结果
    error TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    finished_at TIMESTAMP
);
```

### API

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/tasks` | 创建任务，返回 task_id |
| GET | `/api/tasks/{id}` | 查询任务状态（进度 + 输出） |
| GET | `/api/tasks` | 当前用户的任务列表 |
| DELETE | `/api/tasks/{id}` | 删除已完成/失败的任务 |

### 执行机制

FastAPI `BackgroundTasks.add_task()` 启动后台函数。函数内按子步骤更新 `progress` 和 `status`，无需消息队列。前端轮询 `GET /api/tasks/{id}` 每 2 秒获取进度。

### 前端

- 新建 `TaskProgress.vue` 组件（进度条 + 子步骤文字 + 成功/失败状态）
- 模态框或内嵌展示

---

## 子系统三：AI Agent 一键自动化

### 流水线定义

```
Step 1 (10%):  数据画像   → 复用 chart_service._profile_data()
Step 2 (25%):  智能清洗   → 复用 cleaning_service.ai_analyze() + ai_execute()
Step 3 (40%):  图表推荐   → 复用 chart_service.recommend()
Step 4 (60%):  洞察提取   → 新 prompt：提取 3-5 个关键洞察
Step 5 (80%):  报告生成   → 复用 report_service.generate()
Step 6 (100%): 聚合输出   → 保存报告 + 图表快照 + 血缘记录
```

### 新增 API

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/agent/run` | 启动一键分析，入参 `{dataset_id}`，返回 `{task_id}` |
| GET | `/api/agent/result/{task_id}` | 获取完整结果摘要 |

### 实现

- `agent_service.py` — `run_pipeline()` 函数，接受 dataset_id 和 task_id，顺序执行 6 步，每步更新任务进度
- `api/agent.py` — 创建 task 记录，调用 `BackgroundTasks.add_task(agent_service.run_pipeline)`

### 前端

DatasetDetail 页面顶部加 **"一键分析"** 按钮（强调色渐变），点击后弹出 TaskProgress 模态框，完成后跳转到报告页面。

---

## 子系统四：数据血缘追踪

### 数据模型

```sql
CREATE TABLE data_lineage (
    id TEXT PRIMARY KEY,
    task_id TEXT,                 -- 关联 agent pipeline 任务（可为空）
    user_id TEXT NOT NULL,
    dataset_id TEXT NOT NULL,
    operation TEXT NOT NULL,      -- 'upload' | 'clean_*' | 'chart' | 'query' | 'report'
    target TEXT NOT NULL,         -- 'column:销售额' | 'table:data' | 'rows:all'
    summary TEXT NOT NULL,        -- 人类可读摘要
    before_snapshot TEXT,         -- JSON: {row_count, columns, sample}
    after_snapshot TEXT,          -- JSON: 变换后快照
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### API

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/lineage/{dataset_id}` | 完整变换链（时间序列表） |
| GET | `/api/lineage/{dataset_id}/graph` | 节点+边数据（前端画 DAG 用） |

### 集成点

在以下位置各加一行 `lineage_service.log()`：
- `cleaning.execute()` — 每次执行清洗操作
- `cleaning.ai_execute()` — AI 清洗
- `datasets.upload()` — 数据上传
- `agent_service.run_pipeline()` — Agent 每步完成时

### 前端

DatasetDetail 新增 **"数据血缘"** 标签页，左侧时间轴列表展示变换链，右侧可选 ECharts 力导向图展示 DAG。

---

## 子系统五：Docker 部署

### 文件清单

```
datapilot/
├── docker-compose.yml
├── .env.example                  # DEEPSEEK_API_KEY=xxx / JWT_SECRET=xxx
├── backend/
│   └── Dockerfile
├── frontend/
│   ├── Dockerfile
│   └── nginx.conf
```

### docker-compose.yml

```yaml
version: "3.8"
services:
  backend:
    build: ./backend
    ports: ["8000:8000"]
    volumes:
      - uploads_data:/app/uploads
      - duckdb_data:/app/duckdb_data
      - sqlite_data:/app/data.db
      - reports_data:/app/reports
    environment:
      - DEEPSEEK_API_KEY=${DEEPSEEK_API_KEY}
      - JWT_SECRET=${JWT_SECRET}
    restart: unless-stopped

  frontend:
    build: ./frontend
    ports: ["80:80"]
    depends_on: [backend]
    restart: unless-stopped

volumes:
  uploads_data:
  duckdb_data:
  sqlite_data:
  reports_data:
```

### 后端 Dockerfile

基于 `python:3.12-slim`，安装依赖，`CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]`

### 前端 Dockerfile

`node:20-alpine` 构建 `npm run build` → 产出 `dist/` 复制到 `nginx:alpine`，配置反向代理 `/api/*` → `backend:8000`

### nginx.conf

```nginx
server {
    listen 80;
    root /usr/share/nginx/html;
    location / { try_files $uri /index.html; }
    location /api/ { proxy_pass http://backend:8000; }
}
```

---

## 实施顺序

按依赖关系推进：

1. **RBAC** — 基础安全层，先做避免后续返工
2. **异步任务队列** — 基础设施，Agent 依赖它
3. **AI Agent** — 复用 1+2，核心价值功能
4. **数据血缘** — 在 Agent 和清洗流程中旁路记录
5. **Docker** — 最后打包

---

## 自检清单

- [x] 所有数据模型有完整 SQL DDL
- [x] 所有 API 有方法 + 路径 + 说明
- [x] 前端改动点明确
- [x] 依赖关系清晰，实施顺序合理
- [x] 无 TBD / TODO / placeholder
- [x] 复用现有 Service，不推倒重来
