from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi.responses import StreamingResponse
from io import BytesIO
from datetime import datetime
from app.database import get_db
from sqlalchemy.orm import Session
from app.schemas import (
    DailyReport, ReportListResponse, WeeklyReport, MonthlyReport,
    TrendResponse, ComparisonResponse
)
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


@router.get("/weekly", response_model=WeeklyReport, summary="查询周报表")
def get_weekly_report(
    year: int = Query(..., description="年份", ge=2000, le=2100),
    week: int = Query(..., description="周数", ge=1, le=53),
    db: Session = Depends(get_db)
):
    report = ReportService.get_weekly_report(db, year, week)
    return report


@router.get("/weekly/export", summary="导出周报表 Excel")
def export_weekly_report(
    year: int = Query(..., description="年份", ge=2000, le=2100),
    week: int = Query(..., description="周数", ge=1, le=53),
    db: Session = Depends(get_db)
):
    excel_data = ReportService.generate_weekly_excel_report(db, year, week)
    if not excel_data:
        raise HTTPException(status_code=404, detail="报表数据不存在")

    filename = f"weekly_report_{year}_w{week:02d}.xlsx"
    return StreamingResponse(
        BytesIO(excel_data),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/monthly", response_model=MonthlyReport, summary="查询月报表")
def get_monthly_report(
    year: int = Query(..., description="年份", ge=2000, le=2100),
    month: int = Query(..., description="月份", ge=1, le=12),
    db: Session = Depends(get_db)
):
    report = ReportService.get_monthly_report(db, year, month)
    return report


@router.get("/monthly/export", summary="导出月报表 Excel")
def export_monthly_report(
    year: int = Query(..., description="年份", ge=2000, le=2100),
    month: int = Query(..., description="月份", ge=1, le=12),
    db: Session = Depends(get_db)
):
    excel_data = ReportService.generate_monthly_excel_report(db, year, month)
    if not excel_data:
        raise HTTPException(status_code=404, detail="报表数据不存在")

    filename = f"monthly_report_{year}_{month:02d}.xlsx"
    return StreamingResponse(
        BytesIO(excel_data),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/trend/utilization", response_model=TrendResponse, summary="资源利用率趋势")
def get_utilization_trend(
    start_date: str = Query(..., description="开始日期，格式 YYYY-MM-DD"),
    end_date: str = Query(..., description="结束日期，格式 YYYY-MM-DD"),
    period: str = Query("day", description="周期：day/week/month"),
    db: Session = Depends(get_db)
):
    if period not in ('day', 'week', 'month'):
        raise HTTPException(status_code=400, detail="period 参数必须是 day、week 或 month")

    try:
        start_date_obj = datetime.strptime(start_date, "%Y-%m-%d").date()
        end_date_obj = datetime.strptime(end_date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="日期格式错误，应为 YYYY-MM-DD")

    if start_date_obj > end_date_obj:
        raise HTTPException(status_code=400, detail="开始日期不能晚于结束日期")

    trend = ReportService.get_utilization_trend(db, start_date_obj, end_date_obj, period)
    return trend


@router.get("/trend/revenue", response_model=TrendResponse, summary="收入趋势")
def get_revenue_trend(
    start_date: str = Query(..., description="开始日期，格式 YYYY-MM-DD"),
    end_date: str = Query(..., description="结束日期，格式 YYYY-MM-DD"),
    period: str = Query("day", description="周期：day/week/month"),
    db: Session = Depends(get_db)
):
    if period not in ('day', 'week', 'month'):
        raise HTTPException(status_code=400, detail="period 参数必须是 day、week 或 month")

    try:
        start_date_obj = datetime.strptime(start_date, "%Y-%m-%d").date()
        end_date_obj = datetime.strptime(end_date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="日期格式错误，应为 YYYY-MM-DD")

    if start_date_obj > end_date_obj:
        raise HTTPException(status_code=400, detail="开始日期不能晚于结束日期")

    trend = ReportService.get_revenue_trend(db, start_date_obj, end_date_obj, period)
    return trend


@router.get("/trend/work-orders", response_model=TrendResponse, summary="工单数量趋势")
def get_work_order_trend(
    start_date: str = Query(..., description="开始日期，格式 YYYY-MM-DD"),
    end_date: str = Query(..., description="结束日期，格式 YYYY-MM-DD"),
    period: str = Query("day", description="周期：day/week/month"),
    db: Session = Depends(get_db)
):
    if period not in ('day', 'week', 'month'):
        raise HTTPException(status_code=400, detail="period 参数必须是 day、week 或 month")

    try:
        start_date_obj = datetime.strptime(start_date, "%Y-%m-%d").date()
        end_date_obj = datetime.strptime(end_date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="日期格式错误，应为 YYYY-MM-DD")

    if start_date_obj > end_date_obj:
        raise HTTPException(status_code=400, detail="开始日期不能晚于结束日期")

    trend = ReportService.get_work_order_trend(db, start_date_obj, end_date_obj, period)
    return trend


@router.get("/comparison/floor", response_model=ComparisonResponse, summary="各楼层对比")
def get_floor_comparison(
    date: str = Query(..., description="日期，格式 YYYY-MM-DD"),
    db: Session = Depends(get_db)
):
    try:
        date_obj = datetime.strptime(date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="日期格式错误，应为 YYYY-MM-DD")

    comparison = ReportService.get_floor_comparison(db, date_obj)
    return comparison


@router.get("/comparison/resource-type", response_model=ComparisonResponse, summary="各资源类型对比")
def get_resource_type_comparison(
    date: str = Query(..., description="日期，格式 YYYY-MM-DD"),
    db: Session = Depends(get_db)
):
    try:
        date_obj = datetime.strptime(date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="日期格式错误，应为 YYYY-MM-DD")

    comparison = ReportService.get_resource_type_comparison(db, date_obj)
    return comparison


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
