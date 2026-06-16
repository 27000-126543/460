from sqlalchemy.orm import Session
from app.models import Member, MemberLevel
from app.schemas import MemberCreate, MemberUpdate
from app.utils import hash_password, verify_password
from typing import Optional


class MemberService:
    @staticmethod
    def create_member(db: Session, member_data: MemberCreate) -> Member:
        hashed_password = hash_password(member_data.password)
        credit_limits = {
            MemberLevel.BASIC: 1000.0,
            MemberLevel.SILVER: 3000.0,
            MemberLevel.GOLD: 8000.0,
            MemberLevel.PLATINUM: 20000.0
        }
        credit_limit = member_data.credit_limit if member_data.credit_limit else credit_limits.get(member_data.level, 1000.0)

        db_member = Member(
            name=member_data.name,
            email=member_data.email,
            phone=member_data.phone,
            password_hash=hashed_password,
            level=member_data.level,
            credit_limit=credit_limit
        )
        db.add(db_member)
        db.commit()
        db.refresh(db_member)
        return db_member

    @staticmethod
    def get_member_by_id(db: Session, member_id: int) -> Optional[Member]:
        return db.query(Member).filter(Member.id == member_id).first()

    @staticmethod
    def get_member_by_email(db: Session, email: str) -> Optional[Member]:
        return db.query(Member).filter(Member.email == email).first()

    @staticmethod
    def get_member_by_phone(db: Session, phone: str) -> Optional[Member]:
        return db.query(Member).filter(Member.phone == phone).first()

    @staticmethod
    def list_members(
        db: Session,
        page: int = 1,
        page_size: int = 20,
        level: Optional[MemberLevel] = None,
        keyword: Optional[str] = None
    ) -> tuple[list[Member], int]:
        query = db.query(Member)
        if level:
            query = query.filter(Member.level == level)
        if keyword:
            query = query.filter(
                (Member.name.like(f"%{keyword}%")) |
            (Member.email.like(f"%{keyword}%")) |
            (Member.phone.like(f"%{keyword}%"))
            )
        total = query.count()
        items = query.order_by(Member.id.desc()).offset((page - 1) * page_size).limit(page_size).all()
        return items, total

    @staticmethod
    def update_member(db: Session, member_id: int, update_data: MemberUpdate) -> Optional[Member]:
        db_member = MemberService.get_member_by_id(db, member_id)
        if not db_member:
            return None
        update_dict = update_data.model_dump(exclude_unset=True)
        for key, value in update_dict.items():
            setattr(db_member, key, value)
        db.commit()
        db.refresh(db_member)
        return db_member

    @staticmethod
    def authenticate(db: Session, email: str, password: str) -> Optional[Member]:
        member = MemberService.get_member_by_email(db, email)
        if not member or not member.is_active:
            return None
        if not verify_password(password, member.password_hash):
            return None
        return member

    @staticmethod
    def recharge(db: Session, member_id: int, amount: float) -> Optional[Member]:
        db_member = MemberService.get_member_by_id(db, member_id)
        if not db_member:
            return None
        db_member.balance += amount
        db.commit()
        db.refresh(db_member)
        return db_member

    @staticmethod
    def check_booking_permission(db: Session, member_id: int, amount: float) -> tuple[bool, str]:
        member = MemberService.get_member_by_id(db, member_id)
        if not member:
            return False, "会员不存在"
        if not member.is_active:
            return False, "会员账户已被禁用"
        if member.default_count >= 3:
            return False, "违约次数过多，预订受限"
        available_credit = member.balance + member.credit_limit
        if amount > available_credit:
            return False, f"信用额度不足，可用额度：¥{available_credit}"
        return True, ""

    @staticmethod
    def record_default(db: Session, member_id: int) -> Optional[Member]:
        member = MemberService.get_member_by_id(db, member_id)
        if not member:
            return None
        member.default_count += 1
        member.credit_limit = max(0, member.credit_limit - 200)
        db.commit()
        db.refresh(member)
        return member
