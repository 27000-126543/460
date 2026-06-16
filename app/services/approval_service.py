from sqlalchemy.orm import Session
from app.models import Approval, ApprovalStatus, Booking, BookingStatus, Admin, MemberLevel
from app.services.notification_service import notify_booking_approved, notify_booking_rejected, notify_approval_escalated
from app.config import settings
from datetime import datetime, timedelta
from typing import Optional, List, Tuple


class ApprovalService:
    @staticmethod
    def get_approval_by_id(db: Session, approval_id: int) -> Optional[Approval]:
        return db.query(Approval).filter(Approval.id == approval_id).first()

    @staticmethod
    def get_approval_by_booking_id(db: Session, booking_id: int) -> Optional[Approval]:
        return db.query(Approval).filter(Approval.booking_id == booking_id).first()

    @staticmethod
    def list_approvals(
        db: Session,
        page: int = 1,
        page_size: int = 20,
        status: Optional[ApprovalStatus] = None,
        approver_level: Optional[int] = None
    ) -> Tuple[List[Approval], int]:
        query = db.query(Approval)
        if status:
            query = query.filter(Approval.status == status)
        if approver_level:
            query = query.filter(Approval.approver_level == approver_level)

        total = query.count()
        items = query.order_by(Approval.submitted_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
        return items, total

    @staticmethod
    def approve_booking(db: Session, booking_id: int, admin: Admin, remark: str = "") -> Tuple[bool, str]:
        approval = ApprovalService.get_approval_by_booking_id(db, booking_id)
        if not approval:
            return False, "审批记录不存在"

        if approval.status != ApprovalStatus.PENDING and approval.status != ApprovalStatus.ESCALATED:
            return False, "该审批已处理"

        if admin.level < approval.approver_level:
            return False, "权限不足，无法处理该审批"

        booking = db.query(Booking).filter(Booking.id == booking_id).first()
        if not booking:
            return False, "预订不存在"

        approval.status = ApprovalStatus.APPROVED
        approval.approver_id = admin.id
        approval.processed_at = datetime.now()
        approval.remark = remark

        booking.status = BookingStatus.APPROVED

        db.commit()

        from app.models import Member
        member = db.query(Member).filter(Member.id == booking.member_id).first()
        if member:
            notify_booking_approved(db, booking, member)

        return True, "审核通过"

    @staticmethod
    def reject_booking(db: Session, booking_id: int, admin: Admin, reason: str) -> Tuple[bool, str]:
        approval = ApprovalService.get_approval_by_booking_id(db, booking_id)
        if not approval:
            return False, "审批记录不存在"

        if approval.status != ApprovalStatus.PENDING and approval.status != ApprovalStatus.ESCALATED:
            return False, "该审批已处理"

        if admin.level < approval.approver_level:
            return False, "权限不足，无法处理该审批"

        booking = db.query(Booking).filter(Booking.id == booking_id).first()
        if not booking:
            return False, "预订不存在"

        approval.status = ApprovalStatus.REJECTED
        approval.approver_id = admin.id
        approval.processed_at = datetime.now()
        approval.remark = reason

        booking.status = BookingStatus.REJECTED
        booking.rejection_reason = reason

        db.commit()

        from app.models import Member
        member = db.query(Member).filter(Member.id == booking.member_id).first()
        if member:
            notify_booking_rejected(db, booking, member, reason)

        return True, "已拒绝"

    @staticmethod
    def check_timeout_and_escalate(db: Session):
        timeout_threshold = datetime.now() - timedelta(hours=settings.APPROVAL_TIMEOUT_HOURS)
        pending_approvals = db.query(Approval).filter(
            Approval.status == ApprovalStatus.PENDING,
            Approval.submitted_at < timeout_threshold
        ).all()

        for approval in pending_approvals:
            booking = db.query(Booking).filter(Booking.id == approval.booking_id).first()
            if not booking:
                continue

            next_level = approval.approver_level + 1
            max_level = db.query(Admin.level).order_by(Admin.level.desc()).first()
            max_level_value = max_level[0] if max_level else 3

            if next_level <= max_level_value:
                approval.status = ApprovalStatus.ESCALATED
                approval.approver_level = next_level
                approval.escalated_at = datetime.now()
                notify_approval_escalated(db, booking, next_level)
            else:
                approval.status = ApprovalStatus.APPROVED
                approval.approver_level = max_level_value
                approval.processed_at = datetime.now()
                approval.remark = "超时自动通过"
                booking.status = BookingStatus.APPROVED

                from app.models import Member
                member = db.query(Member).filter(Member.id == booking.member_id).first()
                if member:
                    notify_booking_approved(db, booking, member)

        db.commit()
        return len(pending_approvals)
