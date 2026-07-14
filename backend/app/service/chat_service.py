import os
import json
from app.data.duckdb_manager import DuckDBManager
from app.ai.deepseek_client import DeepSeekClient
from app.model.chat import ChatResponse, QueryResultData

class ChatService:
    def __init__(self, duckdb_dir: str):
        self.duckdb_dir = duckdb_dir
        self.ai = DeepSeekClient()

    async def chat(self, dataset_id: str, message: str,
                   history: list[dict] | None = None) -> ChatResponse:
        db_path = os.path.join(self.duckdb_dir, f"{dataset_id}.duckdb")
        mgr = DuckDBManager(db_path)
        context = self._build_data_context(mgr)

        answer = await self.ai.chat_about_data(context, message, history)

        # Extract and execute SQL from the response
        sql_generated = None
        query_result = None

        if "```sql" in answer:
            parts = answer.split("```sql")
            if len(parts) > 1:
                sql_block = parts[1].split("```")[0].strip()
                if sql_block and any(kw in sql_block.upper() for kw in ["SELECT"]):
                    sql_generated = sql_block
                    # Auto-execute the SQL
                    try:
                        # First get the real total count
                        clean_sql = sql_block.strip().rstrip(";")
                        count_sql = f"SELECT COUNT(*) AS _total FROM ({clean_sql}) AS _count_sub"
                        total = mgr.query(count_sql)[0]["_total"]

                        # Then fetch rows (up to 500 for display)
                        rows = mgr.query(sql_block, limit=500)
                        cols = list(rows[0].keys()) if rows else []
                        query_result = QueryResultData(
                            columns=cols,
                            rows=rows,
                            total_rows=total,
                            executed_sql=sql_block,
                        )
                    except Exception as e:
                        query_result = QueryResultData(
                            columns=[], rows=[],
                            total_rows=0, executed_sql=sql_block,
                            error=str(e),
                        )

        return ChatResponse(
            answer=answer,
            sql_generated=sql_generated,
            query_result=query_result,
        )

    def _build_data_context(self, mgr: DuckDBManager) -> str:
        table_info = mgr.get_table_info("data")
        columns = mgr.get_columns("data")
        total_rows = mgr.query("SELECT COUNT(*) AS cnt FROM data")[0]["cnt"]

        parts = [f"数据集共 {total_rows} 行, {len(columns)} 列。\n"]
        parts.append("## 列统计")
        for info in table_info:
            col = info["column_name"]
            dtype = info["dtype"]
            null_count = info["null_count"]
            samples = info.get("sample_values", [])[:5]
            is_numeric = any(t in dtype.upper() for t in ["INT", "FLOAT", "DOUBLE", "BIGINT", "DECIMAL"])
            quoted = f'"{col}"'

            line = f"- {col} ({dtype})"
            if null_count > 0:
                line += f", 空值{null_count}个"
            if is_numeric:
                stats = mgr.query(f"SELECT MIN({quoted}) AS mn, MAX({quoted}) AS mx, ROUND(AVG({quoted}), 2) AS av FROM data")
                if stats:
                    s = stats[0]
                    line += f", 范围[{s['mn']}, {s['mx']}], 均值{s['av']}"
            else:
                unique = mgr.query(f"SELECT COUNT(DISTINCT {quoted}) AS cnt FROM data")[0]["cnt"]
                line += f", {unique}个不同值"
                if unique <= 10:
                    top = mgr.query(f"SELECT {quoted} AS v, COUNT(*) AS c FROM data GROUP BY {quoted} ORDER BY c DESC")
                    dist = ", ".join([f'{r["v"]}:{r["c"]}行' for r in top])
                    line += f", 分布: {dist}"
            if samples:
                line += f", 样例: {samples}"
            parts.append(line)

        sample = mgr.query("SELECT * FROM data LIMIT 5")
        parts.append(f"\n## 样本行\n{json.dumps(sample, ensure_ascii=False, default=str)}")
        return "\n".join(parts)
