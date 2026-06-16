from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas import (
    MemberResponse, MemberListResponse, MemberUpdate,
    BookingListResponse, ResourceResponse, Token
)
from app.services import MemberService, BookingService
from app.deps import get_current_admin
from app.models import Admin, MemberLevel, BookingStatus
from app.utils import verify_password, create_access_token
from typing import Optional
from datetime import datetime
from pydantic import BaseModel

router = APIRouter(prefix="/admin", tags=["管理员"])


class AdminLogin(BaseModel):
    username: str
    password: str


@router.post("/login", response_model=Token, summary="管理员登录")
def admin_login(login_data: AdminLogin, db: Session = Depends(get_db)):
    admin = db.query(Admin).filter(Admin.username == login_data.username).first()
    if not admin or not admin.is_active:
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    if not verify_password(login_data.password, admin.password_hash):
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    access_token = create_access_token(admin.id, "admin")
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/members", response_model=MemberListResponse, summary="会员列表")
def list_members(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    level: Optional[MemberLevel] = None,
    keyword: Optional[str] = None,
    current_admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    items, total = MemberService.list_members(db, page, page_size, level, keyword)
    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.get("/members/{member_id}", response_model=MemberResponse, summary="会员详情")
def get_member(
    member_id: int,
    current_admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    member = MemberService.get_member_by_id(db, member_id)
    if not member:
        raise HTTPException(status_code=404, detail="会员不存在")
    return member


@router.put("/members/{member_id}", response_model=MemberResponse, summary="更新会员信息")
def update_member(
    member_id: int,
    update_data: MemberUpdate,
    current_admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    member = MemberService.update_member(db, member_id, update_data)
    if not member:
        raise HTTPException(status_code=404, detail="会员不存在")
    return member


@router.get("/bookings", response_model=BookingListResponse, summary="所有预订列表")
def list_all_bookings(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    member_id: Optional[int] = None,
    resource_id: Optional[int] = None,
    status: Optional[BookingStatus] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    start_dt = datetime.fromisoformat(start_date) if start_date else None
    end_dt = datetime.fromisoformat(end_date) if end_date else None

    items, total = BookingService.list_bookings(
        db, page, page_size, member_id, resource_id, status, start_dt, end_dt
    )
    result = []
    for booking in items:
        booking_dict = booking.__dict__.copy()
        booking_dict["resource_name"] = booking.resource.name if booking.resource else ""
        result.append(booking_dict)
    return {"items": result, "total": total, "page": page, "page_size": page_size}
