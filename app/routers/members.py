from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas import (
    MemberCreate, MemberUpdate, MemberResponse, MemberListResponse,
    MemberLogin, Token, NotificationResponse, NotificationListResponse,
    MarkReadBatchRequest, UnreadCountResponse
)
from app.services import MemberService, notification_service
from app.deps import get_current_member
from app.utils import create_access_token
from app.models import Member
from typing import Optional

router = APIRouter(prefix="/members", tags=["会员管理"])


@router.post("/register", response_model=Token, summary="会员注册")
def register(member_data: MemberCreate, db: Session = Depends(get_db)):
    existing = MemberService.get_member_by_email(db, member_data.email)
    if existing:
        raise HTTPException(status_code=400, detail="邮箱已被注册")
    existing_phone = MemberService.get_member_by_phone(db, member_data.phone)
    if existing_phone:
        raise HTTPException(status_code=400, detail="手机号已被注册")

    member = MemberService.create_member(db, member_data)
    access_token = create_access_token(member.id, "member")
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/login", response_model=Token, summary="会员登录")
def login(login_data: MemberLogin, db: Session = Depends(get_db)):
    member = MemberService.authenticate(db, login_data.email, login_data.password)
    if not member:
        raise HTTPException(status_code=401, detail="邮箱或密码错误")
    access_token = create_access_token(member.id, "member")
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=MemberResponse, summary="获取当前会员信息")
def get_profile(current_member: Member = Depends(get_current_member)):
    return current_member


@router.put("/me", response_model=MemberResponse, summary="更新个人信息")
def update_profile(
    update_data: MemberUpdate,
    current_member: Member = Depends(get_current_member),
    db: Session = Depends(get_db)
):
    updated = MemberService.update_member(db, current_member.id, update_data)
    return updated


@router.get("/notifications", response_model=NotificationListResponse, summary="我的通知列表")
def list_member_notifications(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    type: Optional[str] = None,
    is_read: Optional[bool] = None,
    current_member: Member = Depends(get_current_member),
    db: Session = Depends(get_db)
):
    items, total = notification_service.list_member_notifications(
        db, current_member.id, page, page_size, type, is_read
    )
    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.post("/notifications/{notification_id}/read", summary="标记单条通知已读")
def mark_notification_read(
    notification_id: int,
    current_member: Member = Depends(get_current_member),
    db: Session = Depends(get_db)
):
    notification = notification_service.mark_as_read(
        db, notification_id, "member", current_member.id
    )
    if not notification:
        raise HTTPException(status_code=404, detail="通知不存在")
    return {"message": "已标记为已读"}


@router.post("/notifications/read-batch", summary="批量标记通知已读")
def mark_batch_read(
    request: MarkReadBatchRequest,
    current_member: Member = Depends(get_current_member),
    db: Session = Depends(get_db)
):
    count = notification_service.mark_batch_as_read(
        db, request.ids, "member", current_member.id
    )
    return {"message": f"已标记 {count} 条为已读", "count": count}


@router.post("/notifications/read-all", summary="全部标记已读")
def mark_all_read(
    current_member: Member = Depends(get_current_member),
    db: Session = Depends(get_db)
):
    count = notification_service.mark_all_as_read(db, "member", current_member.id)
    return {"message": f"已全部标记为已读", "count": count}


@router.get("/notifications/unread-count", response_model=UnreadCountResponse, summary="未读数量")
def get_unread_count(
    current_member: Member = Depends(get_current_member),
    db: Session = Depends(get_db)
):
    count = notification_service.get_unread_count(db, "member", current_member.id)
    return {"unread_count": count}
