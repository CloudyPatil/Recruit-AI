from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, EmailStr
from passlib.context import CryptContext
from database.mysql_db import execute_query
from middleware.auth_middleware import create_token, get_current_user
from typing import Optional
import httpx

router = APIRouter(prefix="/auth", tags=["Auth"])
pwd = CryptContext(schemes=["bcrypt"])

class RegisterInput(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: str        # 'hr' or 'candidate'
    company: Optional[str] = None

class LoginInput(BaseModel):
    email: EmailStr
    password: str

@router.post("/register")
def register(data: RegisterInput):
    existing = execute_query(
        "SELECT id FROM users WHERE email=%s",
        (data.email,), fetch=True
    )
    if existing:
        raise HTTPException(400, "Email already exists")

    hashed = pwd.hash(data.password)
    user_id = execute_query(
        "INSERT INTO users (name,email,password,role,company) VALUES (%s,%s,%s,%s,%s)",
        (data.name, data.email, hashed, data.role, data.company)
    )
    return {"message": "Registered successfully", "user_id": user_id}

@router.post("/login")
def login(data: LoginInput):
    user = execute_query(
        "SELECT * FROM users WHERE email=%s",
        (data.email,), fetch=True
    )
    if not user or not pwd.verify(data.password, user[0]["password"]):
        raise HTTPException(401, "Invalid credentials")

    token = create_token({"user_id": user[0]["id"], "role": user[0]["role"]})
    return {
        "access_token": token,
        "token_type": "bearer",
        "role": user[0]["role"],
        "name": user[0]["name"]
    }

# Add to routes/auth.py

class GoogleCheckInput(BaseModel):
    token: str

@router.post("/google-check")
async def google_check(data: GoogleCheckInput):
    async with httpx.AsyncClient() as client:
        res = await client.get(
            f"https://oauth2.googleapis.com/tokeninfo?id_token={data.token}"
        )
    if res.status_code != 200:
        raise HTTPException(400, "Invalid Google token")

    email = res.json().get("email")
    existing = execute_query(
        "SELECT * FROM users WHERE email=%s", (email,), fetch=True
    )

    if existing:
        user = existing[0]
        token = create_token({"user_id": user["id"], "role": user["role"]})
        return {
            "exists": True,
            "access_token": token,
            "role": user["role"],
            "name": user["name"]
        }
    return {"exists": False}


# Update /google endpoint to accept name
class GoogleAuthInput(BaseModel):
    token: str
    role: str = "candidate"
    name: str = ""
    company: str = ""

@router.post("/google")
async def google_login(data: GoogleAuthInput):
    async with httpx.AsyncClient() as client:
        res = await client.get(
            f"https://oauth2.googleapis.com/tokeninfo?id_token={data.token}"
        )
    if res.status_code != 200:
        raise HTTPException(400, "Invalid Google token")

    email = res.json().get("email")
    name = data.name or res.json().get("name", "User")

    existing = execute_query(
        "SELECT * FROM users WHERE email=%s", (email,), fetch=True
    )

    if existing:
        user = existing[0]
    else:
        user_id = execute_query(
            "INSERT INTO users (name,email,password,role,company) VALUES (%s,%s,%s,%s,%s)",
            (name, email, "GOOGLE_AUTH", data.role, data.company)
        )
        user = execute_query(
            "SELECT * FROM users WHERE id=%s", (user_id,), fetch=True
        )[0]

    token = create_token({"user_id": user["id"], "role": user["role"]})
    return {
        "access_token": token,
        "token_type": "bearer",
        "role": user["role"],
        "name": user["name"]
    }

from passlib.context import CryptContext

class ChangePasswordInput(BaseModel):
    old_password: str
    new_password: str

@router.post("/change-password")
def change_password(
    data: ChangePasswordInput,
    user=Depends(get_current_user)
):
    # Get current password
    current = execute_query(
        "SELECT password FROM users WHERE id=%s",
        (user["id"],), fetch=True
    )[0]

    # Google users can't change password
    if current["password"] == "GOOGLE_AUTH":
        raise HTTPException(400, "Google login users cannot change password")

    # Verify old password
    if not pwd.verify(data.old_password, current["password"]):
        raise HTTPException(401, "Incorrect old password")

    # Validate new password
    if len(data.new_password) < 6:
        raise HTTPException(400, "Password must be at least 6 characters")

    # Update
    new_hash = pwd.hash(data.new_password)
    execute_query(
        "UPDATE users SET password=%s WHERE id=%s",
        (new_hash, user["id"])
    )
    return {"message": "Password changed successfully"}