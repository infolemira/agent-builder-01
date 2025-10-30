# main.py
import os
from typing import Dict, Any, Optional

from fastapi import FastAPI, Depends, Header, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from schemas import ItemCreate, ItemUpdate, LoginPayload, SignupPayload
from supabase_service import get_supabase, get_user_from_token

app = FastAPI(title="Agent Builder 01 — FastAPI + Supabase")

# -----------------------------------
# CORS (omogućava pozive s frontenda)
# -----------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # promijeni kasnije ako imaš svoj frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------------
# Helpers
# -----------------------------------
async def get_bearer_token(authorization: Optional[str] = Header(default=None)) -> str:
    if not authorization:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing Authorization header")
    lower = authorization.lower().strip()
    if not lower.startswith("bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Authorization header")
    token = authorization.split(" ", 1)[1].strip()
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Empty bearer token")
    return token


async def require_user(token: str = Depends(get_bearer_token)) -> Dict[str, Any]:
    user = await get_user_from_token(token)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")
    return {"token": token, "user": user}


# -----------------------------------
# Health check
# -----------------------------------
@app.get("/health")
async def health():
    return {"ok": True}


# -----------------------------------
# AUTH — Signup & Login
# -----------------------------------
@app.post("/auth/signup")
async def signup(body: SignupPayload):
    sb = get_supabase()
    try:
        res = await sb.auth.sign_up({"email": body.email, "password": body.password})
        return {"user": getattr(res, "user", None)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/auth/login")
async def login(body: LoginPayload):
    sb = get_supabase()
    try:
        res = await sb.auth.sign_in_with_password({"email": body.email, "password": body.password})
        session = getattr(res, "session", None)
        if not session or not session.get("access_token"):
            raise HTTPException(status_code=401, detail="Invalid credentials")
        return {
            "access_token": session["access_token"],
            "token_type": "bearer",
            "expires_in": session.get("expires_in"),
            "user": res.user,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))


# -----------------------------------
# ITEMS — Create
# -----------------------------------
@app.post("/items")
async def create_item(body: ItemCreate, ctx=Depends(require_user)):
    token: str = ctx["token"]
    user = ctx["user"]
    user_id = user.id

    sb = get_supabase(token)
    payload = {
        "user_id": user_id,
        "title": body.title,
        "description": body.description,
        "done": body.done,
    }
    try:
        res = await sb.table("items").insert(payload).select("*").single().execute()
        return JSONResponse(content=res.data, status_code=201)
    except Exception as e:
        raise HTTPException(status_code=403, detail=str(e))


# -----------------------------------
# ITEMS — List (vraća samo vlastite redove)
# -----------------------------------
@app.get("/items")
async def list_items(ctx=Depends(require_user)):
    token: str = ctx["token"]
    sb = get_supabase(token)
    try:
        res = await sb.table("items").select("*").order("created_at", desc=True).execute()
        return res.data
    except Exception as e:
        raise HTTPException(status_code=403, detail=str(e))


# -----------------------------------
# ITEMS — Update
# -----------------------------------
@app.patch("/items/{item_id}")
async def update_item(item_id: str, body: ItemUpdate, ctx=Depends(require_user)):
    token: str = ctx["token"]
    patch: Dict[str, Any] = {k: v for k, v in body.model_dump().items() if v is not None}
    if not patch:
        raise HTTPException(status_code=400, detail="Nothing to update")

    sb = get_supabase(token)
    try:
        res = await sb.table("items").update(patch).eq("id", item_id).select("*").maybe_single().execute()
        if not res.data:
            raise HTTPException(status_code=404, detail="Item not found or not authorized")
        return res.data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=403, detail=str(e))


# -----------------------------------
# ITEMS — Delete
# -----------------------------------
@app.delete("/items/{item_id}")
async def delete_item(item_id: str, ctx=Depends(require_user)):
    token: str = ctx["token"]
    sb = get_supabase(token)
    try:
        res = await sb.table("items").delete().eq("id", item_id).select("id").maybe_single().execute()
        if not res.data:
            raise HTTPException(status_code=404, detail="Item not found or not authorized")
        return {"deleted_id": res.data["id"]}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=403, detail=str(e))


# -----------------------------------
# Lokalno pokretanje (za test)
# -----------------------------------
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
