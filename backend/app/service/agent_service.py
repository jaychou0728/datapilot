import os
import json
import asyncio
from app.prompts import prompt
from app.data.duckdb_manager import DuckDBManager
from app.service.chart_service import ChartService
from app.service.cleaning_service import CleaningService
from app.service.report_service import ReportService
from app.service.task_service import TaskService
from app.service.history_service import HistoryService
from app.service.lineage_service import LineageService
from app.ai.deepseek_client import DeepSeekClient
from app.config import DUCKDB_DIR

class AgentService:
    def __init__(self):
        self.duckdb_dir = DUCKDB_DIR
        self.task_svc = TaskService()
        self.ai = DeepSeekClient()
        self.hist_svc = HistoryService()
        self.lineage_svc = LineageService()

    async def run_pipeline(self, task_id: str, user_id: str, dataset_id: str):
        db_path = os.path.join(self.duckdb_dir, f"{dataset_id}.duckdb")
        if not os.path.exists(db_path):
            self.task_svc.update(task_id, status="failed", error="数据集不存在")
            return

        mgr = DuckDBManager(db_path)
        cs = ChartService(self.duckdb_dir)
        cleanup_svc = CleaningService(db_path=db_path, table_name="data")

        try:
            # Step 1: 数据画像 (10%)
            self.task_svc.update(task_id, status="running", progress=10)
            profile = cs._profile_data(mgr)
            total_rows = mgr.query("SELECT COUNT(*) AS cnt FROM data")[0]["cnt"]
            total_cols = len(profile["columns"])
            self.hist_svc.log(user_id, "agent", f"开始一键分析（{total_rows}行·{total_cols}列）", dataset_id)
            self.lineage_svc.log(user_id, dataset_id, task_id, "agent", "pipeline",
                                 f"开始一键分析",
                                 {"row_count": total_rows, "columns_count": total_cols, "columns": profile["columns"]},
                                 {})

            # Step 2: 智能清洗 (25%)
            self.task_svc.update(task_id, progress=25)
            rows_before = total_rows
            analysis = await cleanup_svc.ai_analyze()
            suggestions = analysis.get("suggestions", [])
            if suggestions:
                ops = [{"operation": s["operation"], "params": s.get("params", {})}
                       for s in suggestions if s.get("operation")]
                await cleanup_svc.ai_execute(ops)
                rows_after_clean = mgr.query("SELECT COUNT(*) AS cnt FROM data")[0]["cnt"]
                self.hist_svc.log(user_id, "clean", f"一键分析·自动清洗：{len(suggestions)}项", dataset_id)
                self.lineage_svc.log(user_id, dataset_id, task_id, "clean", "table:data",
                                     f"AI自动清洗：{len(suggestions)}项操作",
                                     {"row_count": rows_before},
                                     {"row_count": rows_after_clean})
            else:
                self.hist_svc.log(user_id, "clean", "一键分析·未发现需清洗的问题", dataset_id)

            # Refresh profile after cleaning
            profile = cs._profile_data(mgr)
            rows_after_clean = mgr.query("SELECT COUNT(*) AS cnt FROM data")[0]["cnt"]
            self.task_svc.update(task_id, progress=40)

            # Step 3: 图表推荐 (40%)
            charts = await cs.recommend(dataset_id)
            self.hist_svc.log(user_id, "chart", f"一键分析·生成{len(charts)}个图表", dataset_id)
            self.lineage_svc.log(user_id, dataset_id, task_id, "chart", "charts",
                                 f"AI推荐{len(charts)}个图表：{', '.join(c.title for c in charts[:5])}",
                                 {}, {"chart_count": len(charts)})
            self.task_svc.update(task_id, progress=55)

            # Step 4: 洞察提取 (60%)
            insights = await self._extract_insights(profile, charts)
            self.task_svc.update(task_id, progress=70)

            # Step 5: 报告生成 (80%)
            rs = ReportService(duckdb_dir=self.duckdb_dir)
            report = await rs.generate(user_id, dataset_id, dataset_id, profile)
            self.hist_svc.log(user_id, "report", f"一键分析·生成报告：{report.get('title', '')}", dataset_id)
            self.lineage_svc.log(user_id, dataset_id, task_id, "report", "report",
                                 f"生成报告：{report.get('title', '')}",
                                 {}, {"report_id": report["id"], "section_count": len(report.get("sections", []))})
            self.task_svc.update(task_id, progress=95)

            # Step 6: 聚合输出 (100%)
            result = {
                "report_id": report["id"],
                "report_title": report.get("title", ""),
                "chart_count": len(charts),
                "cleaning_changes": len(suggestions),
                "insights": insights,
            }
            self.hist_svc.log(user_id, "agent", f"一键分析完成：清洗{len(suggestions)}项·{len(charts)}个图表·报告已生成", dataset_id)
            self.task_svc.update(task_id, status="done", progress=100, output=result)

        except Exception as e:
            self.task_svc.update(task_id, status="failed", error=str(e))
            self.hist_svc.log(user_id, "agent", f"一键分析失败：{str(e)[:100]}", dataset_id)

    async def _extract_insights(self, profile: dict, charts: list) -> list[str]:
        summary = json.dumps({
            "total_rows": profile["total_rows"],
            "columns": profile["columns"],
            "numeric_columns": profile.get("numeric_columns", []),
            "column_stats": profile.get("column_stats", {}),
            "chart_count": len(charts),
        }, ensure_ascii=False, default=str)

        sys_msg, user_msg = prompt("insight", summary=summary[:6000])

        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        response = await self.ai.chat([
            {"role": "system", "content": sys_msg},
            {"role": "user", "content": user_msg},
        ], temperature=0.4)

        text = response.strip()
        if text.startswith("```"): text = text.split("```")[1].split("```")[0].strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return []
