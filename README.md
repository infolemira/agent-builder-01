from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional, List
from supabase import create_client, Client
import os
import jwt

# --------------------------------------------------
# ✅ Konfiguracija aplikacije
# --------------------------------------------------

app = FastAPI(
    title="Agent Builder 01 — FastAPI + Supabase",
    version="0.1.0",
    description="API service for managing users and items with Supabase authentication"
)

# CORS (dozvoljava pozive s web klijenta)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --------------------------------------------------
# ✅ Supabase klijent
# --------------------------------------------------

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Supabase URL i KEY nisu postavljeni u environment varijablama!")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --------------------------------------------------
# ✅ Autentifikacija (Bearer token)
# --------------------------------------------------

security = HTTPBearer()

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    Provjera JWT tokena i izvlačenje user_id
    """
    token = credentials.credentials
    try:
        payload = jwt.decode(token, options={"verify_signature": False})
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token payload")
        return user_id
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

# --------------------------------------------------
# ✅ Pydantic modeli
# --------------------------------------------------

class SignupPayload(BaseModel):
    email: str
    password: str

class LoginPayload(BaseModel):
    email: str
    password: str

class ItemCreate(BaseModel):
    title: str
    description: Optional[str] = None
    done: bool = False

class ItemUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    done: Optional[bool] = None

# --------------------------------------------------
# ✅ Health endpoint
# --------------------------------------------------

@app.get("/health", tags=["default"])
def health():
    return {"status": "ok"}

@app.get("/", tags=["default"])
def root():
    return {"message": "Agent Builder 01 API is running 🚀"}

# --------------------------------------------------
# ✅ Auth endpointi (Signup / Login)
# --------------------------------------------------

@app.post("/auth/signup", tags=["auth"])
def signup(payload: SignupPayload):
    res = supabase.auth.sign_up(
        {"email": payload.email, "password": payload.password}
    )
    if res.user is None:
        raise HTTPException(status_code=400, detail="Signup failed")
    return {"message": "Signup successful", "user": res.user}

@app.post("/auth/login", tags=["auth"])
def login(payload: LoginPayload):
    res = supabase.auth.sign_in_with_password(
        {"email": payload.email, "password": payload.password}
    )
    if res.session is None:
        raise HTTPException(status_code=401, detail="Invalid login credentials")
    return {
        "access_token": res.session.access_token,
        "token_type": "bearer",
        "expires_in": res.session.expires_in,
        "user": res.user,
    }

# --------------------------------------------------
# ✅ Items (CRUD)
# --------------------------------------------------

@app.post("/items", tags=["items"])
def create_item(item: ItemCreate, user_id: str = Depends(get_current_user)):
    data = {
        "title": item.title,
        "description": item.description,
        "done": item.done,
        "user_id": user_id
    }
    res = supabase.table("items").insert(data).execute()
    if not res.data:
        raise HTTPException(status_code=400, detail="Failed to create item")
    return {"message": "Item created successfully", "item": res.data[0]}

@app.get("/items", tags=["items"])
def list_items(user_id: str = Depends(get_current_user)):
    res = supabase.table("items").select("*").eq("user_id", user_id).execute()
    return res.data

@app.patch("/items/{item_id}", tags=["items"])
def update_item(item_id: str, item: ItemUpdate, user_id: str = Depends(get_current_user)):
    update_data = item.dict(exclude_unset=True)
    res = (
        supabase.table("items")
        .update(update_data)
        .eq("id", item_id)
        .eq("user_id", user_id)
        .execute()
    )
    if not res.data:
        raise HTTPException(status_code=404, detail="Item not found or not yours")
    return {"message": "Item updated", "item": res.data[0]}

@app.delete("/items/{item_id}", tags=["items"])
def delete_item(item_id: str, user_id: str = Depends(get_current_user)):
    res = (
        supabase.table("items")
        .delete()
        .eq("id", item_id)
        .eq("user_id", user_id)
        .execute()
    )
    if res.data == []:
        raise HTTPException(status_code=404, detail="Item not found or not yours")
    return {"message": "Item deleted", "id": item_id}

# --------------------------------------------------
# ✅ Kraj
# --------------------------------------------------
