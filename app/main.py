# app/main.py
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional
import os

from supabase_service import supabase
from app.auth import get_current_user, AuthedUser

# Routers (optional – ako postoje, include)
try:
    from app.ai import router as ai_router
except Exception:
    ai_router = None
try:
    from app.history import router as history_router
except Exception:
    history_router = None
try:
    from app.debug import router as debug_router
except Exception:
    debug_router = None

app = FastAPI(
    title="Agent Builder 01 — FastAPI + Supabase",
    version="0.1.0",
    description="API service with Supabase auth and RLS-aware CRUD"
)

# ---------- CORS ----------
_frontends = os.getenv("FRONTEND_ORIGINS", "*")
if _frontends.strip() == "*":
    allow_origins = ["*"]; allow_credentials = False
else:
    allow_origins = [o.strip() for o in _frontends.split(",") if o.strip()]
    allow_credentials = True

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------- Include routers ----------
if ai_router:        app.include_router(ai_router)
if history_router:   app.include_router(history_router)
if debug_router:     app.include_router(debug_router)   # <— /debug/env

# ---------- MODELI ----------
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

# ---------- HEALTH / ROOT / UI ----------
@app.get("/health", tags=["default"])
def health(): return {"status": "ok"}

@app.get("/", tags=["default"])
def root(): return {"message": "Agent Builder 01 API is running 🚀"}

@app.get("/ui", include_in_schema=False)
def ui_page(): return FileResponse("index.html")

# ---------- AUTH ----------
@app.post("/auth/signup", tags=["auth"])
def signup(payload: SignupPayload):
    res = supabase.auth.sign_up({"email": payload.email, "password": payload.password})
    if res.user is None: raise HTTPException(status_code=400, detail="Signup failed")
    return {"message": "Signup successful", "user": res.user}

@app.post("/auth/login", tags=["auth"])
def login(payload: LoginPayload):
    try:
        res = supabase.auth.sign_in_with_password({"email": payload.email, "password": payload.password})
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid login credentials")
    if res.session is None: raise HTTPException(status_code=401, detail="Invalid login credentials")
    return {
        "access_token": res.session.access_token,
        "token_type": "bearer",
        "expires_in": res.session.expires_in,
        "user": res.user,
    }

# ---------- ITEMS (CRUD) ----------
@app.post("/items", tags=["items"])
def create_item(item: ItemCreate, user: AuthedUser = Depends(get_current_user)):
    supabase.postgrest.auth(user.token)
    data = {"title": item.title, "description": item.description, "done": item.done, "user_id": user.id}
    res = supabase.table("items").insert(data).execute()
    if not res.data: raise HTTPException(status_code=400, detail="Failed to create item")
    return {"message": "Item created successfully", "item": res.data[0]}

@app.get("/items", tags=["items"])
def list_items(user: AuthedUser = Depends(get_current_user)):
    supabase.postgrest.auth(user.token)
    res = supabase.table("items").select("*").eq("user_id", user.id).order("created_at", desc=True).execute()
    return res.data

@app.patch("/items/{item_id}", tags=["items"])
def update_item(item_id: str, item: ItemUpdate, user: AuthedUser = Depends(get_current_user)):
    supabase.postgrest.auth(user.token)
    update_data = item.dict(exclude_unset=True)
    if not update_data: raise HTTPException(status_code=400, detail="No fields to update")
    res = supabase.table("items").update(update_data).eq("id", item_id).eq("user_id", user.id).execute()
    if not res.data: raise HTTPException(status_code=404, detail="Item not found or not yours")
    return {"message": "Item updated", "item": res.data[0]}

@app.delete("/items/{item_id}", tags=["items"])
def delete_item(item_id: str, user: AuthedUser = Depends(get_current_user)):
    supabase.postgrest.auth(user.token)
    res = supabase.table("items").delete().eq("id", item_id).eq("user_id", user.id).execute()
    if res.data == []: raise HTTPException(status_code=404, detail="Item not found or not yours")
    return {"message": "Item deleted", "id": item_id}
