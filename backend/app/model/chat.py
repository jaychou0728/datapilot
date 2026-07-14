from pydantic import BaseModel

class ChatRequest(BaseModel):
    dataset_id: str
    message: str
    history: list[dict] | None = None

class QueryResultData(BaseModel):
    columns: list[str]
    rows: list[dict]
    total_rows: int
    executed_sql: str
    error: str | None = None

class ChatResponse(BaseModel):
    answer: str
    sql_generated: str | None = None
    query_result: QueryResultData | None = None
    chart_suggestion: dict | None = None
