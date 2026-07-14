import os
import json
from app.data.duckdb_manager import DuckDBManager
from app.ai.deepseek_client import DeepSeekClient
from app.model.chart import ChartItem

class ChartService:
    def __init__(self, duckdb_dir: str):
        self.duckdb_dir = duckdb_dir
        self.ai = DeepSeekClient()

    async def recommend(self, dataset_id: str, hint: str | None = None) -> list[ChartItem]:
        db_path = os.path.join(self.duckdb_dir, f"{dataset_id}.duckdb")
        mgr = DuckDBManager(db_path)
        profile = self._profile_data(mgr)
        charts = await self.ai.recommend_charts(profile, hint or "")
        return [ChartItem(**c) for c in charts]

    def _profile_data(self, mgr: DuckDBManager) -> dict:
        table_info = mgr.get_table_info("data")
        columns = mgr.get_columns("data")
        total_rows = mgr.query("SELECT COUNT(*) AS cnt FROM data")[0]["cnt"]

        numeric_cols = []
        categorical_cols = []
        date_cols = []
        col_stats = {}

        for col in columns:
            quoted = f'"{col}"'
            info = next((t for t in table_info if t["column_name"] == col), {})
            dtype = info.get("dtype", "").upper()

            is_date = any(t in dtype for t in ["DATE", "TIME", "TIMESTAMP"])
            is_numeric = any(t in dtype for t in ["INT", "FLOAT", "DOUBLE", "BIGINT", "DECIMAL", "NUMERIC"])

            if is_date:
                date_cols.append(col)
                categorical_cols.append(col)
            elif is_numeric:
                numeric_cols.append(col)
            else:
                categorical_cols.append(col)

            # Base stats for all columns
            if is_numeric:
                stats = mgr.query(f"""
                    SELECT
                        MIN({quoted}) AS min_val,
                        MAX({quoted}) AS max_val,
                        ROUND(AVG({quoted}), 2) AS avg_val,
                        ROUND(STDDEV({quoted}), 2) AS std_val,
                        COUNT(DISTINCT {quoted}) AS unique_count,
                        SUM(CASE WHEN {quoted} IS NULL THEN 1 ELSE 0 END) AS null_count
                    FROM data
                """)
                s = stats[0] if stats else {}
                col_stats[col] = {
                    "type": "numeric",
                    "min": s.get("min_val"),
                    "max": s.get("max_val"),
                    "avg": s.get("avg_val"),
                    "std": s.get("std_val"),
                    "unique_count": s.get("unique_count", 0),
                    "null_count": s.get("null_count", 0),
                }
            else:
                unique_count = mgr.query(f"SELECT COUNT(DISTINCT {quoted}) AS cnt FROM data")[0]["cnt"]
                top_vals = mgr.query(f"""
                    SELECT {quoted} AS val, COUNT(*) AS cnt
                    FROM data WHERE {quoted} IS NOT NULL
                    GROUP BY {quoted} ORDER BY cnt DESC LIMIT 10
                """)
                nulls = mgr.query(f"SELECT COUNT(*) AS cnt FROM data WHERE {quoted} IS NULL")[0]["cnt"]
                col_stats[col] = {
                    "type": "date" if is_date else "categorical",
                    "unique_count": unique_count,
                    "null_count": nulls,
                    "top_values": [{"value": r["val"], "count": r["cnt"]} for r in top_vals],
                }

        # --- DATA QUALITY ASSESSMENT ---
        assessment = []
        for col in categorical_cols:
            if col_stats[col]["unique_count"] == 1:
                val = col_stats[col]["top_values"][0]["value"]
                assessment.append(f'列"{col}"只有一个值"{val}"，不适合分组对比')
            elif col_stats[col]["unique_count"] <= 3:
                vals = [v["value"] for v in col_stats[col]["top_values"]]
                assessment.append(f'列"{col}"只有{col_stats[col]["unique_count"]}个不同值: {vals}')

        for col in numeric_cols:
            s = col_stats[col]
            if s["std"] == 0 or (s["max"] == s["min"]):
                assessment.append(f'列"{col}"所有值相同({s["min"]})，无法做数值对比')

        # --- SAMPLE ROWS (stratified: first, middle, last) ---
        sample_rows = mgr.query(f"SELECT * FROM data LIMIT 20")
        if total_rows > 40:
            mid = total_rows // 2
            mid_rows = mgr.query(f"SELECT * FROM data LIMIT 10 OFFSET {mid}")
            sample_rows.extend(mid_rows)
            last_rows = mgr.query(f"SELECT * FROM data LIMIT 10 OFFSET {total_rows - 10}")
            sample_rows.extend(last_rows)

        # ============ CHART-TYPE-SPECIFIC DATA ============

        # --- 1. AGGREGATIONS (for bar/pie charts) ---
        aggregations = {}
        for cat_col in categorical_cols:
            cat_unique = col_stats[cat_col]["unique_count"]
            if cat_unique > 30 or cat_unique == 0:
                continue
            quoted_cat = f'"{cat_col}"'
            agg_parts = [quoted_cat, "COUNT(*) AS _count"]
            for num_col in numeric_cols:
                quoted_num = f'"{num_col}"'
                agg_parts.append(f"ROUND(AVG({quoted_num}), 2) AS _{num_col}_avg")
                agg_parts.append(f"ROUND(SUM({quoted_num}), 2) AS _{num_col}_sum")
            try:
                agg_result = mgr.query(
                    f"SELECT {', '.join(agg_parts)} FROM data GROUP BY {quoted_cat} ORDER BY _count DESC",
                    limit=50
                )
                if agg_result:
                    aggregations[cat_col] = agg_result
            except Exception:
                pass

        # --- 2. TIME SERIES (for line charts) ---
        time_series = {}
        for date_col in date_cols:
            for num_col in numeric_cols:
                key = f"{date_col}__{num_col}"
                try:
                    ts = mgr.query(f"""
                        SELECT "{date_col}" AS _date, "{num_col}" AS _value
                        FROM data
                        WHERE "{date_col}" IS NOT NULL AND "{num_col}" IS NOT NULL
                        ORDER BY "{date_col}"
                        LIMIT 200
                    """)
                    if ts and len(ts) > 1:
                        time_series[key] = ts
                except Exception:
                    pass

        # --- 3. HISTOGRAMS (for distribution charts) ---
        histograms = {}
        for num_col in numeric_cols:
            s = col_stats[num_col]
            if s["min"] is None or s["max"] is None or s["min"] == s["max"]:
                continue
            try:
                bucket_count = min(12, max(5, int(total_rows ** 0.3)))
                width = (s["max"] - s["min"]) / bucket_count
                if width == 0:
                    continue
                hist_sql = f"""
                    SELECT
                        FLOOR(("{num_col}" - {s['min']}) / {width}) AS bucket,
                        COUNT(*) AS cnt,
                        ROUND({s['min']} + (FLOOR(("{num_col}" - {s['min']}) / {width}) + 0.5) * {width}, 2) AS bin_center
                    FROM data
                    WHERE "{num_col}" IS NOT NULL
                    GROUP BY bucket
                    ORDER BY bucket
                """
                hist = mgr.query(hist_sql, limit=20)
                if hist:
                    histograms[num_col] = hist
            except Exception:
                pass

        # --- 4. SCATTER PAIRS (for scatter/bubble charts) ---
        scatter_data = {}
        scatter_notes = []
        if len(numeric_cols) >= 2:
            # Compute all pairs among top 5 numeric cols (by variance)
            sorted_nums = sorted(numeric_cols,
                key=lambda c: col_stats[c].get("std", 0) or 0, reverse=True)[:5]
            pairs = []
            for i in range(len(sorted_nums)):
                for j in range(i + 1, len(sorted_nums)):
                    pairs.append((sorted_nums[i], sorted_nums[j]))

            for x_col, y_col in pairs:
                key = f"{x_col}__{y_col}"
                x_unique = col_stats[x_col]["unique_count"]
                y_unique = col_stats[y_col]["unique_count"]

                # For low-cardinality columns, include all points (no sampling needed)
                if x_unique <= 5 and y_unique <= 5:
                    try:
                        points = mgr.query(f"""
                            SELECT "{x_col}" AS x, "{y_col}" AS y, COUNT(*) AS weight
                            FROM data
                            WHERE "{x_col}" IS NOT NULL AND "{y_col}" IS NOT NULL
                            GROUP BY "{x_col}", "{y_col}"
                            ORDER BY weight DESC
                            LIMIT 500
                        """)
                        if points and len(points) >= 2:
                            scatter_data[key] = points
                            scatter_notes.append(f"{key}: {len(points)}个不同点(全量,含权重)")
                    except Exception:
                        pass
                else:
                    # For high-cardinality, sample 500 points evenly
                    sample_size = min(500, int(total_rows))
                    step = max(1, total_rows // sample_size)
                    try:
                        points = mgr.query(f"""
                            SELECT "{x_col}" AS x, "{y_col}" AS y
                            FROM (
                                SELECT "{x_col}", "{y_col}",
                                       ROW_NUMBER() OVER () AS rn
                                FROM data
                                WHERE "{x_col}" IS NOT NULL AND "{y_col}" IS NOT NULL
                            ) _sub
                            WHERE rn % {step} = 0
                            LIMIT 500
                        """)
                        if points and len(points) >= 5:
                            scatter_data[key] = points
                            scatter_notes.append(f"{key}: 均匀采样{len(points)}个点(共{total_rows}行)")
                    except Exception:
                        pass

            # Flag sparse scatter data
            for key, points in scatter_data.items():
                if len(points) <= 5:
                    scatter_notes.append(f"! {key}: 只有{len(points)}个点，散点图信息量低")

        # --- 5. CORRELATION MATRIX (for heatmap) ---
        correlations = []
        for i, c1 in enumerate(numeric_cols):
            for c2 in numeric_cols[i + 1:]:
                try:
                    corr = mgr.query(f"SELECT ROUND(CORR(\"{c1}\", \"{c2}\"), 3) AS r FROM data")
                    if corr and corr[0]["r"] is not None:
                        correlations.append({"x": c1, "y": c2, "r": corr[0]["r"]})
                except Exception:
                    pass
        correlations.sort(key=lambda c: abs(c["r"]), reverse=True)

        # --- 6. TOP/BOTTOM EXTREMES (for highlighting in charts) ---
        extremes = {}
        for num_col in numeric_cols[:4]:  # Top 4 numeric cols
            try:
                top = mgr.query(f"""
                    SELECT * FROM data
                    WHERE "{num_col}" IS NOT NULL
                    ORDER BY "{num_col}" DESC
                    LIMIT 5
                """)
                bottom = mgr.query(f"""
                    SELECT * FROM data
                    WHERE "{num_col}" IS NOT NULL
                    ORDER BY "{num_col}" ASC
                    LIMIT 5
                """)
                extremes[num_col] = {"top": top, "bottom": bottom}
            except Exception:
                pass

        return {
            "total_rows": total_rows,
            "total_columns": len(columns),
            "columns": columns,
            "numeric_columns": numeric_cols,
            "categorical_columns": categorical_cols,
            "date_columns": date_cols,
            "column_stats": col_stats,
            "assessment": assessment,
            # Chart-specific data
            "sample_rows": sample_rows,
            "aggregations": aggregations,
            "time_series": time_series,
            "histograms": histograms,
            "scatter_data": scatter_data,
            "scatter_notes": scatter_notes,
            "correlations": correlations,
            "extremes": extremes,
        }
