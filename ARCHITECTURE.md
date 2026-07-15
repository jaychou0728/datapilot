# DataPilot 完整技术文档（AI Agent 参考）

本文档供 AI Agent 理解整个 DataPilot 项目的所有技术细节，无需阅读源码即可完全掌握项目结构、数据流、函数签名和约定。

---

## 一、项目概述

DataPilot 是一个 AI 驱动的 Web 数据分析平台。用户上传 CSV/Excel，系统通过 DeepSeek API 完成数据清洗、图表推荐、SQL 查询、对话分析和报告生成。

**核心流程**: 上传 → 预览 → AI 清洗 → 图表推荐 → NL→SQL → 一键分析 → PDF 报告

## 二、技术栈与版本

| 层 | 技术 | 关键依赖 |
|---|---|---|
| 后端框架 | Python 3.10+ FastAPI | uvicorn, pydantic |
| 数据存储 | DuckDB (列式分析) + SQLite (元数据) | duckdb, pandas, numpy |
| AI | DeepSeek API (OpenAI 兼容) | openai (SDK) |
| PDF | Playwright (chromium headless) | playwright |
| 前端 | Vue 3 + Vite | element-plus, echarts, pinia, vue-router, marked, mitt |
| 部署 | Docker Compose + Nginx | — |

## 三、目录结构（完整版）

```
datapilot/
├── .env.example                    # 根目录环境变量模板 (DEEPSEEK_API_KEY, JWT_SECRET)
├── docker-compose.yml              # backend:8000 + frontend:80 + 4 volumes
├── CLAUDE.md                       # 开发规范与人机约定
├── README.md                       # 项目展示 (人类阅读)
├── ARCHITECTURE.md                 # 本文档 (AI Agent 阅读)
│
├── backend/
│   ├── Dockerfile                  # python:3.11-slim, uvicorn 启动
│   ├── requirements.txt            # fastapi, uvicorn, duckdb, pandas, openpyxl, pyarrow, playwright, bcrypt, pyjwt, python-multipart
│   ├── .env.example                # DEEPSEEK_API_KEY, JWT_SECRET, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL, MAX_FILE_SIZE_MB, DATA_RETENTION_DAYS
│   └── app/
│       ├── main.py                 # FastAPI app 创建, CORS 中间件, 路由注册, startup/shutdown 事件, 全局异常处理
│       ├── config.py               # 所有环境变量读取 (os.getenv), 默认值定义
│       ├── database.py             # SQLite 连接管理 + init_db() 建表语句
│       ├── ai/
│       │   ├── base.py             # BaseLLMClient 抽象类: chat(messages, temp, max_tokens) → str, chat_stream() 生成器
│       │   └── deepseek_client.py  # DeepSeekClient(BaseLLMClient): 实现所有 AI 能力
│       │                           #   - chat() 基础对话
│       │                           #   - nl_to_sql(table_schema, question) → str
│       │                           #   - explain_sql(sql) → str
│       │                           #   - explain_query_result(sql, result_summary, question) → str
│       │                           #   - recommend_charts(profile, hint) → list[dict]
│       │                           #   - chat_about_data(data_context, message, history) → str
│       │                           #   每个方法: 检查 API key → 加载 prompt 模板 → 调用 self.chat() → 解析 JSON
│       ├── prompts/
│       │   ├── manager.py          # prompt(name, **kwargs) → str | (str, str)
│       │   │                       #   缓存机制: 首次加载后存入 _cache dict
│       │   │                       #   --- 分隔线: 上方 system, 下方 user; 无分隔线: 单变量接收
│       │   ├── clean.txt           # 数据清洗: system="只输出JSON数组" user=画像+操作列表+示例
│       │   ├── chart.txt           # 图表推荐: system="只输出JSON数组" user=6维画像数据+规则
│       │   ├── sql.txt             # NL→SQL: system="只输出SQL" user=表结构+问题
│       │   ├── explain_sql.txt     # 解释SQL: 单消息, 无system
│       │   ├── explain_result.txt  # 解释结果: 单消息, 问题+SQL+结果摘要
│       │   ├── chat.txt            # 对话: system=数据分析助手角色+能力+规则
│       │   ├── report.txt          # 报告生成: system="只输出JSON" user=画像+输出格式
│       │   └── insight.txt         # 洞察提取: system="只输出JSON数组" user=摘要
│       ├── api/
│       │   ├── router.py           # 汇总所有子路由到 api_router
│       │   ├── auth.py             # POST /register, /login, GET /me
│       │   ├── datasets.py         # POST /upload, GET /, GET /{id}, GET /{id}/preview, GET /{id}/export, DELETE /{id}
│       │   ├── cleaning.py         # POST /{id}/analyze, /{id}/execute, /{id}/ai-execute, /{id}/undo
│       │   ├── query.py            # POST /execute (body: sql或nl+dataset_id)
│       │   ├── charts.py           # POST /recommend, POST /data
│       │   ├── chat.py             # POST / (body: dataset_id, message, history)
│       │   ├── agent.py            # POST /run (body: dataset_id), GET /result/{task_id}
│       │   ├── reports.py          # POST /generate, GET /, GET /{id}, DELETE /{id}, GET /{id}/export
│       │   ├── tasks.py            # GET /{task_id}, GET / (list by user)
│       │   ├── history.py          # GET / (query: type, limit)
│       │   ├── dashboard.py        # GET /stats
│       │   ├── versions.py         # GET /{dataset_id}, POST /snapshot/{id}, POST /rollback, GET /diff/{id}
│       │   ├── metadata.py         # GET /{dataset_id}, PUT / (body), DELETE /{dataset_id}/{col}
│       │   └── lineage.py          # GET /{dataset_id}/chain, GET /{dataset_id}/graph
│       ├── service/
│       │   ├── dataset_service.py  # DatasetService(FileStore, duckdb_dir)
│       │   │                       #   ingest(filename, content, user_id) → DatasetInfo
│       │   │                       #   preview(dataset_id, page, page_size) → {columns, rows, total_rows}
│       │   │                       #   get_info(dataset_id) → dict | None
│       │   │                       #   list_all(user_id, is_admin) → list[dict]
│       │   │                       #   delete(dataset_id)
│       │   │                       #   is_owner(dataset_id, user_id) → bool
│       │   ├── cleaning_service.py # CleaningService(db_path, table_name="data")
│       │   │                       #   scan() → list[CleaningIssue]  规则扫描(重复/空值/空格/类型/异常值)
│       │   │                       #   ai_analyze() → {suggestions, profile_summary, total_rows, total_columns}
│       │   │                       #   ai_execute(operations) → CleanResult  9种操作Python实现
│       │   │                       #   execute(actions, fill_strategy) → CleanResult  手动模式
│       │   │                       #   undo() → bool  从内存备份恢复 (已废弃,改用VersionService)
│       │   │                       #   _build_profile() → dict  构建数据画像供AI分析
│       │   ├── chart_service.py    # ChartService(duckdb_dir)
│       │   │                       #   recommend(dataset_id, hint) → list[ChartItem]
│       │   │                       #   _profile_data(mgr) → dict  6维画像:
│       │   │                       #     {total_rows, columns, numeric_columns, categorical_columns,
│       │   │                       #      date_columns, column_stats, assessment, sample_rows,
│       │   │                       #      aggregations, time_series, histograms, scatter_data,
│       │   │                       #      scatter_notes, correlations, extremes}
│       │   ├── agent_service.py    # AgentService
│       │   │                       #   run_pipeline(task_id, user_id, dataset_id) → async 6步:
│       │   │                       #     ①数据画像(10%) ②AI清洗(25%) ③图表推荐(40%)
│       │   │                       #     ④洞察提取(55-70%) ⑤报告生成(80-95%) ⑥聚合输出(100%)
│       │   │                       #   每步更新 TaskService + HistoryService + LineageService
│       │   ├── report_service.py   # ReportService(duckdb_dir)
│       │   │                       #   generate(user_id, dataset_id, dataset_name, profile) → dict
│       │   │                       #   get_report(report_id) → dict | None
│       │   │                       #   list_by_user(user_id) → list[dict]
│       │   │                       #   list_all() → list[dict]
│       │   │                       #   delete(report_id)
│       │   │                       #   报告存两份: reports/{id}.json + SQLite reports表
│       │   ├── version_service.py  # VersionService
│       │   │                       #   create(dataset_id, label, db_path) → dict | None
│       │   │                       #     先读DuckDB行数→shutil.copy2快照→写SQLite记录
│       │   │                       #   list_versions(dataset_id) → list[dict]
│       │   │                       #   rollback(dataset_id, version_id) → bool  文件替换
│       │   │                       #   diff(dataset_id, v1_id, v2_id) → dict  行数/列数对比
│       │   │                       #   delete_dataset(dataset_id)  清理所有快照
│       │   ├── task_service.py     # TaskService
│       │   │                       #   create(user_id, type, input_data) → dict
│       │   │                       #   update(task_id, status, progress, output, error)
│       │   │                       #   get(task_id) → dict
│       │   │                       #   list_by_user(user_id, limit) → list[dict]
│       │   │                       #   delete(task_id)
│       │   ├── history_service.py  # HistoryService
│       │   │                       #   log(user_id, type, detail, dataset_id)  所有操作点调用
│       │   │                       #   list_by_user(user_id, type, limit) → list[dict]
│       │   ├── lineage_service.py  # LineageService
│       │   │                       #   log(user_id, dataset_id, task_id, operation, target, summary,
│       │   │                       #       before_snapshot, after_snapshot)  try/except pass (非关键)
│       │   │                       #   get_chain(dataset_id) → list[dict]
│       │   │                       #   get_graph(dataset_id) → {nodes, edges}
│       │   │                       #   _ensure_table()  独立建表, 不依赖 init_db()
│       │   └── metadata_service.py # MetadataService
│       │                           #   save(dataset_id, column_name, label, unit, description)
│       │                           #   get(dataset_id) → {col: {label, unit, description}}
│       │                           #   build_context(dataset_id, col) → str  列级上下文
│       │                           #   build_all_hints(dataset_id) → str  所有列的提示字符串
│       ├── data/
│       │   ├── duckdb_manager.py   # DuckDBManager(db_path)
│       │   │                       #   create_table(df, table_name)  Pandas→DuckDB
│       │   │                       #   query(sql, limit) → list[dict]  安全检查: 拦截 INSERT/UPDATE/DELETE/DROP/ALTER/CREATE/PURGE/CHECKPOINT
│       │   │                       #   preview(table, page, page_size) → (rows, total)
│       │   │                       #   get_columns(table) → list[str]
│       │   │                       #   get_table_info(table) → list[dict]  列名/dtype/空值/样本
│       │   │                       #   overwrite_table(df, table)  先DROP后CREATE
│       │   │                       #   close()  关闭连接
│       │   └── file_store.py       # FileStore(base_dir)
│       │                           #   save(dataset_id, filename, content)  存到 uploads/{id}/filename
│       │                           #   get_path(dataset_id) → Path
│       │                           #   delete(dataset_id)  shutil.rmtree
│       │                           #   cleanup(retention_days)  删除过期文件
│       ├── middleware/
│       │   └── auth.py             # get_current_user: Header→JWT decode→查SQLite users表→返回dict
│       │                           # get_current_user_id: 同上但只返回 user_id 字符串
│       │                           # DEFAULT_USER_ID: 未登录时的默认用户
│       ├── model/
│       │   ├── dataset.py          # DatasetInfo(id, name, rows, columns, fields, created_at)
│       │   │                       # ColumnInfo(name, dtype, null_count, sample_values)
│       │   ├── cleaning.py         # CleaningIssue(type, column, count, sample, severity)
│       │   │                       # CleanResult(rows_before, rows_after, changes, can_undo)
│       │   │                       # CleanRequest(actions, fill_strategy)
│       │   └── chart.py            # ChartItem(title, chart_type, reason, echarts_option, data_query)
│       └── utils/
│           ├── file_parser.py      # parse_file(path) → DataFrame
│           │                       #   编码检测: UTF-8→GBK→GB2312→Latin-1
│           │                       #   CSV: pandas.read_csv(x10编码重试)
│           │                       #   Excel: pandas.read_excel(支持.xls/.xlsx)
│           │                       #   ParseError 自定义异常
│           └── response.py         # success(data, message) → {code:0, data, message}
│                                   # error(code, message) → {code, message}
│
├── frontend/
│   ├── Dockerfile                  # node:20-alpine build + nginx:alpine serve
│   ├── nginx.conf                  # /api/* → proxy_pass backend:8000, /* → /usr/share/nginx/html
│   ├── package.json                # vue 3.5, element-plus 2.9, echarts 5.6, pinia 2.3, vue-router 4.5, marked 15, mitt 3
│   ├── .env                        # VITE_API_BASE_URL=http://localhost:8000/api
│   ├── .env.production             # VITE_API_BASE_URL=/api
│   ├── index.html
│   └── src/
│       ├── main.ts                 # createApp, use(pinia), use(router), use(ElementPlus), mount
│       ├── App.vue                  # 顶部导航栏(login页隐藏) + router-view, 全局CSS变量+ElementPlus覆写
│       ├── router/
│       │   └── index.ts            # 8条路由: /login(guest) /(dashboard) /datasets/:id /upload /history /reports /reports/:id /users
│       │                           # beforeEach: 无token→/login, 有token且/login→/
│       ├── api/
│       │   ├── client.ts           # axios.create(baseURL=VITE_API_BASE_URL, timeout=30s)
│       │   │                       # request拦截器: 自动加 Bearer token
│       │   │                       # response拦截器: code!==0→ElMessage.error, code===0→return data.data
│       │   ├── auth.ts             # login, register, getMe
│       │   ├── datasets.ts         # uploadDataset, getDatasets, getDataset, deleteDataset, previewDataset, getExportUrl
│       │   ├── cleaning.ts         # aiAnalyze, aiExecute, undoCleaning
│       │   ├── charts.ts           # recommendCharts, fetchChartData
│       │   ├── query.ts            # executeQuery(datasetId, sql?, nl?)
│       │   ├── chat.ts             # sendMessage(datasetId, message, history?)
│       │   ├── agent.ts            # runAgent(datasetId) → {task_id}
│       │   ├── reports.ts          # generateReport, getReports, getReport, deleteReport
│       │   ├── tasks.ts            # getTask(taskId)
│       │   ├── history.ts          # getHistory(type?)
│       │   ├── dashboard.ts        # getDashboardStats
│       │   ├── versions.ts         # listVersions, rollbackVersion, createSnapshot
│       │   ├── metadata.ts         # getMetadata, saveMetadata, deleteColumnMeta
│       │   └── lineage.ts          # 存在但前端未使用
│       ├── views/
│       │   ├── Login.vue           # 登录/注册切换, username+password+submit, 全屏无导航
│       │   ├── Dashboard.vue       # 数据集卡片网格, 统计摘要, 最近活动, 空状态, 删除确认
│       │   ├── Upload.vue          # el-upload拖拽, CSV/Excel, 上传后显示结果+跳转按钮
│       │   ├── DatasetDetail.vue   # 核心页面 (约420行)
│       │   │                       #   5个Tab: 预览/清洗/图表/SQL/AI对话
│       │   │                       #   顶部按钮: 一键分析/生成报告/导出CSV
│       │   │                       #   监听 bus 事件: dataset:cleaned, dataset:undo
│       │   │                       #   Ctrl+Z 快捷键撤销清洗
│       │   │                       #   图表导出: 逐个下载/合并下载
│       │   │                       #   导入: useDatasetStore, useCleaningStore, useChartStore, bus
│       │   ├── Reports.vue         # 报告卡片列表, 删除确认, loading/empty状态
│       │   ├── ReportDetail.vue    # 报告展示: 文字+内嵌ChartPanel, 导出PDF按钮
│       │   ├── History.vue         # 操作日志时间线, 类型下拉筛选, loading/empty状态
│       │   └── Users.vue           # 用户管理 (admin only)
│       ├── components/
│       │   ├── DataTable.vue       # el-table + el-pagination, props: columns/rows/total/page/loading
│       │   │                       #   空状态: el-empty 插槽
│       │   ├── ChartPanel.vue      # ECharts 封装, props: echartsOption
│       │   │                       #   渲染前注入默认9色调色板, 悬停显示导出按钮
│       │   │                       #   onUnmounted 中 dispose() 防内存泄漏
│       │   │                       #   expose: exportPng(), getDataUrl()
│       │   ├── CleaningPanel.vue   # AI清洗面板 (独立组件, 崩溃不影响页面)
│       │   │                       #   按钮: AI分析→建议卡片列表(checkbox) → 执行选中/撤销
│       │   │                       #   建议卡片4层信息: 标题+严重度 / 字段+行数% / 描述 / 修复预览
│       │   ├── TaskProgress.vue    # 异步任务进度弹窗, props: taskId/modelValue
│       │   │                       #   每2秒轮询 getTask(), pending→running→done/failed
│       │   │                       #   后台运行可关闭弹窗, 完成后ElNotification通知
│       │   └── AiLoading.vue       # AI思考中动画 (点脉冲+文字)
│       ├── stores/
│       │   ├── useAuth.ts          # token+user, login/register/checkAuth/logout
│       │   ├── useDataset.ts       # current DatasetInfo, load/clear
│       │   ├── useCleaning.ts      # suggestions[], selectedFixIndexes[], totalRows
│       │   │                       # analyze/execute/undo, canUndo, cleanResult
│       │   ├── useChart.ts         # charts[], loading, load(datasetId, fields?)
│       │   │                       #   load() 内部: 推荐→补data_query→fetchChartData→填充echarts_option
│       │   └── eventBus.ts         # mitt 实例, 'dataset:cleaned' / 'dataset:undo' 事件
│       ├── composables/
│       │   └── useChart.ts         # ECharts 生命周期封装 (已废弃, 前端不再使用)
│       └── utils/
│           └── format.ts           # formatDate() 日期格式化
│
└── duckdb_data/                    # DuckDB 数据文件 (运行时生成)
    ├── {dataset_id}.duckdb         # 每个数据集一个文件, 表名固定 data
    └── versions/{dataset_id}/      # 版本快照 v{n}.duckdb
```

## 四、数据流详解

### 4.1 上传流程

```
前端 Upload.vue
  → el-upload @change → uploadDataset(file.raw)
  → POST /api/datasets/upload (multipart/form-data)
  → datasets.py: upload()
    → file_store.save(dataset_id, filename, content)     # 存原始文件
    → parse_file(file_path)                               # 编码检测+Pandas解析
    → DuckDBManager.create_table(df, "data")              # Pandas→DuckDB
    → INSERT dataset_owners (dataset_id, user_id, filename)
    → hist_svc.log(upload)
    → return DatasetInfo(id, name, rows, columns, fields)
```

### 4.2 AI 清洗流程

```
前端 CleaningPanel.vue
  ① 点击 "AI 分析数据质量"
  → POST /api/cleaning/{id}/analyze
  → CleaningService.ai_analyze()
    → _build_profile() → {total_rows, columns, column_stats, sample_rows}
    → json.dumps(profile)
    → prompt("clean", profile_json=...) → sys_msg, user_msg
    → DeepSeekClient.chat([sys, user]) → JSON suggestions
    → return {suggestions, profile_summary, total_rows, total_columns}
  → 前端渲染建议卡片: title/severity/affected_columns/行数占比/description/fix预览

  ② 用户勾选要修复的项 → 点击 "执行选中修复"
  → POST /api/cleaning/{id}/ai-execute (operations: [{operation, params}])
  → cleaning.py: ai_execute()
    → VersionService.create(dataset_id, "AI清洗前快照")  # shutil.copy2 文件快照
    → CleaningService.ai_execute(operations)
      → DuckDBManager.query("SELECT * FROM data") → Pandas DataFrame
      → 遍历operations, 每个operation是预定义的Python操作:
        clean_currency: str.replace(prefix, "") → pd.to_numeric()
        extract_number: str.replace(unit, "") → pd.to_numeric()
        normalize_case: str.upper()/lower()/title()
        drop_column: df.drop(columns=[col])
        rename_column: df.rename(columns={old: new})
        drop_outliers: df.loc[mask, col]=None
        deduplicate: df.drop_duplicates()
        trim_strings: str.strip()
        fill_nulls: fillna(mean/median/mode) 或 dropna()
      → DuckDBManager.overwrite_table(df, "data")  # DROP+CREATE
      → return CleanResult(rows_before, rows_after, changes, can_undo=True)
    → hist_svc.log(clean) + lineage_svc.log(clean)
    → return {changes, rows_before, rows_after, can_undo}

  ③ 如需撤销
  → cleaningStore.undo() → POST /api/cleaning/{id}/undo
  → cleaning.py: undo()
    → VersionService.list_versions() → 取最新版本
    → VersionService.rollback(dataset_id, latest_version_id)
      → shutil.copy2(version_file, current_file)  # 文件级回滚
    → 前端 bus.emit('dataset:undo') → DatasetDetail 刷新预览
```

### 4.3 图表推荐流程

```
前端 DatasetDetail.vue Tab3
  → 点击 "AI 推荐图表"
  → chartStore.load(datasetId, fields)
    → POST /api/charts/recommend (body: {dataset_id, hint})
    → ChartService.recommend()
      → DuckDBManager.get_table_info() + 多维度SQL查询
      → _profile_data() 构建6维画像:
        ① 列统计 (numeric: min/max/avg/std/unique/null; categorical: unique/top_values)
        ② 数据质量评估 (单值列/常量列/空值)
        ③ 聚合数据 (GROUP BY 分类列, 限50组)
        ④ 时序数据 (日期列×数值列, 限200点)
        ⑤ 直方图 (bucket=N^(0.3), 5-12个桶)
        ⑥ 散点数据 (前5数值列两两配对, 采样500点)
        ⑦ 相关性矩阵 (所有数值列对CORR)
        ⑧ 极值 (top5/bottom5)
      → DeepSeekClient.recommend_charts(profile)
        → prompt("chart", total_rows, numeric_cols, stats_desc, ...)
        → AI 返回 [{title, chart_type, reason, data_query, echarts_option}]
    → 对每个chart, 如果有data_query, fetchChartData() 获取真实数据填充echarts_option
    → 前端 ChartPanel 渲染 ECharts (注入9色默认色板防黑屏)

  图表导出:
  → 逐个下载: ChartPanel.exportPng() → getDataURL → a.click()
  → 合并下载: 遍历ChartPanel.getDataUrl() → canvas绘制 → a.click()
```

### 4.4 NL→SQL 查询流程

```
前端 DatasetDetail.vue Tab4
  → 自然语言模式: 输入问题 → 回车
  → POST /api/query/execute (body: {dataset_id, nl: "统计各品牌均价"})
  → query.py: execute_query()
    → DuckDBManager.get_table_info() 获取列信息
    → DeepSeekClient.nl_to_sql(table_schema, question)
      → prompt("sql", table_schema, question) → sys_msg, user_msg
      → AI 返回纯 SQL 字符串 (或 "CANNOT_GENERATE")
    → 如果是 CANNOT_GENERATE → 返回 error
    → DuckDBManager.query(sql, limit=1000)  # 安全检查后执行
    → DeepSeekClient.explain_query_result(sql, result_summary, question)
      → prompt("explain_result", ...) → 1-3句中文解读
    → 前端展示: 执行SQL + AI解读 + DataTable结果
```

### 4.5 Agent 一键分析流程

```
前端 DatasetDetail.vue
  → 点击 "一键分析"
  → POST /api/agent/run (body: {dataset_id})
  → agent.py: run_agent()
    → TaskService.create(user_id, "agent_pipeline", {dataset_id}) → task
    → threading.Thread(target=_run_pipeline_in_thread, daemon=True).start()
    → 立即返回 {task_id}
  → 前端 TaskProgress 每2秒轮询 GET /api/agent/result/{task_id}

  后台线程 _run_pipeline_in_thread():
    loop = asyncio.new_event_loop()
    ① 数据画像 (10%): ChartService._profile_data() → 总行数/列数
    ② AI清洗 (25%): CleaningService.ai_analyze() → ai_execute()
    ③ 图表推荐 (40-55%): ChartService.recommend()
    ④ 洞察提取 (55-70%): 调用 _extract_insights()
       → prompt("insight", summary) → AI 返回 3-5个洞察字符串
    ⑤ 报告生成 (80-95%): ReportService.generate()
       → prompt("report", summary) → JSON报告 → 存文件+SQLite
    ⑥ 聚合输出 (100%): TaskService.update(done, output=result)
    每步更新: TaskService进度 + HistoryService记录 + LineageService记录
    异常处理: try/except → TaskService.update(failed, error=str(e))

  前端 TaskProgress 检测到 done → emit('done', output)
  → DatasetDetail.onAgentDone() → router.push(/reports/{report_id})
```

### 4.6 报告与 PDF 导出

```
报告生成 (手动):
  POST /api/reports/generate?dataset_id=xxx
  → reports.py: generate()
    → ChartService._profile_data() → 画像
    → ReportService.generate()
      → prompt("report", summary) → sys_msg, user_msg
      → AI 返回 JSON {title, sections: [{type:text/chart, ...}]}
      → 验证: JSON parse 失败时返回错误报告
      → 存两份: reports/{id}.json + SQLite reports表

PDF 导出:
  GET /api/reports/{id}/export
  → reports.py: export_pdf()
    → _render_report_html(report)
      → 遍历 sections: text→<h3>+<p>, chart→<div id="chartN"> + ECharts init 脚本
      → 内联 CDN: echarts@5.6.0
      → 注入默认9色调色板到每个图表
      → 完整HTML: <!DOCTYPE>+echarts CDN+CSS+chart divs+script
    → _html_to_pdf(html)
      → tempfile 写HTML文件
      → async_playwright().chromium.launch()
      → page.goto(file:///..., wait_until="networkidle")
      → page.wait_for_timeout(2000)  # 等ECharts渲染
      → page.pdf(format="A4", margin=...)
      → os.unlink(temp file)
      → return Response(pdf, media_type="application/pdf")
```

## 五、数据库 Schema

### SQLite (data.db)

```sql
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT DEFAULT 'user',       -- 'admin' | 'user'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS dataset_owners (
    dataset_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    filename TEXT NOT NULL,
    PRIMARY KEY (dataset_id, user_id)
);

CREATE TABLE IF NOT EXISTS dataset_versions (
    id TEXT PRIMARY KEY,
    dataset_id TEXT NOT NULL,
    version INTEGER NOT NULL,
    label TEXT DEFAULT '',
    row_count INTEGER DEFAULT 0,
    column_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS reports (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    dataset_id TEXT,
    title TEXT NOT NULL,
    file_path TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS task_queue (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    type TEXT NOT NULL,             -- 'agent_pipeline' | ...
    status TEXT DEFAULT 'pending',  -- 'pending'|'running'|'done'|'failed'
    progress INTEGER DEFAULT 0,
    input TEXT,                     -- JSON
    output TEXT,                    -- JSON
    error TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    finished_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS history_log (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    type TEXT NOT NULL,             -- 'upload'|'clean'|'query'|'chart'|'report'|'delete'|'agent'
    detail TEXT NOT NULL,
    dataset_id TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS data_lineage (
    id TEXT PRIMARY KEY,
    task_id TEXT,
    user_id TEXT NOT NULL,
    dataset_id TEXT NOT NULL,
    operation TEXT NOT NULL,
    target TEXT NOT NULL,
    summary TEXT NOT NULL,
    before_snapshot TEXT,           -- JSON
    after_snapshot TEXT,            -- JSON
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS column_metadata (
    dataset_id TEXT NOT NULL,
    column_name TEXT NOT NULL,
    label TEXT DEFAULT '',
    unit TEXT DEFAULT '',
    description TEXT DEFAULT '',
    PRIMARY KEY (dataset_id, column_name)
);
```

### DuckDB (duckdb_data/{dataset_id}.duckdb)

每个数据集一个独立文件，表名固定 `data`。表结构由上传的 CSV/Excel 决定。
`get_table_name()` 通过 `SELECT table_name FROM information_schema.tables WHERE table_name='data'` 检测。

## 六、所有 API 端点签名

### 统一响应格式

```json
{"code": 0, "data": {...}, "message": "ok"}
{"code": 400, "data": null, "message": "错误描述"}
```

### 端点列表

| 方法 | 路径 | 请求体 | 响应 data | 说明 |
|------|------|--------|-----------|------|
| POST | /api/auth/register | {username, password} | {token, user} | 注册+自动登录 |
| POST | /api/auth/login | {username, password} | {token, user} | 登录 |
| GET | /api/auth/me | — | user dict | 当前用户信息 |
| POST | /api/datasets/upload | FormData(file) | DatasetInfo | 上传CSV/Excel |
| GET | /api/datasets | — | [DatasetInfo] | 数据集列表(按权限) |
| GET | /api/datasets/{id} | — | DatasetInfo | 单个信息 |
| GET | /api/datasets/{id}/preview | ?page&page_size | {columns, rows, total_rows} | 分页预览 |
| GET | /api/datasets/{id}/export | — | File download | CSV导出 |
| DELETE | /api/datasets/{id} | — | message | 删除+清理 |
| POST | /api/cleaning/{id}/analyze | — | {suggestions, total_rows, ...} | AI分析 |
| POST | /api/cleaning/{id}/execute | {actions[], fill_strategy} | CleanResult | 规则清洗 |
| POST | /api/cleaning/{id}/ai-execute | {operations[{operation,params}]} | CleanResult | AI清洗执行 |
| POST | /api/cleaning/{id}/undo | — | message | 回滚到最新版本 |
| POST | /api/query/execute | {dataset_id, sql?, nl?} | {columns, rows, executed_sql, ai_explanation} | SQL/NL查询 |
| POST | /api/charts/recommend | {dataset_id, hint?} | {charts: [ChartItem]} | AI图表推荐 |
| POST | /api/charts/data | {dataset_id, data_query} | {data/categories/values} | 图表数据查询 |
| POST | /api/chat | {dataset_id, message, history?} | {answer, query_result?} | AI对话 |
| POST | /api/agent/run | {dataset_id} | {task_id} | 启动一键分析 |
| GET | /api/agent/result/{task_id} | — | task dict | 查询任务状态 |
| POST | /api/reports/generate | ?dataset_id | report dict | 生成报告 |
| GET | /api/reports | — | [report] | 报告列表 |
| GET | /api/reports/{id} | — | report dict | 报告详情 |
| DELETE | /api/reports/{id} | — | message | 删除报告 |
| GET | /api/reports/{id}/export | — | PDF binary | 导出PDF |
| GET | /api/tasks/{task_id} | — | task dict | 任务状态 |
| GET | /api/tasks | — | [task] | 用户任务列表 |
| GET | /api/history | ?type&limit | [log] | 操作历史 |
| GET | /api/dashboard/stats | — | {reports_count, operations_count, recent_activities} | 仪表盘统计 |
| GET | /api/versions/{dataset_id} | — | [version] | 版本列表 |
| POST | /api/versions/snapshot/{id} | — | version dict | 手动快照 |
| POST | /api/versions/rollback | {dataset_id, version_id} | message | 回滚 |
| GET | /api/versions/diff/{id} | ?v1&v2 | diff dict | 版本对比 |
| GET | /api/metadata/{dataset_id} | — | {col: {label, unit, desc}} | 列元数据 |
| PUT | /api/metadata | {dataset_id, column_name, label, unit, desc} | message | 保存元数据 |
| DELETE | /api/metadata/{id}/{col} | — | message | 删除列元数据 |
| GET | /api/lineage/{id}/chain | — | [lineage] | 血缘链 |
| GET | /api/lineage/{id}/graph | — | {nodes, edges} | 血缘图 |
| GET | /api/health | — | {status:"ok"} | 健康检查 |

## 七、关键约定与避坑

### 7.1 后端约定

- **所有 INSERT 显式写 `created_at`**: 用 `datetime.now().isoformat()`，不依赖 SQLite DEFAULT
- **新增 SQLite 表**: 在 `database.py:init_db()` 加 `CREATE TABLE IF NOT EXISTS`，同时在对应 Service 写 `_ensure_table()` 兜底
- **异步后台任务**: 用 `threading.Thread(daemon=True)` + `asyncio.new_event_loop()`。禁止 `BackgroundTasks.add_task()`（不支持 async）
- **AI 调用必须 try/except**: API 可能超时/余额不足/限流，业务代码不能因 AI 不可用而崩溃
- **Prompt 调用**: 先看 `.txt` 有没有 `---`，有→tuple解包(sys_msg, user_msg)，没有→单变量接收
- **DuckDB 操作前检查文件存在**: `os.path.exists(db_path)` 先判断，返回 404 而非 500
- **非关键功能 silent fail**: lineage、metadata 写入失败不抛异常，`try/except: pass`
- **DuckDB Windows 文件锁**: 先读数据→`mgr.close()`→再 `shutil.copy2()`，不能在连接打开时复制文件
- **Route 文件保持薄**: 只做参数校验 + 调 service + 调 hist_svc.log()。业务逻辑全在 service 层

### 7.2 前端约定

- **禁止顶级 `v-loading`**: 每个功能块自己管理 loading ref
- **Event Bus 跨组件通信**: `bus.emit()` / `bus.on()`，不在 A 组件里调 B 组件方法
- **ECharts 必须 dispose**: `onUnmounted(() => { chart?.dispose(); chart = null })`
- **ECharts 渲染前设默认色板**: `chart.setOption({ color: [9色] }, false)` 防饼图全黑
- **图表导出用 `a.click()`**: 不需要 `appendChild` 到 body
- **ElMessage 只在 client.ts 的 axios 拦截器使用**: 页面组件通过 try/catch + el-alert ref 处理错误反馈
- **模板安全访问**: `v-for` 里访问嵌套对象提供 `getXxx(key)` 安全访问函数返回默认值
- **Tab pane name 必须唯一**: 删旧版再加新版，防止重复 name 导致渲染错乱
- **Pinia Store 按功能拆分**: 一个 store 只做一件事，不在 store A 里 import store B

### 7.3 Docker 部署

- Nginx 配置: `/api/*` → `proxy_pass http://backend:8000/api/`, `/*` → 静态文件
- 4 个 Docker volumes: uploads_data, duckdb_data, sqlite_data, reports_data
- 环境变量通过 docker-compose.yml 的 `environment` 注入

## 八、AI Client 接口

```python
class BaseLLMClient(ABC):
    @abstractmethod
    async def chat(self, messages: list[dict], temperature: float = 0.7,
                   max_tokens: int = 4096) -> str: ...

    async def chat_stream(self, messages, temperature=0.7, max_tokens=4096):
        text = await self.chat(messages, temperature, max_tokens)
        yield text  # 默认回退，子类可覆盖实现 SSE

class DeepSeekClient(BaseLLMClient):
    # 配置: DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL
    # 内部: OpenAI SDK client = AsyncOpenAI(api_key, base_url)
    # chat(): client.chat.completions.create(model, messages, temperature, max_tokens)
    # 所有公开方法: nl_to_sql, explain_sql, explain_query_result, recommend_charts, chat_about_data
    # 公开方法模式: 检查_is_configured() → 加载prompt → 调用self.chat() → 解析JSON
```
