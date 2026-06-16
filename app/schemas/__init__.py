from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from app.models import MemberLevel, ResourceType, ResourceStatus, BookingStatus, ApprovalStatus, PaymentStatus
from app.models import EquipmentType, EquipmentStatus, FaultType, FaultSeverity, WorkOrderStatus


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
    booking_restricted: bool
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
    action: Optional[str] = None
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


class NotificationListResponse(BaseModel):
    items: list[NotificationResponse]
    total: int
    page: int
    page_size: int


class MarkReadBatchRequest(BaseModel):
    ids: list[int]


class UnreadCountResponse(BaseModel):
    unread_count: int


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


class EquipmentBase(BaseModel):
    name: str = Field(..., max_length=100)
    type: EquipmentType
    floor: int
    area: Optional[str] = None
    location: Optional[str] = None
    status: Optional[EquipmentStatus] = EquipmentStatus.ONLINE
    resource_id: Optional[int] = None
    temp_threshold: Optional[float] = 80.0
    current_threshold: Optional[float] = 15.0
    description: Optional[str] = None


class EquipmentCreate(EquipmentBase):
    pass


class EquipmentUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[EquipmentType] = None
    floor: Optional[int] = None
    area: Optional[str] = None
    location: Optional[str] = None
    status: Optional[EquipmentStatus] = None
    resource_id: Optional[int] = None
    temp_threshold: Optional[float] = None
    current_threshold: Optional[float] = None
    description: Optional[str] = None


class EquipmentResponse(EquipmentBase):
    id: int
    fault_count: int = 0
    is_frequent_fault: bool = False
    created_at: datetime

    class Config:
        from_attributes = True


class EquipmentListResponse(BaseModel):
    items: list[EquipmentResponse]
    total: int
    page: int
    page_size: int


class EquipmentDataReport(BaseModel):
    equipment_id: int
    temperature: Optional[float] = None
    current: Optional[float] = None
    is_online: Optional[bool] = True
    raw_data: Optional[str] = None


class EquipmentDataResponse(BaseModel):
    id: int
    equipment_id: int
    temperature: Optional[float] = None
    current: Optional[float] = None
    is_online: bool
    is_anomaly: bool
    anomaly_details: Optional[str] = None
    reported_at: datetime


class AnomalyDetail(BaseModel):
    type: str
    message: str


class AnomalyReportResponse(BaseModel):
    anomaly_detected: bool
    work_order_id: Optional[int] = None
    details: List[AnomalyDetail] = []


class EngineerBase(BaseModel):
    name: str = Field(..., max_length=100)
    phone: str = Field(..., max_length=20)
    specialty: Optional[str] = None
    floor_range: Optional[str] = None
    is_available: Optional[bool] = True


class EngineerCreate(EngineerBase):
    pass


class EngineerUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    specialty: Optional[str] = None
    floor_range: Optional[str] = None
    is_available: Optional[bool] = None


class EngineerResponse(EngineerBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class WorkOrderResponse(BaseModel):
    id: int
    equipment_id: int
    equipment_name: Optional[str] = None
    engineer_id: Optional[int] = None
    engineer_name: Optional[str] = None
    fault_type: FaultType
    severity: FaultSeverity
    status: WorkOrderStatus
    description: Optional[str] = None
    floor: int
    area: Optional[str] = None
    location: Optional[str] = None
    escalation_level: int
    assigned_at: Optional[datetime] = None
    accepted_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    escalated_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class WorkOrderListResponse(BaseModel):
    items: list[WorkOrderResponse]
    total: int
    page: int
    page_size: int


class WorkOrderAssignRequest(BaseModel):
    engineer_id: int


class WorkOrderUpdateRequest(BaseModel):
    remark: Optional[str] = None
    status: Optional[WorkOrderStatus] = None


class FloorUtilization(BaseModel):
    floor: int
    resource_type: ResourceType
    total_resources: int
    total_hours: float
    booked_hours: float
    utilization_rate: float
    revenue: float


class WorkOrderStats(BaseModel):
    total_orders: int
    completed_orders: int
    avg_response_minutes: float
    avg_completion_minutes: float


class DailyReport(BaseModel):
    report_date: str
    data_available: bool
    floor_utilizations: List[FloorUtilization]
    total_revenue: float
    overall_utilization_rate: float
    work_order_stats: WorkOrderStats


class WeeklyReport(BaseModel):
    year: int
    week: int
    data_available: bool
    floor_utilizations: List[FloorUtilization]
    total_revenue: float
    overall_utilization_rate: float
    work_order_stats: WorkOrderStats


class MonthlyReport(BaseModel):
    year: int
    month: int
    data_available: bool
    floor_utilizations: List[FloorUtilization]
    total_revenue: float
    overall_utilization_rate: float
    work_order_stats: WorkOrderStats


class ReportListResponse(BaseModel):
    reports: List[DailyReport]


class TrendPoint(BaseModel):
    period: str
    value: float


class TrendResponse(BaseModel):
    start_date: str
    end_date: str
    period: str
    data_points: List[TrendPoint]


class FloorComparison(BaseModel):
    floor: int
    total_resources: int
    total_hours: float
    booked_hours: float
    utilization_rate: float
    revenue: float
    work_order_count: int


class ResourceTypeComparison(BaseModel):
    resource_type: ResourceType
    total_resources: int
    total_hours: float
    booked_hours: float
    utilization_rate: float
    revenue: float
    work_order_count: int


class ComparisonResponse(BaseModel):
    report_date: str
    floor_comparisons: List[FloorComparison]
    resource_type_comparisons: List[ResourceTypeComparison]


class MaintenanceRecordCreate(BaseModel):
    work_order_id: Optional[int] = None
    result: str
    materials_used: Optional[str] = None
    photo_url: Optional[str] = None
    needs_recheck: Optional[bool] = False
    recheck_date: Optional[datetime] = None
    remark: Optional[str] = None


class MaintenanceRecordResponse(BaseModel):
    id: int
    work_order_id: int
    equipment_id: int
    engineer_id: int
    result: str
    materials_used: Optional[str] = None
    photo_url: Optional[str] = None
    needs_recheck: bool
    recheck_date: Optional[datetime] = None
    remark: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class MaintenanceRecordListResponse(BaseModel):
    items: list[MaintenanceRecordResponse]
    total: int
    page: int
    page_size: int
