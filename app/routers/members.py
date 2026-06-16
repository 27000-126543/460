from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas import (
    MemberCreate, MemberUpdate, MemberResponse, MemberListResponse,
    MemberLogin, Token, NotificationResponse
)
from app.services import MemberService
from app.deps import get_current_member
from app.utils import create_access_token
from app.models import Member, Notification

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


@router.get("/notifications", response_model=list[NotificationResponse], summary="获取我的通知")
def get_my_notifications(
    page: int = 1,
    page_size: int = 20,
    current_member: Member = Depends(get_current_member),
    db: Session = Depends(get_db)
):
    notifications = db.query(Notification).filter(
        Notification.member_id == current_member.id
    ).order_by(Notification.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return notifications


@router.post("/notifications/{notification_id}/read", summary="标记通知已读")
def mark_notification_read(
    notification_id: int,
    current_member: Member = Depends(get_current_member),
    db: Session = Depends(get_db)
):
    notification = db.query(Notification).filter(
        Notification.id == notification_id,
        Notification.member_id == current_member.id
    ).first()
    if not notification:
        raise HTTPException(status_code=404, detail="通知不存在")
    notification.is_read = True
    db.commit()
    return {"message": "已标记为已读"}
