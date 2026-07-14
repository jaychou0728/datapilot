from pydantic import BaseModel

class CleaningIssue(BaseModel):
    type: str
    column: str | None = None
    count: int
    sample: list = []
    severity: str = "medium"

class ScanResponse(BaseModel):
    issues: list[CleaningIssue]
    summary: str

class CleanRequest(BaseModel):
    dataset_id: str
    actions: list[str]
    fill_strategy: str = "mean"

class CleanResult(BaseModel):
    rows_before: int
    rows_after: int
    changes: list[str]
    can_undo: bool = True
