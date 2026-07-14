import uuid
import os
from datetime import datetime
import pandas as pd
from app.utils.file_parser import parse_file, ParseError
from app.data.file_store import FileStore
from app.data.duckdb_manager import DuckDBManager
from app.model.dataset import DatasetInfo, ColumnInfo
from app.database import get_db

class DatasetService:
    def __init__(self, file_store: FileStore, duckdb_dir: str):
        self.file_store = file_store
        self.duckdb_dir = duckdb_dir
        os.makedirs(duckdb_dir, exist_ok=True)

    def ingest(self, filename: str, content: bytes, user_id: str = "") -> DatasetInfo:
        dataset_id = str(uuid.uuid4())
        self.file_store.save(dataset_id, filename, content)
        file_path = self.file_store.get_path(dataset_id) / filename
        df = parse_file(str(file_path))
        db_path = os.path.join(self.duckdb_dir, f"{dataset_id}.duckdb")
        mgr = DuckDBManager(db_path)
        mgr.create_table(df, "data")
        fields = self._build_fields(df, mgr)

        # Record ownership
        if user_id:
            conn = get_db()
            conn.execute(
                "INSERT INTO dataset_owners (dataset_id, user_id, filename) VALUES (?, ?, ?)",
                (dataset_id, user_id, filename),
            )
            conn.commit()
            conn.close()

        return DatasetInfo(
            id=dataset_id,
            name=filename,
            rows=len(df),
            columns=len(df.columns),
            fields=fields,
            created_at=datetime.now(),
        )

    def _build_fields(self, df: pd.DataFrame, mgr: DuckDBManager) -> list[ColumnInfo]:
        info = mgr.get_table_info("data")
        result = []
        for col_info in info:
            result.append(ColumnInfo(
                name=col_info["column_name"],
                dtype=col_info["dtype"],
                null_count=col_info["null_count"],
                sample_values=col_info["sample_values"],
            ))
        return result

    def preview(self, dataset_id: str, page: int = 1, page_size: int = 50) -> dict:
        db_path = os.path.join(self.duckdb_dir, f"{dataset_id}.duckdb")
        mgr = DuckDBManager(db_path)
        columns = mgr.get_columns("data")
        rows, total = mgr.preview("data", page, page_size)
        return {"columns": columns, "rows": rows, "total_rows": total, "page": page, "page_size": page_size}

    def get_info(self, dataset_id: str) -> dict | None:
        ds_dir = self.file_store.get_path(dataset_id)
        if not ds_dir.exists():
            return None
        files = list(ds_dir.iterdir())
        if not files:
            return None
        filename = files[0].name
        db_path = os.path.join(self.duckdb_dir, f"{dataset_id}.duckdb")
        if not os.path.exists(db_path):
            return None
        mgr = DuckDBManager(db_path)
        columns = mgr.get_columns("data")
        rows_count = mgr.query("SELECT COUNT(*) AS cnt FROM data")[0]["cnt"]
        fields = mgr.get_table_info("data")
        return {
            "id": dataset_id, "name": filename, "rows": rows_count,
            "columns": len(columns), "fields": fields,
        }

    def list_all(self, user_id: str = "", is_admin: bool = False) -> list[dict]:
        datasets = []
        owned_ids = set()
        if user_id and not is_admin:
            conn = get_db()
            rows = conn.execute(
                "SELECT dataset_id FROM dataset_owners WHERE user_id = ?", (user_id,)
            ).fetchall()
            conn.close()
            owned_ids = {r["dataset_id"] for r in rows}

        for ds_dir in self.file_store.base_dir.iterdir():
            if ds_dir.is_dir():
                ds_id = ds_dir.name
                if not is_admin and user_id and ds_id not in owned_ids:
                    continue
                info = self.get_info(ds_id)
                if info:
                    datasets.append(info)
        datasets.sort(key=lambda d: d.get("id", ""), reverse=True)
        return datasets

    def is_owner(self, dataset_id: str, user_id: str) -> bool:
        conn = get_db()
        row = conn.execute(
            "SELECT 1 FROM dataset_owners WHERE dataset_id = ? AND user_id = ?",
            (dataset_id, user_id),
        ).fetchone()
        conn.close()
        return row is not None

    def delete(self, dataset_id: str):
        self.file_store.delete(dataset_id)
        db_path = os.path.join(self.duckdb_dir, f"{dataset_id}.duckdb")
        if os.path.exists(db_path):
            os.remove(db_path)
        conn = get_db()
        conn.execute("DELETE FROM dataset_owners WHERE dataset_id = ?", (dataset_id,))
        conn.commit()
        conn.close()

    def get_table_name(self, dataset_id: str) -> str:
        return "data"

    def get_db_path(self, dataset_id: str) -> str:
        return os.path.join(self.duckdb_dir, f"{dataset_id}.duckdb")
