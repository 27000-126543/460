from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi.responses import StreamingResponse
from io import BytesIO
from datetime import datetime
from app.database import get_db
from sqlalchemy.orm import Session
from app.schemas import DailyReport, ReportListResponse
from app.services import ReportService

router = APIRouter(prefix="/reports", tags=["运营报表"])


@router.get("/daily", response_model=DailyReport, summary="查询日报表")
def get_daily_report(
    date: str = Query(..., description="日期，格式 YYYY-MM-DD"),
    db: Session = Depends(get_db)
):
    try:
        date_obj = datetime.strptime(date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="日期格式错误，应为 YYYY-MM-DD")

    report = ReportService.get_daily_report(db, date_obj)
    return report


@router.get("/daily/export", summary="导出日报表 Excel")
def export_daily_report(
    date: str = Query(..., description="日期，格式 YYYY-MM-DD"),
    db: Session = Depends(get_db)
):
    try:
        date_obj = datetime.strptime(date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="日期格式错误，应为 YYYY-MM-DD")

    excel_data = ReportService.generate_excel_report(db, date_obj)
    if not excel_data:
        raise HTTPException(status_code=404, detail="报表数据不存在")

    return StreamingResponse(
        BytesIO(excel_data),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=report_{date}.xlsx"}
    )


@router.get("/range", response_model=ReportListResponse, summary="查询日期范围报表")
def get_range_report(
    start_date: str = Query(..., description="开始日期，格式 YYYY-MM-DD"),
    end_date: str = Query(..., description="结束日期，格式 YYYY-MM-DD"),
    db: Session = Depends(get_db)
):
    try:
        start_date_obj = datetime.strptime(start_date, "%Y-%m-%d").date()
        end_date_obj = datetime.strptime(end_date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="日期格式错误，应为 YYYY-MM-DD")

    reports = ReportService.get_report_by_date_range(db, start_date_obj, end_date_obj)
    return ReportListResponse(reports=reports)
