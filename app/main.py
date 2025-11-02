# app/main.py
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from supabase_service import supabase
from app.auth import get_current_user, AuthedUser
from app.history import router as history_router
from app.ai import router as ai_router
import os

app = FastAPI(
    title="Agent Builder 01 — FastAPI + Supabase",
    version="0.1.0",
    description="API service with Supabase auth and RLS-aware CRUD"
)




# -- HISTORY ROUTES --
app.include_router(history_router)
# -- AI ROUTES --
app.include_router(ai_router)
# ---------- CORS ----------
_frontends = os.getenv("FRONTEND_ORIGINS", "*")

# Ako je *, ne smijemo koristiti credentials=True (CORS pravilo)
if _frontends.strip() == "*":
    allow_origins = ["*"]
    allow_credentials = False
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


# ---------- HEALTH / ROOT ----------
@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/")
def root():
    return {"message": "Agent Builder 01 API is running 🚀"}


# ---------- AUTH ----------
@app.post("/auth/signup")
def signup(payload: SignupPayload):
    res = supabase.auth.sign_up({"email": payload.email, "password": payload.password})
    if res.user is None:
        raise HTTPException(status_code=400, detail="Signup failed")
    return {"message": "Signup successful", "user": res.user}


@app.post("/auth/login")
def login(payload: LoginPayload):
    try:
        res = supabase.auth.sign_in_with_password({"email": payload.email, "password": payload.password})
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid login credentials")
    if res.session is None:
        raise HTTPException(status_code=401, detail="Invalid login credentials")
    return {
        "access_token": res.session.access_token,
        "token_type": "bearer",
        "expires_in": res.session.expires_in,
        "user": res.user,
    }


# ---------- ITEMS (CRUD) ----------
@app.post("/items")
def create_item(item: ItemCreate, user: AuthedUser = Depends(get_current_user)):
    supabase.postgrest.auth(user.token)
    data = {
        "title": item.title,
        "description": item.description,
        "done": item.done,
        "user_id": user.id,
    }
    res = supabase.table("items").insert(data).execute()
    if not res.data:
        raise HTTPException(status_code=400, detail="Failed to create item")
    return {"message": "Item created successfully", "item": res.data[0]}


@app.get("/items")
def list_items(user: AuthedUser = Depends(get_current_user)):
    supabase.postgrest.auth(user.token)
    res = (
        supabase.table("items")
        .select("*")
        .eq("user_id", user.id)
        .order("created_at", desc=True)
        .execute()
    )
    return res.data


@app.patch("/items/{item_id}")
def update_item(item_id: str, item: ItemUpdate, user: AuthedUser = Depends(get_current_user)):
    supabase.postgrest.auth(user.token)
    update_data = item.dict(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")
    res = (
        supabase.table("items")
        .update(update_data)
        .eq("id", item_id)
        .eq("user_id", user.id)
        .execute()
    )
    if not res.data:
        raise HTTPException(status_code=404, detail="Item not found or not yours")
    return {"message": "Item updated", "item": res.data[0]}


@app.delete("/items/{item_id}")
def delete_item(item_id: str, user: AuthedUser = Depends(get_current_user)):
    supabase.postgrest.auth(user.token)
    res = (
        supabase.table("items")
        .delete()
        .eq("id", item_id)
        .eq("user_id", user.id)
        .execute()
    )
    if res.data == []:
        raise HTTPException(status_code=404, detail="Item not found or not yours")
    return {"message": "Item deleted", "id": item_id}
