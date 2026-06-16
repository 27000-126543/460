from sqlalchemy.orm import Session
from app.models import Booking, BookingStatus, WorkOrder, WorkOrderStatus, Resource, ResourceType
from datetime import date, timedelta, datetime
from typing import Optional, List
from openpyxl import Workbook
from io import BytesIO


class ReportService:
    @staticmethod
    def get_daily_report(db: Session, report_date: date) -> dict:
        start_dt = datetime.combine(report_date, datetime.min.time())
        end_dt = datetime.combine(report_date, datetime.max.time())

        resources = db.query(Resource).all()
        resource_by_type_floor = {}
        for r in resources:
            key = (r.floor, r.type.value)
            if key not in resource_by_type_floor:
                resource_by_type_floor[key] = {"count": 0, "hourly_rate": r.hourly_rate}
            resource_by_type_floor[key]["count"] += 1

        bookings = db.query(Booking).filter(
            Booking.start_time <= end_dt,
            Booking.end_time >= start_dt,
            Booking.status.in_([BookingStatus.COMPLETED, BookingStatus.APPROVED])
        ).all()

        booked_hours_by_key = {}
        revenue_by_key = {}
        for booking in bookings:
            r = booking.resource
            if not r:
                continue
            key = (r.floor, r.type.value)
            
            overlap_start = max(booking.start_time, start_dt)
            overlap_end = min(booking.end_time, end_dt)
            hours = max(0, (overlap_end - overlap_start).total_seconds() / 3600)
            
            booked_hours_by_key[key] = booked_hours_by_key.get(key, 0) + hours
            
            amount = booking.actual_amount if booking.actual_amount else booking.total_amount
            revenue_by_key[key] = revenue_by_key.get(key, 0) + amount

        floor_utilizations = []
        total_revenue = 0
        total_booked_hours = 0
        total_available_hours = 0

        for (floor, rtype), info in resource_by_type_floor.items():
            count = info["count"]
            total_hours = count * 24
            booked_hours = booked_hours_by_key.get((floor, rtype), 0)
            revenue = revenue_by_key.get((floor, rtype), 0)
            utilization = booked_hours / total_hours if total_hours > 0 else 0

            floor_utilizations.append({
                "floor": floor,
                "resource_type": rtype,
                "total_resources": count,
                "total_hours": total_hours,
                "booked_hours": round(booked_hours, 2),
                "utilization_rate": round(utilization, 4),
                "revenue": round(revenue, 2)
            })

            total_revenue += revenue
            total_booked_hours += booked_hours
            total_available_hours += total_hours

        overall_utilization = total_booked_hours / total_available_hours if total_available_hours > 0 else 0

        work_orders = db.query(WorkOrder).filter(
            WorkOrder.created_at >= start_dt,
            WorkOrder.created_at <= end_dt
        ).all()

        total_orders = len(work_orders)
        completed_orders = sum(1 for w in work_orders if w.status == WorkOrderStatus.COMPLETED)

        response_times = []
        completion_times = []
        for w in work_orders:
            if w.accepted_at and w.created_at:
                response_times.append((w.accepted_at - w.created_at).total_seconds() / 60)
            if w.completed_at and w.created_at:
                completion_times.append((w.completed_at - w.created_at).total_seconds() / 60)

        avg_response = sum(response_times) / len(response_times) if response_times else 0
        avg_completion = sum(completion_times) / len(completion_times) if completion_times else 0

        data_available = total_booked_hours > 0 or total_orders > 0

        return {
            "report_date": report_date.isoformat(),
            "data_available": data_available,
            "floor_utilizations": sorted(floor_utilizations, key=lambda x: (x["floor"], x["resource_type"])),
            "total_revenue": round(total_revenue, 2),
            "overall_utilization_rate": round(overall_utilization, 4),
            "work_order_stats": {
                "total_orders": total_orders,
                "completed_orders": completed_orders,
                "avg_response_minutes": round(avg_response, 2),
                "avg_completion_minutes": round(avg_completion, 2)
            }
        }

    @staticmethod
    def generate_excel_report(db: Session, report_date: date) -> bytes:
        report = ReportService.get_daily_report(db, report_date)

        wb = Workbook()

        ws1 = wb.active
        ws1.title = "资源利用率"
        ws1.append(["楼层", "资源类型", "总资源数", "总时长(小时)", "已预订时长(小时)", "利用率(%)", "收入(元)"])
        for fu in report["floor_utilizations"]:
            ws1.append([
                fu["floor"],
                fu["resource_type"],
                fu["total_resources"],
                fu["total_hours"],
                fu["booked_hours"],
                round(fu["utilization_rate"] * 100, 2),
                fu["revenue"]
            ])

        ws2 = wb.create_sheet("工单统计")
        ws2.append(["统计项", "数值"])
        stats = report["work_order_stats"]
        ws2.append(["总工单数", stats["total_orders"]])
        ws2.append(["已完成数", stats["completed_orders"]])
        ws2.append(["平均响应(分钟)", stats["avg_response_minutes"]])
        ws2.append(["平均完成(分钟)", stats["avg_completion_minutes"]])
        ws2.append(["总收入(元)", report["total_revenue"]])
        ws2.append(["整体利用率(%)", round(report["overall_utilization_rate"] * 100, 2)])

        output = BytesIO()
        wb.save(output)
        return output.getvalue()

    @staticmethod
    def get_report_by_date_range(db: Session, start_date: date, end_date: date) -> List[dict]:
        reports = []
        current = start_date
        while current <= end_date:
            reports.append(ReportService.get_daily_report(db, current))
            current += timedelta(days=1)
        return reports

    @staticmethod
    def generate_booking_report(db, start_date=None, end_date=None):
        return {}

    @staticmethod
    def generate_payment_report(db, start_date=None, end_date=None):
        return {}

    @staticmethod
    def generate_equipment_report(db, start_date=None, end_date=None):
        return {}
