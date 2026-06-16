from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime
from app.models import MemberLevel, ResourceType, ResourceStatus, BookingStatus, ApprovalStatus, PaymentStatus


class MemberBase(BaseModel):
    name: str = Field(..., max_length=100)
    email: EmailStr
    phone: str = Field(..., max_length=20)
    level: Optional[MemberLevel] = MemberLevel.BASIC
    credit_limit: Optional[float] = 1000.0


class MemberCreate(MemberBase):
    password: str = Field(..., min_length=6, max_length=100)


class MemberUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    level: Optional[MemberLevel] = None
    credit_limit: Optional[float] = None
    balance: Optional[float] = None
    is_active: Optional[bool] = None


class MemberLogin(BaseModel):
    email: EmailStr
    password: str


class MemberResponse(MemberBase):
    id: int
    balance: float
    default_count: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class MemberListResponse(BaseModel):
    items: list[MemberResponse]
    total: int
    page: int
    page_size: int


class ResourceBase(BaseModel):
    name: str = Field(..., max_length=100)
    type: ResourceType
    floor: int
    area: Optional[str] = None
    capacity: Optional[int] = 1
    hourly_rate: float
    status: Optional[ResourceStatus] = ResourceStatus.AVAILABLE
    description: Optional[str] = None


class ResourceCreate(ResourceBase):
    pass


class ResourceUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[ResourceType] = None
    floor: Optional[int] = None
    area: Optional[str] = None
    capacity: Optional[int] = None
    hourly_rate: Optional[float] = None
    status: Optional[ResourceStatus] = None
    description: Optional[str] = None


class ResourceResponse(ResourceBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class ResourceListResponse(BaseModel):
    items: list[ResourceResponse]
    total: int
    page: int
    page_size: int


class BookingCreate(BaseModel):
    resource_id: int
    start_time: datetime
    end_time: datetime


class BookingRecommendRequest(BaseModel):
    type: ResourceType
    start_time: datetime
    end_time: datetime
    floor: Optional[int] = None
    capacity: Optional[int] = None


class BookingUpdate(BaseModel):
    status: Optional[BookingStatus] = None
    actual_start_time: Optional[datetime] = None
    actual_end_time: Optional[datetime] = None


class BookingResponse(BaseModel):
    id: int
    member_id: int
    resource_id: int
    resource_name: Optional[str] = None
    start_time: datetime
    end_time: datetime
    actual_start_time: Optional[datetime] = None
    actual_end_time: Optional[datetime] = None
    status: BookingStatus
    total_amount: float
    actual_amount: Optional[float] = None
    rejection_reason: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class BookingListResponse(BaseModel):
    items: list[BookingResponse]
    total: int
    page: int
    page_size: int


class BookingActionResponse(BaseModel):
    success: bool
    message: str
    booking: Optional[BookingResponse] = None


class ApprovalResponse(BaseModel):
    id: int
    booking_id: int
    status: ApprovalStatus
    approver_level: int
    submitted_at: datetime
    processed_at: Optional[datetime] = None
    escalated_at: Optional[datetime] = None
    remark: Optional[str] = None

    class Config:
        from_attributes = True


class ApprovalAction(BaseModel):
    action: str
    remark: Optional[str] = None


class PaymentResponse(BaseModel):
    id: int
    booking_id: Optional[int] = None
    member_id: int
    amount: float
    status: PaymentStatus
    payment_type: Optional[str] = None
    transaction_id: Optional[str] = None
    remark: Optional[str] = None
    created_at: datetime
    paid_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class RechargeRequest(BaseModel):
    amount: float
    payment_type: str = "balance"


class NotificationResponse(BaseModel):
    id: int
    type: str
    title: str
    content: str
    is_read: bool
    created_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    user_id: Optional[int] = None
    user_type: Optional[str] = None


class APIResponse(BaseModel):
    code: int = 0
    message: str = "success"
    data: Optional[dict] = None
