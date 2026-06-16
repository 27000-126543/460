from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas import (
    BookingCreate, BookingResponse, BookingListResponse,
    BookingActionResponse, BookingRecommendRequest, ResourceResponse
)
from app.services import BookingService, MemberService
from app.deps import get_current_member
from app.models import Member, BookingStatus, ResourceType
from typing import Optional
from datetime import datetime

router = APIRouter(prefix="/bookings", tags=["预订管理"])


@router.post("", response_model=BookingActionResponse, summary="创建预订")
def create_booking(
    booking_data: BookingCreate,
    current_member: Member = Depends(get_current_member),
    db: Session = Depends(get_db)
):
    success, message, booking = BookingService.create_booking(db, current_member.id, booking_data)
    if not success:
        return BookingActionResponse(success=False, message=message)
    return BookingActionResponse(success=True, message=message, booking=booking)


@router.get("", response_model=BookingListResponse, summary="我的预订列表")
def list_my_bookings(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[BookingStatus] = None,
    current_member: Member = Depends(get_current_member),
    db: Session = Depends(get_db)
):
    items, total = BookingService.list_bookings(
        db, page, page_size, member_id=current_member.id, status=status
    )
    result = []
    for booking in items:
        booking_dict = booking.__dict__.copy()
        booking_dict["resource_name"] = booking.resource.name if booking.resource else ""
        result.append(booking_dict)
    return {"items": result, "total": total, "page": page, "page_size": page_size}


@router.get("/{booking_id}", response_model=BookingResponse, summary="预订详情")
def get_booking(
    booking_id: int,
    current_member: Member = Depends(get_current_member),
    db: Session = Depends(get_db)
):
    booking = BookingService.get_booking_by_id(db, booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="预订不存在")
    if booking.member_id != current_member.id:
        raise HTTPException(status_code=403, detail="无权查看他人预订")

    booking_dict = booking.__dict__.copy()
    booking_dict["resource_name"] = booking.resource.name if booking.resource else ""
    return booking_dict


@router.post("/{booking_id}/cancel", response_model=BookingActionResponse, summary="取消预订")
def cancel_booking(
    booking_id: int,
    current_member: Member = Depends(get_current_member),
    db: Session = Depends(get_db)
):
    success, message = BookingService.cancel_booking(db, booking_id, current_member.id)
    if not success:
        return BookingActionResponse(success=False, message=message)
    booking = BookingService.get_booking_by_id(db, booking_id)
    return BookingActionResponse(success=True, message=message, booking=booking)


@router.post("/{booking_id}/check-in", response_model=BookingActionResponse, summary="签到")
def check_in(
    booking_id: int,
    current_member: Member = Depends(get_current_member),
    db: Session = Depends(get_db)
):
    booking = BookingService.get_booking_by_id(db, booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="预订不存在")
    if booking.member_id != current_member.id:
        raise HTTPException(status_code=403, detail="无权操作")

    success, message = BookingService.check_in(db, booking_id)
    if not success:
        return BookingActionResponse(success=False, message=message)
    booking = BookingService.get_booking_by_id(db, booking_id)
    return BookingActionResponse(success=True, message=message, booking=booking)


@router.post("/{booking_id}/check-out", response_model=BookingActionResponse, summary="签退结算")
def check_out(
    booking_id: int,
    current_member: Member = Depends(get_current_member),
    db: Session = Depends(get_db)
):
    booking = BookingService.get_booking_by_id(db, booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="预订不存在")
    if booking.member_id != current_member.id:
        raise HTTPException(status_code=403, detail="无权操作")

    success, message, amount = BookingService.check_out(db, booking_id)
    if not success:
        return BookingActionResponse(success=False, message=message)
    booking = BookingService.get_booking_by_id(db, booking_id)
    return BookingActionResponse(success=True, message=message, booking=booking)


@router.post("/recommend", response_model=list[ResourceResponse], summary="推荐可用资源")
def recommend_resources(
    request: BookingRecommendRequest,
    db: Session = Depends(get_db)
):
    resources = BookingService.recommend_resources(
        db, request.type.value, request.start_time, request.end_time,
        request.floor, request.capacity
    )
    return resources
