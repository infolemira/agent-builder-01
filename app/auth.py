# app/auth.py
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from supabase_service import supabase

security = HTTPBearer()

class AuthedUser(BaseModel):
    id: str
    token: str

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> AuthedUser:
    """
    Validacija user JWT-a preko Supabase-a. Vraća (user_id, token).
    """
    token = credentials.credentials
    try:
        res = supabase.auth.get_user(token)
        if res.user is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return AuthedUser(id=res.user.id, token=token)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
