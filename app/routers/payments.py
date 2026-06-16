from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas import PaymentResponse, RechargeRequest
from app.services import PaymentService, MemberService
from app.deps import get_current_member
from app.models import Member, PaymentStatus
from typing import Optional

router = APIRouter(prefix="/payments", tags=["支付管理"])


@router.post("/recharge", summary="账户充值")
def recharge(
    recharge_data: RechargeRequest,
    current_member: Member = Depends(get_current_member),
    db: Session = Depends(get_db)
):
    success, message, payment = PaymentService.recharge(
        db, current_member.id, recharge_data.amount, recharge_data.payment_type
    )
    if not success:
        raise HTTPException(status_code=400, detail=message)
    return {
        "success": True,
        "message": message,
        "payment": payment,
        "balance": MemberService.get_member_by_id(db, current_member.id).balance
    }


@router.get("", response_model=list[PaymentResponse], summary="我的支付记录")
def list_my_payments(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[PaymentStatus] = None,
    current_member: Member = Depends(get_current_member),
    db: Session = Depends(get_db)
):
    items, total = PaymentService.list_payments(
        db, page, page_size, member_id=current_member.id, status=status
    )
    return items


@router.get("/{payment_id}", response_model=PaymentResponse, summary="支付详情")
def get_payment(
    payment_id: int,
    current_member: Member = Depends(get_current_member),
    db: Session = Depends(get_db)
):
    payment = PaymentService.get_payment_by_id(db, payment_id)
    if not payment:
        raise HTTPException(status_code=404, detail="支付记录不存在")
    if payment.member_id != current_member.id:
        raise HTTPException(status_code=403, detail="无权查看")
    return payment
