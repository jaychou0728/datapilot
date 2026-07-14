import os
from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from app.middleware.auth import get_current_user_id, get_current_user
from app.service.report_service import ReportService
from app.service.history_service import HistoryService
from app.service.chart_service import ChartService
from app.data.duckdb_manager import DuckDBManager
from app.data.file_store import FileStore
from app.config import DUCKDB_DIR, UPLOAD_DIR
from app.utils.response import success, error

router = APIRouter(prefix="/api/reports", tags=["reports"])
svc = ReportService(duckdb_dir=DUCKDB_DIR)
hist_svc = HistoryService()

@router.post("/generate")
async def generate(dataset_id: str = Query(...), user_id: str = Depends(get_current_user_id)):
    db_path = os.path.join(DUCKDB_DIR, f"{dataset_id}.duckdb")
    if not os.path.exists(db_path):
        return error(404, "数据集不存在")

    mgr = DuckDBManager(db_path)
    cs = ChartService(DUCKDB_DIR)
    profile = cs._profile_data(mgr)

    fs = FileStore(UPLOAD_DIR)
    ds_dir = fs.get_path(dataset_id)
    ds_name = "unknown"
    if ds_dir.exists():
        files = list(ds_dir.iterdir())
        if files: ds_name = files[0].name

    report = await svc.generate(user_id, dataset_id, ds_name, profile)
    hist_svc.log(user_id, "report", f"生成分析报告: {report.get('title', '')}", dataset_id)
    return success(data=report)

@router.get("")
def list_reports(user: dict = Depends(get_current_user)):
    if user["role"] == "admin":
        return success(data=svc.list_all())
    return success(data=svc.list_by_user(user["id"]))

@router.get("/{report_id}")
def get_report(report_id: str):
    report = svc.get_report(report_id)
    if not report: return error(404, "报告不存在")
    return success(data=report)

@router.delete("/{report_id}")
def delete_report(report_id: str):
    svc.delete(report_id)
    return success(message="已删除")

@router.get("/{report_id}/export")
async def export_pdf(report_id: str):
    report = svc.get_report(report_id)
    if not report: return error(404, "报告不存在")

    try:
        html = _render_report_html(report)
        pdf = await _html_to_pdf(html)
        return Response(content=pdf, media_type="application/pdf",
                       headers={"Content-Disposition": f'attachment; filename="report-{report_id[:8]}.pdf"'})
    except Exception as e:
        return error(500, str(e))


async def _html_to_pdf(html: str) -> bytes:
    import tempfile, os
    from playwright.async_api import async_playwright

    tmp = tempfile.NamedTemporaryFile(suffix=".html", delete=False, mode="w", encoding="utf-8")
    tmp.write(html)
    tmp.close()

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()
            file_url = f"file:///{tmp.name.replace(chr(92), '/')}"
            await page.goto(file_url, wait_until="networkidle")
            # Wait for ECharts to render (charts init via setTimeout or onload)
            await page.wait_for_timeout(2000)
            pdf = await page.pdf(format="A4", margin={"top": "20mm", "bottom": "20mm", "left": "15mm", "right": "15mm"})
            await browser.close()
            return pdf
    finally:
        os.unlink(tmp.name)

def _render_report_html(report: dict) -> str:
    import json
    chart_scripts = ""
    chart_divs = ""
    chart_idx = 0

    for s in report.get("sections", []):
        if s["type"] == "text":
            chart_divs += f"<h3>{s['title']}</h3><p class='text'>{s['content']}</p>"
        elif s["type"] == "chart":
            opt_json = json.dumps(s.get("echarts_option", {}), ensure_ascii=False)
            chart_divs += f"<h3>{s['title']}</h3><div id='chart{chart_idx}' class='chart'></div><p class='caption'>{s.get('content', '')}</p>"
            chart_scripts += f"var c{chart_idx}=echarts.init(document.getElementById('chart{chart_idx}'));c{chart_idx}.setOption({opt_json});"
            chart_idx += 1

    return f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<script src="https://cdn.jsdelivr.net/npm/echarts@5.6.0/dist/echarts.min.js"></script>
<style>
body {{ font-family: 'PingFang SC','Microsoft YaHei',sans-serif; max-width: 780px; margin: 0 auto; padding: 40px 50px; color: #1a1a1a; }}
h1 {{ font-size: 24px; margin-bottom: 2px; }}
.subtitle {{ color: #828282; font-size: 12px; margin: 0 0 32px; }}
h3 {{ font-size: 15px; margin: 28px 0 8px; }}
p.text {{ font-size: 13px; line-height: 1.9; color: #333; margin: 0 0 12px; }}
.chart {{ width: 100%; height: 320px; margin: 8px 0; }}
p.caption {{ font-size: 11px; color: #868e96; text-align: center; margin: 4px 0 20px; }}
</style></head><body>
<h1>{report.get('title', '')}</h1>
<p class="subtitle">{report.get('dataset_name', '')} · {report.get('generated_at', '')}</p>
{chart_divs}
<script>{chart_scripts}</script>
</body></html>"""
