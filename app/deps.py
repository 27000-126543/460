from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.database import get_db
from app.utils import decode_access_token
from app.models import Member, Admin

security = HTTPBearer()


async def get_current_member(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> Member:
    token = credentials.credentials
    payload = decode_access_token(token)
    user_id = payload.get("user_id")
    user_type = payload.get("user_type")

    if user_id is None or user_type != "member":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的认证凭证"
        )

    member = db.query(Member).filter(Member.id == user_id, Member.is_active == True).first()
    if member is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在或已被禁用"
        )

    return member


async def get_current_admin(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> Admin:
    token = credentials.credentials
    payload = decode_access_token(token)
    user_id = payload.get("user_id")
    user_type = payload.get("user_type")

    if user_id is None or user_type != "admin":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的认证凭证"
        )

    admin = db.query(Admin).filter(Admin.id == user_id, Admin.is_active == True).first()
    if admin is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="管理员不存在或已被禁用"
        )

    return admin
