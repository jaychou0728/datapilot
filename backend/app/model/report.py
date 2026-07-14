from pydantic import BaseModel
from datetime import datetime

class ReportInfo(BaseModel):
    id: str
    user_id: str
    dataset_id: str
    title: str
    created_at: datetime
