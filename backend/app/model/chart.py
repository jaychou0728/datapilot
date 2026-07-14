from pydantic import BaseModel

class ChartRecommendRequest(BaseModel):
    dataset_id: str
    hint: str | None = None

class ChartItem(BaseModel):
    title: str
    chart_type: str
    echarts_option: dict
    reason: str
    data_query: dict | None = None  # {type, x_col, y_col, group_col, agg, limit}

class ChartRecommendResponse(BaseModel):
    charts: list[ChartItem]
