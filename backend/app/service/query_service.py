import os
import json
import asyncio
from app.data.duckdb_manager import DuckDBManager
from app.ai.deepseek_client import DeepSeekClient
from app.model.query import QueryResult

class QueryService:
    def __init__(self, duckdb_dir: str):
        self.duckdb_dir = duckdb_dir
        self.ai = DeepSeekClient()

    def execute(self, dataset_id: str, sql: str | None = None,
                natural_language: str | None = None) -> QueryResult:
        db_path = os.path.join(self.duckdb_dir, f"{dataset_id}.duckdb")
        if not os.path.exists(db_path):
            raise FileNotFoundError(f"数据集 {dataset_id} 不存在")

        mgr = DuckDBManager(db_path)

        if natural_language and not sql:
            table_info = mgr.get_table_info("data")
            schema = json.dumps(table_info, ensure_ascii=False)
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            sql = loop.run_until_complete(
                self.ai.generate_sql(schema, natural_language)
            )
            if sql is None:
                raise ValueError("AI 无法理解您的问题，请换个方式描述或直接输入 SQL")

        if not sql:
            raise ValueError("请提供 SQL 或自然语言描述")

        rows = mgr.query(sql)
        columns = list(rows[0].keys()) if rows else mgr.get_columns("data")

        explanation = None
        if natural_language:
            summary = f"{len(rows)} 行, 列: {', '.join(columns)}"
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            explanation = loop.run_until_complete(
                self.ai.explain_query_result(sql, summary, natural_language)
            )

        return QueryResult(
            columns=columns, rows=rows, row_count=len(rows),
            executed_sql=sql, ai_explanation=explanation,
        )
