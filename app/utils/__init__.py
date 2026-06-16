from passlib.context import CryptContext
from datetime import datetime, timedelta
from jose import JWTError, jwt
from app.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(user_id: int, user_type: str = "member") -> str:
    expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode = {
        "user_id": user_id,
        "user_type": user_type,
        "exp": expire
    }
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        return {}


def calculate_hours(start_time: datetime, end_time: datetime) -> float:
    duration = end_time - start_time
    hours = duration.total_seconds() / 3600
    return round(max(hours, 0.01), 2)


def calculate_cost(hourly_rate: float, hours: float) -> float:
    return round(hourly_rate * hours, 2)
