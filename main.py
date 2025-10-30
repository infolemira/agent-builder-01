# main.py — Full API: Auth (signup/login) + Items CRUD + Bearer auth (Supabase)
from typing import Optional, Dict, Any
import os

from fastapi import FastAPI, Depends, HTTPException, status, Path
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr

# Supabase v2 client
from supabase.client import create_client, Client

# -------------------------------
# Supabase init
# -------------------------------
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")
if not SUPABASE_URL or not SUPABASE_ANON_KEY:
    raise RuntimeError("Missing SUPABASE_URL or SUPABASE_ANON_KEY.")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

# -------------------------------
# FastAPI app
# -------------------------------
app = FastAPI(
    title="Agent Builder 01 — FastAPI + Supabase",
    description="API service for managing users and items with Supabase authentication",
    version="0.1.0",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],           # promijeni na domenu frontenda kad budeš imala
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------------
# Security (dodaje 🔒 Authorize)
# -------------------------------
security = HTTPBearer(auto_error=True)

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    """Validiraj Bearer token preko Supabase Auth-a."""
    token = credentials.credentials
    try:
        res = supabase.auth.get_user(token)  # v2 sync call
        user = getattr(res, "user", None)
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token.")
        return {"id": user.id, "email": user.email}
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token.")

# -------------------------------
# Schemas
# -------------------------------
class SignupPayload(BaseModel):
    email: EmailStr
    password: str

class LoginPayload(BaseModel):
    email: EmailStr
    password: str

class ItemCreate(BaseModel):
    title: str
    description: Optional[str] = None
    done: bool = False

class ItemUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    done: Optional[bool] = None

# -------------------------------
# Health & Root
# -------------------------------
@app.get("/health", tags=["default"])
def health():
    return {"ok": True}

@app.get("/", tags=["default"])
def root():
    return {"message": "Welcome to Agent Builder 01 API"}

# -------------------------------
# AUTH
# -------------------------------
@app.post("/auth/signup", tags=["default"])
def signup(payload: SignupPayload):
    """
    Kreira usera u Supabase Auth-u. Ako su u projektu uključene potvrde emaila,
    korisnik mora potvrditi mail prije logina (osim ako ručno potvrdiš u dashboardu).
    """
    try:
        data = {"email": payload.email, "password": payload.password}
        res = supabase.auth.sign_up(data)
        user = getattr(res, "user", None)
        if not user:
            raise HTTPException(status_code=400, detail="Signup failed.")
        return {"user_id": user.id, "email": user.email}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/auth/login", tags=["default"])
def login(payload: LoginPayload):
    """
    Prijava i izdavanje access tokena iz Supabase Auth-a.
    """
    try:
        data = {"email": payload.email, "password": payload.password}
        res = supabase.auth.sign_in_with_password(data)
        session = getattr(res, "session", None)
        if not session or not session.access_token:
            raise HTTPException(status_code=401, detail="Invalid login credentials")
        return {
            "access_token": session.access_token,
            "token_type": "bearer",
            "expires_in": session.expires_in,
            "user": {"id": res.user.id, "email": res.user.email},
        }
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid login credentials")

# -------------------------------
# ITEMS CRUD (RLS po user_id)
# -------------------------------
@app.get("/items", tags=["default"], dependencies=[Depends(security)])
def list_items(user=Depends(get_current_user)):
    resp = (
        supabase.table("items")
        .select("*")
        .eq("user_id", user["id"])
        .order("created_at", desc=True)
        .execute()
    )
    return resp.data or []

@app.post("/items", tags=["default"], dependencies=[Depends(security)], status_code=201)
def create_item(payload: ItemCreate, user=Depends(get_current_user)):
    row = {
        "user_id": user["id"],
        "title": payload.title,
        "description": payload.description,
        "done": payload.done,
    }
    resp = supabase.table("items").insert(row).execute()
    if not resp.data:
        raise HTTPException(status_code=400, detail="Insert failed")
    return resp.data[0]

@app.patch("/items/{item_id}", tags=["default"], dependencies=[Depends(security)])
def update_item(
    item_id: str = Path(..., description="UUID itema"),
    payload: ItemUpdate = None,
    user=Depends(get_current_user),
):
    data = {k: v for k, v in (payload.dict(exclude_unset=True) if payload else {}).items()}
    if not data:
        raise HTTPException(status_code=422, detail="No fields to update.")
    resp = (
        supabase.table("items")
        .update(data)
        .eq("id", item_id)
        .eq("user_id", user["id"])
        .execute()
    )
    if not resp.data:
        raise HTTPException(status_code=404, detail="Item not found")
    return resp.data[0]

@app.delete("/items/{item_id}", tags=["default"], dependencies=[Depends(security)])
def delete_item(item_id: str, user=Depends(get_current_user)):
    resp = (
        supabase.table("items")
        .delete()
        .eq("id", item_id)
        .eq("user_id", user["id"])
        .execute()
    )
    if not resp.data:
        raise HTTPException(status_code=404, detail="Item not found")
    return {"deleted_id": item_id}
