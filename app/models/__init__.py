from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, Float, ForeignKey, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
import enum


class MemberLevel(str, enum.Enum):
    BASIC = "basic"
    SILVER = "silver"
    GOLD = "gold"
    PLATINUM = "platinum"


class ResourceType(str, enum.Enum):
    DESK = "desk"
    MEETING_ROOM = "meeting_room"


class ResourceStatus(str, enum.Enum):
    AVAILABLE = "available"
    OCCUPIED = "occupied"
    MAINTENANCE = "maintenance"


class BookingStatus(str, enum.Enum):
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"
    COMPLETED = "completed"
    EXPIRED = "expired"


class ApprovalStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    ESCALATED = "escalated"


class PaymentStatus(str, enum.Enum):
    PENDING = "pending"
    PAID = "paid"
    REFUNDED = "refunded"


class Member(Base):
    __tablename__ = "members"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, nullable=False, index=True)
    phone = Column(String(20), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    level = Column(Enum(MemberLevel), default=MemberLevel.BASIC, nullable=False)
    credit_limit = Column(Float, default=1000.0, nullable=False)
    balance = Column(Float, default=0.0, nullable=False)
    default_count = Column(Integer, default=0, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    bookings = relationship("Booking", back_populates="member")
    payments = relationship("Payment", back_populates="member")
    notifications = relationship("Notification", back_populates="member")


class Resource(Base):
    __tablename__ = "resources"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    type = Column(Enum(ResourceType), nullable=False)
    floor = Column(Integer, nullable=False)
    area = Column(String(50))
    capacity = Column(Integer, default=1)
    hourly_rate = Column(Float, nullable=False)
    status = Column(Enum(ResourceStatus), default=ResourceStatus.AVAILABLE, nullable=False)
    description = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    bookings = relationship("Booking", back_populates="resource")


class Booking(Base):
    __tablename__ = "bookings"

    id = Column(Integer, primary_key=True, index=True)
    member_id = Column(Integer, ForeignKey("members.id"), nullable=False, index=True)
    resource_id = Column(Integer, ForeignKey("resources.id"), nullable=False, index=True)
    start_time = Column(DateTime(timezone=True), nullable=False, index=True)
    end_time = Column(DateTime(timezone=True), nullable=False)
    actual_start_time = Column(DateTime(timezone=True))
    actual_end_time = Column(DateTime(timezone=True))
    status = Column(Enum(BookingStatus), default=BookingStatus.PENDING_APPROVAL, nullable=False, index=True)
    total_amount = Column(Float, default=0.0, nullable=False)
    actual_amount = Column(Float, default=0.0)
    rejection_reason = Column(String(500))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    member = relationship("Member", back_populates="bookings")
    resource = relationship("Resource", back_populates="bookings")
    approval = relationship("Approval", back_populates="booking", uselist=False)
    payments = relationship("Payment", back_populates="booking")


class Approval(Base):
    __tablename__ = "approvals"

    id = Column(Integer, primary_key=True, index=True)
    booking_id = Column(Integer, ForeignKey("bookings.id"), nullable=False, unique=True, index=True)
    status = Column(Enum(ApprovalStatus), default=ApprovalStatus.PENDING, nullable=False)
    approver_id = Column(Integer, ForeignKey("admins.id"))
    approver_level = Column(Integer, default=1, nullable=False)
    submitted_at = Column(DateTime(timezone=True), server_default=func.now())
    processed_at = Column(DateTime(timezone=True))
    escalated_at = Column(DateTime(timezone=True))
    remark = Column(String(500))

    booking = relationship("Booking", back_populates="approval")
    approver = relationship("Admin", back_populates="approvals")


class Admin(Base):
    __tablename__ = "admins"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False)
    name = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    level = Column(Integer, default=1, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    approvals = relationship("Approval", back_populates="approver")
    notifications = relationship("Notification", back_populates="admin")


class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    booking_id = Column(Integer, ForeignKey("bookings.id"), index=True)
    member_id = Column(Integer, ForeignKey("members.id"), nullable=False, index=True)
    amount = Column(Float, nullable=False)
    status = Column(Enum(PaymentStatus), default=PaymentStatus.PENDING, nullable=False)
    payment_type = Column(String(50))
    transaction_id = Column(String(255))
    remark = Column(String(500))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    paid_at = Column(DateTime(timezone=True))

    booking = relationship("Booking", back_populates="payments")
    member = relationship("Member", back_populates="payments")


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    member_id = Column(Integer, ForeignKey("members.id"), index=True)
    admin_id = Column(Integer, ForeignKey("admins.id"), index=True)
    type = Column(String(50), nullable=False)
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    member = relationship("Member", back_populates="notifications")
    admin = relationship("Admin", back_populates="notifications")
