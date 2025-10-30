from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from supabase import create_client, Client
from pydantic import BaseModel
import os
import requests

# -----------------------------------------------------------------------------
# APP INIT
# -----------------------------------------------------------------------------
app = FastAPI(
    title="Agent Builder 01 — FastAPI + Supabase",
    version="0.1.0",
    description="API service for managing users and items with Supabase authentication",
)

security = HTTPBearer()

# -----------------------------------------------------------------------------
# SUPABASE INIT
# -----------------------------------------------------------------------------
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

def get_supabase() -> Client:
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise ValueError("Supabase credentials not configured")
    return create_client(SUPABASE_URL, SUPABASE_KEY)

# -----------------------------------------------------------------------------
# MODELI
# -----------------------------------------------------------------------------
class SignupPayload(BaseModel):
    email: str
    password: str

class LoginPayload(BaseModel):
    email: str
    password: str

class ItemCreate(BaseModel):
    title: str
    description: str
    done: bool = False

class ItemUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    done: bool | None = None

# -----------------------------------------------------------------------------
# AUTH FUNKCIJE
# -----------------------------------------------------------------------------
def get_user_from_token(token: str):
    """Vrati korisnika iz Supabase Auth tokena."""
    try:
        resp = requests.get(
            f"{SUPABASE_URL}/auth/v1/user",
            headers={"Authorization": f"Bearer {token}", "apikey": SUPABASE_KEY},
        )
        if resp.status_code != 200:
            raise HTTPException(status_code=401, detail="Invalid or expired token")
        return resp.json()
    except Exception:
        raise HTTPException(status_code=401, detail="Authentication failed")

def require_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    return get_user_from_token(token)

# -----------------------------------------------------------------------------
# ROUTES
# -----------------------------------------------------------------------------
@app.get("/health", tags=["default"])
def health():
    return {"status": "ok"}

@app.get("/", tags=["default"])
def root():
    return {"message": "Agent Builder 01 API running successfully."}

# --- SIGNUP -------------------------------------------------------------------
@app.post("/auth/signup", tags=["default"])
def signup(payload: SignupPayload):
    sb = get_supabase()
    try:
        result = sb.auth.sign_up({"email": payload.email, "password": payload.password})
        return {"user": result.user, "session": result.session}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# --- LOGIN --------------------------------------------------------------------
@app.post("/auth/login", tags=["default"])
def login(payload: LoginPayload):
    """Prijavi i vraća access token iz Supabase Autha."""
    url = f"{SUPABASE_URL}/auth/v1/token?grant_type=password"
    headers = {
        "apikey": SUPABASE_KEY,
        "Content-Type": "application/json",
    }
    data = {"email": payload.email, "password": payload.password}

    resp = requests.post(url, headers=headers, json=data)
    if resp.status_code != 200:
        raise HTTPException(status_code=401, detail="Invalid login credentials")
    return resp.json()

# --- CREATE ITEM --------------------------------------------------------------
@app.post("/items", tags=["default"])
async def create_item(item: ItemCreate, user=Depends(require_user)):
    sb = get_supabase()
    uid = (
        user.get("user", {}).get("id")
        or user.get("id")
        or user.get("user_id")
    )
    if not uid:
        raise HTTPException(status_code=401, detail="Missing user id")

    try:
        resp = sb.table("items").insert({
            "title": item.title,
            "description": item.description,
            "done": item.done,
            "user_id": uid
        }).execute()
        return {"item": resp.data[0] if resp.data else None}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DB insert error: {str(e)}")

# --- GET ITEMS (POPPRAVLJENO) -------------------------------------------------
@app.get("/items", tags=["default"])
async def list_items(user=Depends(require_user)):
    """Vraća sve iteme prijavljenog korisnika."""
    sb = get_supabase()

    uid = None
    if isinstance(user, dict):
        uid = (
            user.get("user", {}).get("id")
            or user.get("id")
            or user.get("user_id")
        )

    if not uid:
        return JSONResponse(status_code=401, content={"detail": "Not authenticated (no user id)"})

    try:
        resp = sb.table("items").select("*").eq("user_id", uid).execute()
        rows = resp.data or []
        return {"items": rows}
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"detail": f"DB error: {str(e)}"}
        )

# --- UPDATE ITEM --------------------------------------------------------------
@app.patch("/items/{item_id}", tags=["default"])
async def update_item(item_id: str, item: ItemUpdate, user=Depends(require_user)):
    sb = get_supabase()
    uid = (
        user.get("user", {}).get("id")
        or user.get("id")
        or user.get("user_id")
    )

    try:
        updates = {k: v for k, v in item.dict().items() if v is not None}
        resp = sb.table("items").update(updates).eq("id", item_id).eq("user_id", uid).execute()
        return {"updated": resp.data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DB update error: {str(e)}")

# --- DELETE ITEM --------------------------------------------------------------
@app.delete("/items/{item_id}", tags=["default"])
async def delete_item(item_id: str, user=Depends(require_user)):
    sb = get_supabase()
    uid = (
        user.get("user", {}).get("id")
        or user.get("id")
        or user.get("user_id")
    )
    try:
        sb.table("items").delete().eq("id", item_id).eq("user_id", uid).execute()
        return {"deleted": item_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DB delete error: {str(e)}")
