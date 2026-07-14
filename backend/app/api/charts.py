import os
import json
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from app.service.chart_service import ChartService
from app.service.history_service import HistoryService
from app.data.duckdb_manager import DuckDBManager
from app.config import DUCKDB_DIR
from app.middleware.auth import get_current_user_id
from app.utils.response import success, error
from app.model.chart import ChartRecommendRequest

router = APIRouter(prefix="/api/charts", tags=["charts"])
hist_svc = HistoryService()


class ChartDataRequest(BaseModel):
    dataset_id: str
    query: dict  # {type, x_col, y_col, group_col, agg}


@router.post("/recommend")
async def recommend(req: ChartRecommendRequest, user_id: str = Depends(get_current_user_id)):
    db_path = os.path.join(DUCKDB_DIR, f"{req.dataset_id}.duckdb")
    if not os.path.exists(db_path):
        return error(404, "数据集不存在")
    svc = ChartService(duckdb_dir=DUCKDB_DIR)
    try:
        charts = await svc.recommend(req.dataset_id, req.hint)
        hist_svc.log(user_id, "chart", f"生成了 {len(charts)} 个图表", req.dataset_id)
        return success(data={"charts": [c.model_dump() for c in charts]})
    except Exception as e:
        return error(500, str(e))


@router.post("/data")
def get_chart_data(req: ChartDataRequest):
    db_path = os.path.join(DUCKDB_DIR, f"{req.dataset_id}.duckdb")
    if not os.path.exists(db_path):
        return error(404, "数据集不存在")

    mgr = DuckDBManager(db_path)
    q = req.query

    def r(v, decimals=2):
        """Round numeric values for display."""
        if isinstance(v, float):
            return round(v, decimals)
        return v

    chart_type = q.get("type", "bar")
    x_col = q.get("x_col", "")
    y_col = q.get("y_col", x_col)
    group_col = q.get("group_col", "")
    agg = q.get("agg", "").upper()
    # Normalize category names: TRIM whitespace, Title Case for dedupe
    trim_expr = f"TRIM(CAST({x_col if x_col else group_col} AS VARCHAR))"
    limit = q.get("limit", 1000)

    try:
        if chart_type == "scatter":
            x = f'"{x_col}"' if x_col else '"x"'
            y = f'"{y_col}"' if y_col else '"y"'
            # Filter out nulls, zeros, and implausible negative values
            sql = f"""SELECT {x} AS x, {y} AS y FROM data
                       WHERE {x} IS NOT NULL AND {y} IS NOT NULL
                       AND {x} != 0 AND {y} != 0
                       AND {x} > -1 AND {y} > -1
                       LIMIT {limit}"""
            rows = mgr.query(sql, limit=limit)
            return success(data={"data": [[r(row["x"]), r(row["y"])] for row in rows]})

        elif chart_type == "line" or chart_type == "time_series":
            x = f'"{x_col}"' if x_col else '"x"'
            y = f'"{y_col}"' if y_col else '"y"'
            sql = f"SELECT {x} AS _x, {y} AS _y FROM data WHERE {x} IS NOT NULL AND {y} IS NOT NULL ORDER BY {x} LIMIT {limit}"
            rows = mgr.query(sql, limit=limit)
            return success(data={
                "categories": [str(row["_x"]) for row in rows],
                "values": [r(row["_y"]) for row in rows],
            })

        elif chart_type == "histogram":
            col = f'"{y_col or x_col}"'
            stats = mgr.query(f"SELECT MIN({col}) AS mn, MAX({col}) AS mx FROM data")
            mn, mx = stats[0]["mn"], stats[0]["mx"]
            if mn is None or mx is None or mn == mx:
                return error(400, "列数据不足以生成直方图")
            bins = q.get("bins", 10)
            width = (mx - mn) / bins
            hist = mgr.query(f"""
                SELECT ROUND({mn} + (FLOOR(({col} - {mn}) / {width}) + 0.5) * {width}, 2) AS bin, COUNT(*) AS cnt
                FROM data WHERE {col} IS NOT NULL
                GROUP BY bin ORDER BY bin
            """)
            return success(data={
                "categories": [str(r["bin"]) for r in hist],
                "values": [r["cnt"] for r in hist],
            })

        elif chart_type == "pie":
            col = f'"{group_col or x_col}"'
            label_expr = f"TRIM({col})"
            sql = f"SELECT {label_expr} AS name, COUNT(*) AS value FROM data WHERE {col} IS NOT NULL GROUP BY {label_expr} ORDER BY value DESC LIMIT {limit}"
            rows = mgr.query(sql, limit=limit)
            return success(data={"data": [{"name": str(r["name"]), "value": r["value"]} for r in rows]})

        elif chart_type == "heatmap":
            x = f'"{x_col}"'
            y = f'"{y_col}"'
            if agg:
                sql = f"SELECT {x} AS x, {y} AS y, {agg}(*) AS v FROM data GROUP BY {x}, {y} LIMIT {limit}"
            else:
                sql = f"SELECT {x} AS x, {y} AS y, COUNT(*) AS v FROM data GROUP BY {x}, {y} LIMIT {limit}"
            rows = mgr.query(sql, limit=limit)
            return success(data={"data": [[r["x"], r["y"], r["v"]] for r in rows]})

        else:  # bar / default aggregation
            x = f'"{x_col}"' if x_col else f'"{group_col}"'
            col = f'"{y_col or x_col}"'
            label_expr = f"TRIM({x})"
            if agg:
                sql = f"SELECT {label_expr} AS label, {agg}({col}) AS value FROM data WHERE {x} IS NOT NULL GROUP BY {label_expr} ORDER BY value DESC LIMIT {limit}"
            else:
                sql = f"SELECT {label_expr} AS label, COUNT(*) AS value FROM data WHERE {x} IS NOT NULL GROUP BY {label_expr} ORDER BY value DESC LIMIT {limit}"
            rows = mgr.query(sql, limit=limit)
            return success(data={
                "categories": [str(row["label"]) for row in rows],
                "values": [r(row["value"]) for row in rows],
            })
    except Exception as e:
        return error(500, str(e))
