# schemas.py
from typing import Optional
from pydantic import BaseModel, Field, EmailStr

# -----------------------------
# Item sheme
# -----------------------------
class ItemCreate(BaseModel):
    title: str = Field(..., min_length=1)
    description: Optional[str] = None
    done: bool = False


class ItemUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1)
    description: Optional[str] = None
    done: Optional[bool] = None


# -----------------------------
# Auth sheme
# -----------------------------
class LoginPayload(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6)


class SignupPayload(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6)
