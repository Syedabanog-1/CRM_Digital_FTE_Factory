"""Authentication utilities: password hashing and JWT token management."""

from datetime import datetime, timedelta, timezone
import hashlib
import secrets

from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from production.config import settings

security = HTTPBearer()


def hash_password(password: str) -> str:
    """Hash a plaintext password using SHA-256 with salt."""
    salt = secrets.token_hex(16)
    pw_hash = hashlib.sha256(f"{salt}{password}".encode()).hexdigest()
    return f"{salt}${pw_hash}"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against a salted SHA-256 hash."""
    try:
        salt, pw_hash = hashed_password.split("$", 1)
        return hashlib.sha256(f"{salt}{plain_password}".encode()).hexdigest() == pw_hash
    except (ValueError, AttributeError):
        return False


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """Create a signed JWT access token."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.jwt_expire_minutes)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    """Decode and validate JWT from Authorization: Bearer header."""
    token = credentials.credentials
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm]
        )
        user_id: str | None = payload.get("sub")
        email: str | None = payload.get("email")
        name: str | None = payload.get("name")
        if user_id is None:
            raise credentials_exception
        return {"user_id": user_id, "email": email, "name": name}
    except JWTError:
        raise credentials_exception
