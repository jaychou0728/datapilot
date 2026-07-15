"""DeepSeek API client implementing the LLM adapter interface."""
import json
import httpx
from app.config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL
from app.ai.base import BaseLLMClient
from app.prompts.manager import prompt


class DeepSeekClient(BaseLLMClient):
    """DeepSeek API client. Uses OpenAI-compatible /v1/chat/completions endpoint."""

    def __init__(self):
        self.api_key = DEEPSEEK_API_KEY
        self.base_url = DEEPSEEK_BASE_URL
        self.timeout = 30.0

    def _is_configured(self) -> bool:
        return bool(self.api_key)

    # ── BaseLLMClient implementation ──

    async def chat(self, messages: list[dict], temperature: float = 0.7,
                   max_tokens: int = 4096) -> str:
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

    # ── Domain-specific methods ──

    async def generate_sql(self, table_schema: str, question: str) -> str | None:
        if not self._is_configured():
            return None

        sys_msg, user_msg = prompt("sql", table_schema=table_schema, question=question)
        response = await self.chat(
            [{"role": "system", "content": sys_msg},
             {"role": "user", "content": user_msg}],
            temperature=0.1,
        )

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
        user_msg = prompt("explain_sql", sql=sql)
        return await self.chat(
            [{"role": "user", "content": user_msg}],
            temperature=0.3,
        )

    async def explain_query_result(self, sql: str, result_summary: str,
                                    question: str) -> str:
        if not self._is_configured():
            return ""
        user_msg = prompt("explain_result", sql=sql,
                          result_summary=result_summary, question=question)
        return await self.chat(
            [{"role": "user", "content": user_msg}],
            temperature=0.5,
        )

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

        stats_desc = self._build_stats_desc(columns, col_stats)
        warnings = "\n".join([f"  ! {a}" for a in assessment]) if assessment else "  无"
        chart_hints = self._build_chart_hints(aggregations, time_series,
                                               scatter_data, histograms, correlations)

        agg_raw = json.dumps(aggregations, ensure_ascii=False, default=str)
        ts_raw = json.dumps(time_series, ensure_ascii=False, default=str)
        scatter_raw = json.dumps(scatter_data, ensure_ascii=False, default=str)
        hist_raw = json.dumps(histograms, ensure_ascii=False, default=str)
        corr_raw = json.dumps(correlations, ensure_ascii=False, default=str)

        sys_msg, user_msg = prompt("chart",
            total_rows=total_rows, total_columns=len(columns),
            numeric_cols=numeric_cols, stats_desc=chr(10).join(stats_desc),
            warnings=warnings, chart_hints=chr(10).join(chart_hints),
            agg_json_trimmed=agg_raw if len(agg_raw) < 4000 else agg_raw[:4000],
            ts_json_trimmed=ts_raw if len(ts_raw) < 4000 else ts_raw[:4000],
            scatter_json_trimmed=scatter_raw if len(scatter_raw) < 3000 else scatter_raw[:3000],
            scatter_notes=str(scatter_notes) if scatter_notes else '正常',
            hist_json_trimmed=hist_raw if len(hist_raw) < 2000 else hist_raw[:2000],
            corr_json_trimmed=corr_raw if len(corr_raw) < 2000 else corr_raw[:2000],
        )

        response = await self.chat(
            [{"role": "system", "content": sys_msg},
             {"role": "user", "content": user_msg}],
            temperature=0.2,
        )

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

    async def chat_about_data(self, data_context: str, user_message: str,
                               history: list[dict] | None = None) -> str:
        if not self._is_configured():
            return "AI 服务未配置"

        sys_msg = prompt("chat", data_context=data_context)
        if isinstance(sys_msg, tuple):
            sys_msg = sys_msg[0]
        messages = [{"role": "system", "content": sys_msg}]
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": user_message})

        return await self.chat(messages, temperature=0.7)

    # ── Helpers ──

    def _build_stats_desc(self, columns, col_stats):
        lines = []
        for col in columns:
            s = col_stats[col]
            if s["type"] == "numeric":
                lines.append(
                    f'  {col}: 数值, 范围[{s["min"]}, {s["max"]}], '
                    f'均值{s["avg"]}, 标准差{s["std"]}, {s["unique_count"]}个不同值'
                )
            elif s["type"] == "date":
                lines.append(f'  {col}: 日期/时间, {s["unique_count"]}个不同值')
            else:
                top5 = ", ".join([f'{v["value"]}({v["count"]}行)'
                                  for v in s["top_values"][:5]])
                lines.append(f'  {col}: 分类, {s["unique_count"]}个不同值, {top5}')
        return lines

    def _build_chart_hints(self, aggregations, time_series,
                            scatter_data, histograms, correlations):
        hints = []
        if aggregations:
            hints.append("柱状图/条形图/饼图 -> 用聚合数据(aggregations)")
        if time_series:
            keys = list(time_series.keys())[:3]
            hints.append(f"折线图 -> 用时序数据(time_series), 可用维度: {keys}")
        if scatter_data:
            keys = list(scatter_data.keys())[:3]
            hints.append(f"散点图 -> 用散点数据(scatter_data), 可用维度: {keys}")
        if histograms:
            hints.append("分布直方图 -> 用直方图数据(histograms)")
        if correlations:
            hints.append(f"相关性热力图 -> 用相关性矩阵: {json.dumps(correlations)[:400]}")
        return hints
