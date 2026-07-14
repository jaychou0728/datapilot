import json
import httpx
from app.config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL

class DeepSeekClient:
    def __init__(self):
        self.api_key = DEEPSEEK_API_KEY
        self.base_url = DEEPSEEK_BASE_URL
        self.timeout = 30.0

    def _is_configured(self) -> bool:
        return bool(self.api_key)

    async def chat(self, messages: list[dict], temperature: float = 0.7, max_tokens: int = 4096) -> str:
        if not self._is_configured():
            return "AI 服务未配置，请在 .env 中设置 DEEPSEEK_API_KEY"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": "deepseek-chat",
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(
                    f"{self.base_url}/v1/chat/completions",
                    headers=headers, json=payload,
                )
                if resp.status_code == 402:
                    return "AI 服务账户余额不足"
                if resp.status_code == 429:
                    return "请求过于频繁，请稍后再试"
                resp.raise_for_status()
                data = resp.json()
                return data["choices"][0]["message"]["content"]
        except httpx.TimeoutException:
            return "AI 服务响应超时，请重试"
        except httpx.HTTPError as e:
            return f"AI 服务异常: {e}"

    async def generate_sql(self, table_schema: str, question: str) -> str | None:
        if not self._is_configured():
            return None

        prompt = f"""你是一个 SQL 专家。根据以下表结构生成 DuckDB SQL 查询。

表名: data
表结构:
{table_schema}

用户问题: {question}

要求:
- 只返回 SQL 语句，不要任何解释
- 只能生成 SELECT 语句
- 如果用户的问题无法用 SQL 回答，返回: CANNOT_GENERATE

SQL:"""
        response = await self.chat([
            {"role": "system", "content": "你是一个只输出 SQL 语句的助手。"},
            {"role": "user", "content": prompt},
        ], temperature=0.1)

        sql = response.strip()
        if sql.startswith("```sql"):
            sql = sql.split("```sql")[1].split("```")[0].strip()
        elif sql.startswith("```"):
            sql = sql.split("```")[1].split("```")[0].strip()

        if "CANNOT_GENERATE" in sql:
            return None
        sql_upper = sql.upper()
        forbidden = ["INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE", "TRUNCATE"]
        for kw in forbidden:
            if kw in sql_upper:
                return None
        return sql

    async def explain_sql(self, sql: str) -> str:
        if not self._is_configured():
            return ""
        prompt = f"用一句话中文解释这条 SQL 查询的含义:\n{sql}"
        return await self.chat([
            {"role": "user", "content": prompt},
        ], temperature=0.3)

    async def explain_query_result(self, sql: str, result_summary: str, question: str) -> str:
        if not self._is_configured():
            return ""
        prompt = f"""用户问题: {question}
执行的 SQL: {sql}
查询结果摘要: {result_summary}

用 1-3 句话中文解读这个查询结果。"""
        return await self.chat([
            {"role": "user", "content": prompt},
        ], temperature=0.5)

    async def recommend_charts(self, profile: dict, hint: str = "") -> list[dict]:
        if not self._is_configured():
            return []

        total_rows = profile["total_rows"]
        columns = profile["columns"]
        numeric_cols = profile["numeric_columns"]
        col_stats = profile["column_stats"]
        assessment = profile.get("assessment", [])
        aggregations = profile.get("aggregations", {})
        time_series = profile.get("time_series", {})
        histograms = profile.get("histograms", {})
        scatter_data = profile.get("scatter_data", {})
        correlations = profile.get("correlations", [])
        scatter_notes = profile.get("scatter_notes", [])

        stats_desc = []
        for col in columns:
            s = col_stats[col]
            if s["type"] == "numeric":
                stats_desc.append(
                    f'  {col}: 数值, 范围[{s["min"]}, {s["max"]}], 均值{s["avg"]}, '
                    f'标准差{s["std"]}, {s["unique_count"]}个不同值'
                )
            elif s["type"] == "date":
                stats_desc.append(f'  {col}: 日期/时间, {s["unique_count"]}个不同值')
            else:
                top5 = ", ".join([f'{v["value"]}({v["count"]}行)' for v in s["top_values"][:5]])
                stats_desc.append(f'  {col}: 分类, {s["unique_count"]}个不同值, {top5}')

        warnings = "\n".join([f"  ! {a}" for a in assessment]) if assessment else "  无"

        agg_json = json.dumps(aggregations, ensure_ascii=False, default=str)
        ts_json = json.dumps(time_series, ensure_ascii=False, default=str)
        hist_json = json.dumps(histograms, ensure_ascii=False, default=str)
        scatter_json = json.dumps(scatter_data, ensure_ascii=False, default=str)
        corr_json = json.dumps(correlations, ensure_ascii=False, default=str)

        chart_hints = []
        if aggregations:
            chart_hints.append("柱状图/条形图/饼图 -> 用聚合数据(aggregations)")
        if time_series:
            keys = list(time_series.keys())[:3]
            chart_hints.append(f"折线图 -> 用时序数据(time_series), 可用维度: {keys}")
        if scatter_data:
            keys = list(scatter_data.keys())[:3]
            chart_hints.append(f"散点图 -> 用散点数据(scatter_data), 可用维度: {keys}")
        if histograms:
            chart_hints.append("分布直方图 -> 用直方图数据(histograms)")
        if correlations:
            chart_hints.append(f"相关性热力图 -> 用相关性矩阵: {corr_json[:400]}")

        prompt = f"""你是资深数据可视化专家。根据以下完整数据画像，推荐4-6个不同种类的图表，按分析价值从高到低排序。

## 数据概括
{total_rows}行, {len(columns)}列
数值列: {numeric_cols}

### 字段统计
{chr(10).join(stats_desc)}

### 数据问题
{warnings}

### 数据源与图表类型映射
{chr(10).join(chart_hints)}

### 聚合数据 aggregations (柱状图/条形图/饼图)
{agg_json if len(agg_json) < 4000 else agg_json[:4000]}

### 时序数据 time_series (折线图, x轴=_date, y轴=_value)
{ts_json if len(ts_json) < 4000 else ts_json[:4000]}

### 散点数据 scatter_data (散点图, x轴=x, y轴=y, 低基数数据含weight权重)
{scatter_json if len(scatter_json) < 3000 else scatter_json[:3000]}
### 散点数据质量: {scatter_notes if scatter_notes else '正常'}

### 直方图数据 histograms (分布图, x轴=bin_center, y轴=cnt)
{hist_json if len(hist_json) < 2000 else hist_json[:2000]}

## 质量规则
1. echarts_option 里的 series.data / xAxis.data / yAxis.data 全部设为空数组 []，数据由前端从后端加载
2. data_query 告诉前端如何查询数据，包含: type(bar|line|scatter|pie|histogram), x_col, y_col, group_col, agg(AVG|SUM|COUNT|MIN|MAX), limit
3. 数据标签必须显示: label: {{ show: true, position: "top" }}
4. 坐标轴必须包含 name 和单位, nameLocation: "center", nameGap 足够大
5. tooltip 开启, legend 显示
6. 配色: ["#5470c6","#91cc75","#fac858","#ee6666","#73c0de","#3ba272"]
7. xAxis标签太密设 rotate: 30, grid.containLabel: true
8. 标题精确不夸大
9. 至少包含1个柱状图+1个折线图(有时序数据时)+1个散点图(有散点数据时)+1个分布图(有直方图时)
10. 折线图/柱状图用 agg=AVG 或 SUM; 散点图不设 agg; 饼图用 agg=COUNT

### data_query 示例
柱状图: {{"type":"bar","x_col":"手机型号","y_col":"中国售价","agg":"AVG","limit":50}}
散点图: {{"type":"scatter","x_col":"CPU性能得分","y_col":"发布时间","limit":2000}}
折线图: {{"type":"line","x_col":"发布时间","y_col":"CPU性能得分","agg":"AVG","limit":200}}
饼图: {{"type":"pie","group_col":"CPU性能层级","limit":20}}
直方图: {{"type":"histogram","y_col":"CPU性能得分","bins":10}}

只返回JSON数组: [{{"title":"...","chart_type":"bar|line|pie|scatter|heatmap","reason":"...","data_query":{{...}},"echarts_option":{{series:[{{data:[]}}],xAxis:[{{data:[]}}]}}}} ]"""

        response = await self.chat([
            {"role": "system", "content": "你是资深数据可视化专家。只输出合法JSON数组，不输出任何其他内容。"},
            {"role": "user", "content": prompt},
        ], temperature=0.2)

        text = response.strip()
        if text.startswith("```json"):
            text = text.split("```json")[1].split("```")[0].strip()
        elif text.startswith("```"):
            text = text.split("```")[1].split("```")[0].strip()
        try:
            charts = json.loads(text)
            return charts if isinstance(charts, list) else []
        except json.JSONDecodeError:
            return []

    async def chat_about_data(
        self, data_context: str, user_message: str, history: list[dict] | None = None
    ) -> str:
        if not self._is_configured():
            return "AI 服务未配置"

        system_prompt = f"""你是一个数据分析助手，可以访问以下数据画像并执行 SQL 查询。

{data_context}

## 核心能力
当用户提出数据查询需求时（如"查出所有CPU得分大于100的手机"、"统计各品牌平均价格"），你必须：
1. 在回复中用 ```sql ... ``` 格式生成 DuckDB SQL（表名: data）
2. SQL 会被自动执行，查询结果会以表格形式展示给用户
3. 在 SQL 前后用简短文字解释你在做什么、结果意味着什么

## 其他能力
- 基于列统计数据直接回答（范围、均值、分布等）
- 给出数据分析建议
- 结合样本行和统计数据给出洞察

## 规则
- 用中文回复，简洁专业
- 涉及数据查询时，务必生成 SQL，不要只说"可以用SELECT查询"
- SQL 中列名用双引号包裹（如 "CPU性能得分"）"""

        messages = [{"role": "system", "content": system_prompt}]
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": user_message})

        return await self.chat(messages, temperature=0.7)
