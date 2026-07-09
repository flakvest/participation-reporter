from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from jose import JWTError, jwt
import bcrypt as _bcrypt
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import User

ALGORITHM = "HS256"


def verify_password(plain: str, hashed: str) -> bool:
    return _bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


def hash_password(plain: str) -> str:
    return _bcrypt.hashpw(plain.encode("utf-8"), _bcrypt.gensalt()).decode("utf-8")


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=settings.access_token_expire_minutes))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.secret_key, algorithm=ALGORITHM)


def decode_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None


def get_user_by_callsign(db: Session, callsign: str) -> Optional[User]:
    return db.query(User).filter(User.callsign == callsign.upper()).first()


def create_user(db: Session, callsign: str, password: str, platoon: str, role: str = "operator") -> User:
    user = User(
        callsign=callsign.upper(),
        password_hash=hash_password(password),
        platoon=platoon.upper(),
        role=role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def get_current_user_from_token(token: str) -> Optional[dict]:
    payload = decode_token(token)
    if payload is None:
        return None
    return payload


def get_current_user(request: Request, db: Session = Depends(get_db)) -> Optional[User]:
    token = request.cookies.get("access_token")
    if not token:
        return None
    payload = decode_token(token)
    if payload is None:
        return None
    callsign = payload.get("sub")
    if callsign is None:
        return None
    return get_user_by_callsign(db, callsign)


def require_user(user: Optional[User] = Depends(get_current_user)) -> User:
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    return user
