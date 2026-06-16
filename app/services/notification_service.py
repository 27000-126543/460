from sqlalchemy.orm import Session
from app.models import Notification, Member, Booking, Payment
from datetime import datetime
from typing import Optional


def create_notification(
    db: Session,
    member_id: Optional[int] = None,
    admin_id: Optional[int] = None,
    notification_type: str = "system",
    title: str = "",
    content: str = ""
) -> Notification:
    notification = Notification(
        member_id=member_id,
        admin_id=admin_id,
        type=notification_type,
        title=title,
        content=content
    )
    db.add(notification)
    db.commit()
    db.refresh(notification)
    _send_notification(notification)
    return notification


def _send_notification(notification: Notification):
    print(f"[通知推送] 类型:{notification.type} | 标题:{notification.title} | 内容:{notification.content}")


def notify_booking_created(db: Session, booking: Booking, member: Member):
    create_notification(
        db,
        member_id=member.id,
        notification_type="booking",
        title="预订申请已提交",
        content=f"您的{booking.resource.type.value}预订申请已提交，预订号：{booking.id}，请等待审核。"
    )


def notify_booking_approved(db: Session, booking: Booking, member: Member):
    create_notification(
        db,
        member_id=member.id,
        notification_type="booking",
        title="预订已通过审核",
        content=f"您的预订（编号：{booking.id}）已通过审核，请按时使用。"
    )


def notify_booking_rejected(db: Session, booking: Booking, member: Member, reason: str):
    create_notification(
        db,
        member_id=member.id,
        notification_type="booking",
        title="预订未通过审核",
        content=f"您的预订（编号：{booking.id}）未通过审核，原因：{reason}"
    )


def notify_payment_completed(db: Session, payment: Payment, member: Member):
    create_notification(
        db,
        member_id=member.id,
        notification_type="payment",
        title="费用结算完成",
        content=f"您的订单（编号：{payment.id}）已结算，金额：¥{payment.amount}"
    )


def notify_balance_insufficient(db: Session, member: Member):
    create_notification(
        db,
        member_id=member.id,
        notification_type="payment",
        title="余额不足提醒",
        content=f"您的账户余额不足（当前余额：¥{member.balance}），请及时充值以继续使用预订服务。"
    )


def notify_admin_new_booking(db: Session, booking: Booking, admin_id: int):
    create_notification(
        db,
        admin_id=admin_id,
        notification_type="approval",
        title="新的预订待审核",
        content=f"有新的预订申请（编号：{booking.id}）待您审核，请及时处理。"
    )


def notify_approval_escalated(db: Session, booking: Booking, admin_level: int):
    from app.models import Admin
    admins = db.query(Admin).filter(Admin.level >= admin_level, Admin.is_active == True).all()
    for admin in admins:
        create_notification(
            db,
            admin_id=admin.id,
            notification_type="approval",
            title="预订审核已升级",
            content=f"预订（编号：{booking.id}）审核超时，已升级至{admin_level}级管理员处理。"
        )
