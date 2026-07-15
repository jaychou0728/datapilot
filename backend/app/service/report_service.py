import uuid
import json
import os
import asyncio
from datetime import datetime
from app.database import get_db
from app.ai.deepseek_client import DeepSeekClient
from app.prompts import prompt

REPORTS_DIR = "reports"

class ReportService:
    def __init__(self, duckdb_dir: str):
        self.duckdb_dir = duckdb_dir
        self.ai = DeepSeekClient()
        os.makedirs(REPORTS_DIR, exist_ok=True)

    def _summarize_profile(self, profile: dict) -> str:
        """Build a compact summary instead of dumping the full profile."""
        lines = [f"总行数: {profile.get('total_rows')}, 总列数: {profile.get('total_columns')}"]
        lines.append(f"数值列: {profile.get('numeric_columns', [])}")
        lines.append(f"分类列: {profile.get('categorical_columns', [])}")

        col_stats = profile.get('column_stats', {})
        for col, s in col_stats.items():
            if s.get('type') == 'numeric':
                lines.append(f"  {col}: 数值, 范围[{s.get('min')},{s.get('max')}], 均值{s.get('avg')}, 标准差{s.get('std')}")
            else:
                vals = s.get('top_values', [])[:5]
                dist = ', '.join([f"{v['value']}({v['count']})" for v in vals])
                lines.append(f"  {col}: 分类, {s.get('unique_count')}个值, {dist}")

        # Include all aggregations
        aggs = profile.get('aggregations', {})
        if aggs:
            lines.append("聚合数据(柱状图/饼图用):")
            for cat_col, rows in aggs.items():
                lines.append(f"  按{cat_col}分组({len(rows)}组): {json.dumps(rows, ensure_ascii=False, default=str)}")

        # Include time series
        ts = profile.get('time_series', {})
        if ts:
            lines.append("时序数据(折线图用):")
            for key, rows in ts.items():
                lines.append(f"  {key}({len(rows)}点): {json.dumps(rows[:30], ensure_ascii=False, default=str)}")

        # Include correlations
        corrs = profile.get('correlations', [])[:10]
        if corrs:
            lines.append(f"相关性: {json.dumps(corrs, ensure_ascii=False)}")

        # Include histograms
        hists = profile.get('histograms', {})
        if hists:
            lines.append("分布数据(直方图用):")
            for col, rows in hists.items():
                lines.append(f"  {col}: {json.dumps(rows, ensure_ascii=False, default=str)}")

        # Sample rows (10 rows for context)
        samples = profile.get('sample_rows', [])[:10]
        if samples:
            lines.append(f"样本行: {json.dumps(samples, ensure_ascii=False, default=str)}")

        summary = '\n'.join(lines)
        # Truncate if too long (max ~12000 chars for prompt safety)
        if len(summary) > 12000:
            summary = summary[:12000] + "\n...(数据截断)"
        return summary

    async def generate(self, user_id: str, dataset_id: str, dataset_name: str, data_profile: dict) -> dict:
        report_id = str(uuid.uuid4())
        summary = self._summarize_profile(data_profile)

        sys_msg, user_msg = prompt("report", summary=summary)

        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        response = await self.ai.chat([
            {"role": "system", "content": sys_msg},
            {"role": "user", "content": user_msg},
        ], temperature=0.3, max_tokens=16384)

        text = response.strip()
        if text.startswith("```json"): text = text.split("```json")[1].split("```")[0].strip()
        elif text.startswith("```"): text = text.split("```")[1].split("```")[0].strip()

        try:
            report_data = json.loads(text)
        except json.JSONDecodeError as e:
            print(f"[Report] JSON parse error: {e}")
            print(f"[Report] Raw response (first 500 chars): {text[:500]}")
            report_data = {"title": "分析报告", "sections": [{"type": "text", "title": "生成失败", "content": f"AI 返回数据异常: {text[:200]}..."}]}

        file_path = os.path.join(REPORTS_DIR, f"{report_id}.json")
        full = {
            "id": report_id, "dataset_name": dataset_name,
            "generated_at": datetime.now().isoformat(),
            "title": report_data.get("title", "分析报告"),
            "sections": report_data.get("sections", []),
        }
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(full, f, ensure_ascii=False, default=str)

        conn = get_db()
        conn.execute(
            "INSERT INTO reports (id, user_id, dataset_id, title, file_path, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (report_id, user_id, dataset_id, full["title"], file_path, datetime.now().isoformat()),
        )
        conn.commit()
        conn.close()
        return full

    def get_report(self, report_id: str) -> dict | None:
        file_path = os.path.join(REPORTS_DIR, f"{report_id}.json")
        if not os.path.exists(file_path): return None
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def list_by_user(self, user_id: str) -> list[dict]:
        conn = get_db()
        rows = conn.execute("SELECT * FROM reports WHERE user_id = ? ORDER BY created_at DESC", (user_id,)).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def list_all(self) -> list[dict]:
        conn = get_db()
        rows = conn.execute("SELECT * FROM reports ORDER BY created_at DESC").fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def delete(self, report_id: str):
        conn = get_db()
        conn.execute("DELETE FROM reports WHERE id = ?", (report_id,))
        conn.commit()
        conn.close()
        fp = os.path.join(REPORTS_DIR, f"{report_id}.json")
        if os.path.exists(fp): os.remove(fp)
