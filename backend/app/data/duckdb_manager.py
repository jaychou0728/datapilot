import math
import duckdb
import pandas as pd
from typing import Any

def _sanitize_value(v: Any) -> Any:
    if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
        return None
    return v

FORBIDDEN_KEYWORDS = ["INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE", "TRUNCATE"]

class DuckDBManager:
    def __init__(self, db_path: str):
        self.db_path = db_path

    def _get_connection(self) -> duckdb.DuckDBPyConnection:
        return duckdb.connect(self.db_path, read_only=False)

    def create_table(self, df: pd.DataFrame, table_name: str):
        conn = self._get_connection()
        try:
            conn.execute(f"DROP TABLE IF EXISTS {table_name}")
            conn.execute(f"CREATE TABLE {table_name} AS SELECT * FROM df")
        finally:
            conn.close()

    def overwrite_table(self, df: pd.DataFrame, table_name: str):
        self.create_table(df, table_name)

    def query(self, sql: str, limit: int = 1000) -> list[dict[str, Any]]:
        sql_upper = sql.strip().upper()
        for kw in FORBIDDEN_KEYWORDS:
            if sql_upper.startswith(kw) or f"\n{kw}" in sql_upper:
                raise ValueError(f"不允许写操作，只能执行查询。检测到: {kw}")

        conn = self._get_connection()
        try:
            safe_sql = sql.strip().rstrip(";")
            if "LIMIT" in safe_sql.upper():
                result = conn.execute(safe_sql).fetchdf()
            else:
                result = conn.execute(f"SELECT * FROM ({safe_sql}) AS _sub LIMIT {limit}").fetchdf()
            result = result.where(pd.notna(result), None)
            return result.to_dict(orient="records")
        finally:
            conn.close()

    def preview(self, table_name: str, page: int = 1, page_size: int = 50) -> tuple[list[dict], int]:
        conn = self._get_connection()
        try:
            total = conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
            offset = (page - 1) * page_size
            rows = conn.execute(
                f"SELECT * FROM {table_name} LIMIT {page_size} OFFSET {offset}"
            ).fetchdf().to_dict(orient="records")
            return rows, total
        finally:
            conn.close()

    def get_table_info(self, table_name: str) -> list[dict[str, Any]]:
        conn = self._get_connection()
        try:
            df = conn.execute(f"DESCRIBE {table_name}").fetchdf()
            result = []
            for _, row in df.iterrows():
                col_name = row["column_name"]
                nulls = conn.execute(
                    f"SELECT COUNT(*) FROM {table_name} WHERE \"{col_name}\" IS NULL"
                ).fetchone()[0]
                samples = conn.execute(
                    f"SELECT DISTINCT \"{col_name}\" FROM {table_name} WHERE \"{col_name}\" IS NOT NULL LIMIT 5"
                ).fetchdf().iloc[:, 0].tolist()
                result.append({
                    "column_name": col_name,
                    "dtype": str(row["column_type"]),
                    "null_count": nulls,
                    "sample_values": samples,
                })
            return result
        finally:
            conn.close()

    def get_columns(self, table_name: str) -> list[str]:
        conn = self._get_connection()
        try:
            df = conn.execute(f"SELECT * FROM {table_name} LIMIT 0").fetchdf()
            return list(df.columns)
        finally:
            conn.close()

    def close(self):
        pass
