from sqlalchemy.orm import Session
from app.models import Payment, PaymentStatus, Member
from app.services.member_service import MemberService
from app.services.notification_service import notify_payment_completed, notify_balance_insufficient
from datetime import datetime
from typing import Optional, List, Tuple


class PaymentService:
    @staticmethod
    def create_payment(
        db: Session,
        member_id: int,
        amount: float,
        booking_id: Optional[int] = None,
        payment_type: str = "balance",
        remark: str = ""
    ) -> Payment:
        payment = Payment(
            booking_id=booking_id,
            member_id=member_id,
            amount=amount,
            status=PaymentStatus.PENDING,
            payment_type=payment_type,
            remark=remark
        )
        db.add(payment)
        db.commit()
        db.refresh(payment)
        return payment

    @staticmethod
    def process_payment(db: Session, payment_id: int, transaction_id: str = "") -> Tuple[bool, str, Optional[Payment]]:
        payment = db.query(Payment).filter(Payment.id == payment_id).first()
        if not payment:
            return False, "支付记录不存在", None
        if payment.status == PaymentStatus.PAID:
            return False, "已支付", None

        member = MemberService.get_member_by_id(db, payment.member_id)
        if not member:
            return False, "会员不存在", None

        if member.balance < payment.amount:
            return False, "余额不足", None

        member.balance -= payment.amount
        payment.status = PaymentStatus.PAID
        payment.transaction_id = transaction_id
        payment.paid_at = datetime.now()

        db.commit()
        db.refresh(payment)

        notify_payment_completed(db, payment, member)

        return True, "支付成功", payment

    @staticmethod
    def recharge(db: Session, member_id: int, amount: float, payment_type: str = "alipay") -> Tuple[bool, str, Optional[Payment]]:
        if amount <= 0:
            return False, "充值金额必须大于0", None

        member = MemberService.get_member_by_id(db, member_id)
        if not member:
            return False, "会员不存在", None

        member.balance += amount

        payment = Payment(
            member_id=member_id,
            amount=amount,
            status=PaymentStatus.PAID,
            payment_type=payment_type,
            remark="账户充值",
            paid_at=datetime.now()
        )
        db.add(payment)
        db.commit()
        db.refresh(payment)

        return True, "充值成功", payment

    @staticmethod
    def get_payment_by_id(db: Session, payment_id: int) -> Optional[Payment]:
        return db.query(Payment).filter(Payment.id == payment_id).first()

    @staticmethod
    def list_payments(
        db: Session,
        page: int = 1,
        page_size: int = 20,
        member_id: Optional[int] = None,
        status: Optional[PaymentStatus] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Tuple[List[Payment], int]:
        query = db.query(Payment)
        if member_id:
            query = query.filter(Payment.member_id == member_id)
        if status:
            query = query.filter(Payment.status == status)
        if start_date:
            query = query.filter(Payment.created_at >= start_date)
        if end_date:
            query = query.filter(Payment.created_at <= end_date)

        total = query.count()
        items = query.order_by(Payment.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
        return items, total

    @staticmethod
    def refund(db: Session, payment_id: int, reason: str = "") -> Tuple[bool, str]:
        payment = db.query(Payment).filter(Payment.id == payment_id).first()
        if not payment:
            return False, "支付记录不存在"
        if payment.status != PaymentStatus.PAID:
            return False, "只有已支付订单可退款"

        member = MemberService.get_member_by_id(db, payment.member_id)
        if not member:
            return False, "会员不存在"

        member.balance += payment.amount
        payment.status = PaymentStatus.REFUNDED
        payment.remark = f"{payment.remark} - 退款原因: {reason}" if payment.remark else f"退款原因: {reason}"

        db.commit()
        return True, "退款成功"
