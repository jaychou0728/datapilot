import os
import json
import asyncio
from app.data.duckdb_manager import DuckDBManager
from app.service.chart_service import ChartService
from app.service.cleaning_service import CleaningService
from app.service.report_service import ReportService
from app.service.task_service import TaskService
from app.ai.deepseek_client import DeepSeekClient
from app.config import DUCKDB_DIR

class AgentService:
    def __init__(self):
        self.duckdb_dir = DUCKDB_DIR
        self.task_svc = TaskService()
        self.ai = DeepSeekClient()

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

            # Step 2: 智能清洗 (25%)
            self.task_svc.update(task_id, progress=25)
            analysis = await cleanup_svc.ai_analyze()
            suggestions = analysis.get("suggestions", [])
            if suggestions:
                ops = [{"operation": s["operation"], "params": s.get("params", {})}
                       for s in suggestions if s.get("operation")]
                await cleanup_svc.ai_execute(ops)

            # Refresh profile after cleaning
            profile = cs._profile_data(mgr)
            self.task_svc.update(task_id, progress=40)

            # Step 3: 图表推荐 (40%)
            charts = await cs.recommend(dataset_id)
            self.task_svc.update(task_id, progress=55)

            # Step 4: 洞察提取 (60%)
            insights = await self._extract_insights(profile, charts)
            self.task_svc.update(task_id, progress=70)

            # Step 5: 报告生成 (80%)
            rs = ReportService(duckdb_dir=self.duckdb_dir)
            report = await rs.generate(user_id, dataset_id, dataset_id, profile)
            self.task_svc.update(task_id, progress=95)

            # Step 6: 聚合输出 (100%)
            result = {
                "report_id": report["id"],
                "report_title": report.get("title", ""),
                "chart_count": len(charts),
                "cleaning_changes": len(suggestions),
                "insights": insights,
            }
            self.task_svc.update(task_id, status="done", progress=100, output=result)

        except Exception as e:
            self.task_svc.update(task_id, status="failed", error=str(e))

    async def _extract_insights(self, profile: dict, charts: list) -> list[str]:
        summary = json.dumps({
            "total_rows": profile["total_rows"],
            "columns": profile["columns"],
            "numeric_columns": profile.get("numeric_columns", []),
            "column_stats": profile.get("column_stats", {}),
            "chart_count": len(charts),
        }, ensure_ascii=False, default=str)

        prompt = f"""你是资深数据分析师。根据以下数据画像，提取 3-5 个关键洞察。
每个洞察 50-100 字，包含具体数字。

## 数据画像
{summary[:6000]}

只返回 JSON 字符串数组: ["洞察1", "洞察2", ...]"""

        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        response = await self.ai.chat([
            {"role": "system", "content": "只输出合法JSON数组。"},
            {"role": "user", "content": prompt},
        ], temperature=0.4)

        text = response.strip()
        if text.startswith("```"): text = text.split("```")[1].split("```")[0].strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return []
