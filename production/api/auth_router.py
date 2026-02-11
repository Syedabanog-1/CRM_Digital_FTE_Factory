"""Authentication router: signup and login endpoints."""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from production.auth import hash_password, verify_password, create_access_token
from production.database.queries import get_pool

router = APIRouter(prefix="/auth", tags=["auth"])


class SignupRequest(BaseModel):
    name: str
    email: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


@router.post("/signup", status_code=201)
async def signup(req: SignupRequest):
    """Create a new user account."""
    if len(req.password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 6 characters",
        )

    pool = await get_pool()

    # Check if user already exists
    existing = await pool.fetchrow(
        "SELECT id FROM users WHERE email = $1", req.email
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists",
        )

    password_hash = hash_password(req.password)
    row = await pool.fetchrow(
        "INSERT INTO users (email, name, password_hash) VALUES ($1, $2, $3) RETURNING id",
        req.email,
        req.name,
        password_hash,
    )

    return {"message": "Account created successfully", "user_id": str(row["id"])}


@router.post("/login")
async def login(req: LoginRequest):
    """Authenticate user and return JWT access token."""
    pool = await get_pool()

    user = await pool.fetchrow(
        "SELECT id, name, email, password_hash FROM users WHERE email = $1", req.email
    )
    if not user or not verify_password(req.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    token = create_access_token(
        data={"sub": str(user["id"]), "email": user["email"], "name": user["name"]}
    )

    return {
        "access_token": token,
        "token_type": "bearer",
        "user_name": user["name"],
    }
