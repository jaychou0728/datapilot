# DataPilot

AI 驱动的数据分析平台。上传 Excel/CSV，一键完成数据清洗、图表生成、SQL 查询和商业分析报告。

## 技术栈

| 层 | 技术 |
|---|------|
| 后端 | Python FastAPI + DuckDB + SQLite |
| AI | DeepSeek API（图表推荐、SQL 生成、对话、报告） |
| 前端 | Vue 3 + Element Plus + ECharts |
| 部署 | Docker Compose + Nginx |

## 快速开始

### 开发模式

```bash
# 后端
cd backend
pip install -r requirements.txt
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000

# 前端
cd frontend
npm install
npm run dev
```

浏览器打开 `http://localhost:5173`。

### Docker 部署

```bash
cp .env.example .env   # 编辑填入 DEEPSEEK_API_KEY
docker-compose up -d
```

浏览器打开 `http://localhost`。

## 功能

- **数据上传** — 支持 CSV / Excel，自动识别编码，DuckDB 持久化存储
- **AI 智能清洗** — 9 种安全操作（货币清理、数字提取、大小写统一、去重等），不用 AI 生成的 SQL
- **图表推荐** — 基于 6 维数据画像（聚合/时序/散点/直方图/相关性/极值）自动推荐最佳图表
- **SQL 查询** — 自然语言 + SQL 双模式，AI 解释查询结果
- **AI 对话** — 带数据上下文的对话，AI 自动执行 SQL 并展示结果
- **一键分析** — AI Agent 流水线：画像 → 清洗 → 图表 → 洞察 → 报告
- **分析报告** — AI 生成结构化报告（文本 + 图表），支持 PDF 导出
- **数据血缘** — 追踪从上传到报告的每一步数据变换
- **用户权限** — JWT 认证 + RBAC（管理员/普通用户），数据集按用户隔离

## 项目结构

```
backend/
├── app/
│   ├── ai/              DeepSeek 客户端 + Prompt 工程
│   ├── api/             FastAPI 路由（auth/datasets/cleaning/query/charts/chat/agent）
│   ├── data/            DuckDB 管理器 + 文件存储
│   ├── middleware/      JWT 认证中间件
│   ├── model/           Pydantic 数据模型
│   ├── service/         业务逻辑层
│   └── utils/           文件解析 + 响应工具
├── tests/               12 个单元测试
└── requirements.txt

frontend/src/
├── api/                 Axios API 模块
├── components/          ChartPanel / DataTable / TaskProgress
├── stores/              Pinia 状态管理（auth + dataset）
├── views/               页面组件
└── router/              路由 + 鉴权守卫
```

## 测试

```bash
cd backend
pytest tests/ -v
```
