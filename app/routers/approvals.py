from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas import ApprovalResponse, ApprovalAction, BookingResponse
from app.services import ApprovalService
from app.deps import get_current_admin
from app.models import Admin, ApprovalStatus
from typing import Optional

router = APIRouter(prefix="/approvals", tags=["审批管理"])


@router.get("", response_model=list[ApprovalResponse], summary="审批列表")
def list_approvals(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[ApprovalStatus] = None,
    current_admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    items, total = ApprovalService.list_approvals(db, page, page_size, status, current_admin.level)
    return items


@router.get("/{approval_id}", response_model=ApprovalResponse, summary="审批详情")
def get_approval(
    approval_id: int,
    current_admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    approval = ApprovalService.get_approval_by_id(db, approval_id)
    if not approval:
        raise HTTPException(status_code=404, detail="审批记录不存在")
    return approval


@router.post("/{approval_id}/approve", summary="通过审批")
def approve_booking(
    approval_id: int,
    action: ApprovalAction,
    current_admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    approval = ApprovalService.get_approval_by_id(db, approval_id)
    if not approval:
        raise HTTPException(status_code=404, detail="审批记录不存在")

    action_value = action.action or "approve"
    if action_value != "approve":
        raise HTTPException(status_code=400, detail="操作类型不匹配")

    success, message = ApprovalService.approve_booking(
        db, approval.booking_id, current_admin, action.remark or ""
    )
    if not success:
        raise HTTPException(status_code=400, detail=message)
    return {"message": message}


@router.post("/{approval_id}/reject", summary="拒绝审批")
def reject_booking(
    approval_id: int,
    action: ApprovalAction,
    current_admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    approval = ApprovalService.get_approval_by_id(db, approval_id)
    if not approval:
        raise HTTPException(status_code=404, detail="审批记录不存在")

    action_value = action.action or "reject"
    if action_value != "reject":
        raise HTTPException(status_code=400, detail="操作类型不匹配")

    if not action.remark:
        raise HTTPException(status_code=400, detail="拒绝原因不能为空")

    success, message = ApprovalService.reject_booking(
        db, approval.booking_id, current_admin, action.remark
    )
    if not success:
        raise HTTPException(status_code=400, detail=message)
    return {"message": message}
