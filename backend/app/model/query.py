from pydantic import BaseModel

class QueryRequest(BaseModel):
    dataset_id: str
    sql: str | None = None
    natural_language: str | None = None

class QueryResult(BaseModel):
    columns: list[str]
    rows: list[dict]
    row_count: int
    executed_sql: str
    ai_explanation: str | None = None
