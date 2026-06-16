from sqlalchemy.orm import Session
from app.models import Booking, BookingStatus, MemberLevel, Approval, ApprovalStatus, Resource
from app.schemas import BookingCreate
from app.services.resource_service import ResourceService
from app.services.member_service import MemberService
from app.services.notification_service import (
    notify_booking_created,
    notify_booking_approved,
    notify_booking_rejected,
    notify_admin_new_booking
)
from app.utils import calculate_hours, calculate_cost
from datetime import datetime
from typing import Optional, List, Tuple


class BookingService:
    @staticmethod
    def create_booking(db: Session, member_id: int, booking_data: BookingCreate) -> Tuple[bool, str, Optional[Booking]]:
        member = MemberService.get_member_by_id(db, member_id)
        if not member:
            return False, "会员不存在", None

        if booking_data.start_time >= booking_data.end_time:
            return False, "结束时间必须晚于开始时间", None

        if booking_data.start_time < datetime.now():
            return False, "不能预订过去的时间", None

        resource = ResourceService.get_resource_by_id(db, booking_data.resource_id)
        if not resource:
            return False, "资源不存在", None

        if resource.status.value != "available":
            return False, "资源当前不可用", None

        if not ResourceService.is_resource_available(
            db, booking_data.resource_id,
            booking_data.start_time, booking_data.end_time
        ):
            return False, "该时段资源已被预订", None

        hours = calculate_hours(booking_data.start_time, booking_data.end_time)
        total_amount = calculate_cost(resource.hourly_rate, hours)

        can_book, reason = MemberService.check_booking_permission(db, member_id, total_amount)
        if not can_book:
            return False, reason, None

        booking = Booking(
            member_id=member_id,
            resource_id=booking_data.resource_id,
            start_time=booking_data.start_time,
            end_time=booking_data.end_time,
            total_amount=total_amount
        )

        is_high_level = member.level in [MemberLevel.GOLD, MemberLevel.PLATINUM]

        if is_high_level:
            booking.status = BookingStatus.APPROVED
        else:
            booking.status = BookingStatus.PENDING_APPROVAL

        db.add(booking)
        db.flush()

        if is_high_level:
            approval = Approval(
                booking_id=booking.id,
                status=ApprovalStatus.APPROVED,
                approver_level=0,
                processed_at=datetime.now()
            )
        else:
            approval = Approval(
                booking_id=booking.id,
                status=ApprovalStatus.PENDING,
                approver_level=1
            )
        db.add(approval)
        db.commit()
        db.refresh(booking)

        notify_booking_created(db, booking, member)

        if not is_high_level:
            from app.models import Admin
            admins = db.query(Admin).filter(Admin.level == 1, Admin.is_active == True).all()
            for admin in admins:
                notify_admin_new_booking(db, booking, admin.id)
        else:
            notify_booking_approved(db, booking, member)

        return True, "预订成功", booking

    @staticmethod
    def get_booking_by_id(db: Session, booking_id: int) -> Optional[Booking]:
        return db.query(Booking).filter(Booking.id == booking_id).first()

    @staticmethod
    def list_bookings(
        db: Session,
        page: int = 1,
        page_size: int = 20,
        member_id: Optional[int] = None,
        resource_id: Optional[int] = None,
        status: Optional[BookingStatus] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Tuple[List[Booking], int]:
        query = db.query(Booking)
        if member_id:
            query = query.filter(Booking.member_id == member_id)
        if resource_id:
            query = query.filter(Booking.resource_id == resource_id)
        if status:
            query = query.filter(Booking.status == status)
        if start_date:
            query = query.filter(Booking.start_time >= start_date)
        if end_date:
            query = query.filter(Booking.start_time <= end_date)

        total = query.count()
        items = query.order_by(Booking.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
        return items, total

    @staticmethod
    def cancel_booking(db: Session, booking_id: int, member_id: int) -> Tuple[bool, str]:
        booking = BookingService.get_booking_by_id(db, booking_id)
        if not booking:
            return False, "预订不存在"
        if booking.member_id != member_id:
            return False, "无权取消他人预订"
        if booking.status in [BookingStatus.CANCELLED, BookingStatus.COMPLETED, BookingStatus.REJECTED]:
            return False, "该预订无法取消"

        booking.status = BookingStatus.CANCELLED
        db.commit()
        return True, "预订已取消"

    @staticmethod
    def check_in(db: Session, booking_id: int) -> Tuple[bool, str]:
        booking = BookingService.get_booking_by_id(db, booking_id)
        if not booking:
            return False, "预订不存在"
        if booking.status != BookingStatus.APPROVED:
            return False, "只有已通过审核的预订才能签到"

        booking.actual_start_time = datetime.now()
        db.commit()
        return True, "签到成功"

    @staticmethod
    def check_out(db: Session, booking_id: int) -> Tuple[bool, str, Optional[float]]:
        booking = BookingService.get_booking_by_id(db, booking_id)
        if not booking:
            return False, "预订不存在", None
        if not booking.actual_start_time:
            return False, "尚未签到", None
        if booking.status == BookingStatus.COMPLETED:
            return False, "已结算", None

        actual_end = datetime.now()
        booking.actual_end_time = actual_end
        booking.status = BookingStatus.COMPLETED

        hours = calculate_hours(booking.actual_start_time, actual_end)
        resource = ResourceService.get_resource_by_id(db, booking.resource_id)
        actual_amount = calculate_cost(resource.hourly_rate, hours) if resource else booking.total_amount
        booking.actual_amount = min(actual_amount, booking.total_amount)

        member = MemberService.get_member_by_id(db, booking.member_id)
        if member:
            if member.balance >= booking.actual_amount:
                member.balance -= booking.actual_amount
                from app.models import Payment, PaymentStatus
                payment = Payment(
                    booking_id=booking.id,
                    member_id=member.id,
                    amount=booking.actual_amount,
                    status=PaymentStatus.PAID,
                    payment_type="balance",
                    paid_at=datetime.now()
                )
                db.add(payment)
                from app.services.notification_service import notify_payment_completed
                notify_payment_completed(db, payment, member)
            else:
                from app.services.notification_service import notify_balance_insufficient
                notify_balance_insufficient(db, member)

        db.commit()
        db.refresh(booking)
        return True, "结算完成", booking.actual_amount

    @staticmethod
    def recommend_resources(
        db: Session,
        resource_type: str,
        start_time: datetime,
        end_time: datetime,
        floor: Optional[int] = None,
        capacity: Optional[int] = None
    ) -> List[Resource]:
        from app.models import ResourceType
        type_enum = ResourceType(resource_type)
        return ResourceService.find_available_resources(
            db, type_enum, start_time, end_time, floor, capacity
        )
