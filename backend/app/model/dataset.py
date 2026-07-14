from pydantic import BaseModel
from datetime import datetime

class ColumnInfo(BaseModel):
    name: str
    dtype: str
    null_count: int
    sample_values: list

class DatasetInfo(BaseModel):
    id: str
    name: str
    rows: int
    columns: int
    fields: list[ColumnInfo]
    created_at: datetime

class PreviewResponse(BaseModel):
    columns: list[str]
    rows: list[dict]
    total_rows: int
    page: int
    page_size: int
