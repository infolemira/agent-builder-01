# app/ai.py — OpenRouter + history + export (sa max_tokens limiterom)
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse, Response
from sse_starlette.sse import EventSourceResponse
from pydantic import BaseModel, Field
from typing import Optional, List
import os, json, httpx, csv, io

from app.auth import get_current_user, AuthedUser
from supabase_service import supabase

router = APIRouter(prefix="/ai", tags=["ai"])

OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY")
DEFAULT_MODEL = os.getenv("AI_MODEL", "openrouter/auto")
APP_URL = os.getenv("APP_URL", "https://agent-builder-01-1.onrender.com")
APP_NAME = os.getenv("APP_NAME", "she-ona")
DEFAULT_MAX_TOKENS = int(os.getenv("AI_MAX_TOKENS", "512"))  # siguran limit

def _headers():
    return {
        "Authorization": f"Bearer {OPENROUTER_KEY}",
        "HTTP-Referer": APP_URL,
        "X-Title": APP_NAME,
        "Content-Type": "application/json",
    }

class PromptPayload(BaseModel):
    prompt: str = Field(..., min_length=1)
    temperature: Optional[float] = Field(0.2, ge=0.0, le=1.0)
    model: Optional[str] = Field(None, description="npr. openrouter/auto ili qwen/qwen-2.5-7b-instruct:free")
    max_tokens: Optional[int] = Field(None, ge=32, le=4096, description="maks. izlaznih tokena (default 512)")

async def _save_query(user: AuthedUser, prompt: str, response: str) -> None:
    try:
        supabase.postgrest.auth(user.token)
        supabase.table("queries").insert({
            "user_id": user.id,
            "prompt": prompt,
            "response": response
        }).execute()
    except Exception:
        pass

@router.get("/health-check")
def health_check():
    ok = bool(OPENROUTER_KEY)
    return {"ok": ok, "provider": "openrouter", "default_model": DEFAULT_MODEL, "default_max_tokens": DEFAULT_MAX_TOKENS}

@router.post("/query")
async def ai_query(payload: PromptPayload, user: AuthedUser = Depends(get_current_user)):
    if not OPENROUTER_KEY:
        raise HTTPException(status_code=500, detail="Server nema OPENROUTER_API_KEY")
    model = (payload.model or DEFAULT_MODEL).strip()
    max_tokens = payload.max_tokens or DEFAULT_MAX_TOKENS

    data = {
        "model": model,
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": payload.prompt},
        ],
        "temperature": payload.temperature,
        "max_tokens": max_tokens,  # <= ključna promjena
    }
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post("https://openrouter.ai/api/v1/chat/completions", headers=_headers(), json=data)
    if r.status_code != 200:
        return JSONResponse(status_code=r.status_code, content={"error": "openrouter_error", "detail": r.text})
    resp = r.json()
    answer = (resp.get("choices") or [{}])[0].get("message", {}).get("content", "") or ""
    await _save_query(user, payload.prompt, answer)
    return {"answer": answer, "model": model}

@router.post("/stream")
async def ai_stream(payload: PromptPayload, user: AuthedUser = Depends(get_current_user)):
    if not OPENROUTER_KEY:
        raise HTTPException(status_code=500, detail="Server nema OPENROUTER_API_KEY")
    model = (payload.model or DEFAULT_MODEL).strip()
    max_tokens = payload.max_tokens or DEFAULT_MAX_TOKENS

    data = {
        "model": model,
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": payload.prompt},
        ],
        "temperature": payload.temperature,
        "max_tokens": max_tokens,   # <= i u streamu
        "stream": True,
    }

    async def event_gen():
        collected = ""
        async with httpx.AsyncClient(timeout=None) as client:
            async with client.stream("POST", "https://openrouter.ai/api/v1/chat/completions", headers=_headers(), json=data) as r:
                if r.status_code != 200:
                    yield {"event": "error", "data": json.dumps({"error": await r.aread().decode()})}
                    return
                async for line in r.aiter_lines():
                    if not line or not line.startswith("data:"):
                        continue
                    chunk = line[5:].strip()
                    if chunk == "[DONE]":
                        await _save_query(user, payload.prompt, collected)
                        yield {"event": "end", "data": "{}"}
                        break
                    try:
                        part = json.loads(chunk)
                        delta = ((part.get("choices") or [{}])[0].get("delta") or {}).get("content")
                        if delta:
                            collected += delta
                            yield {"event": "token", "data": json.dumps({"token": delta})}
                    except Exception:
                        continue
    return EventSourceResponse(event_gen(), media_type="text/event-stream")

@router.get("/history")
def history_list(user: AuthedUser = Depends(get_current_user)):
    supabase.postgrest.auth(user.token)
    res = supabase.table("queries").select("*").eq("user_id", user.id).order("created_at", desc=True).execute()
    return {"items": res.data or []}

@router.delete("/history")
def history_delete_all(user: AuthedUser = Depends(get_current_user)):
    supabase.postgrest.auth(user.token)
    supabase.table("queries").delete().eq("user_id", user.id).execute()
    return {"deleted": "all"}

@router.delete("/history/{row_id}")
def history_delete_one(row_id: str, user: AuthedUser = Depends(get_current_user)):
    supabase.postgrest.auth(user.token)
    supabase.table("queries").delete().eq("id", row_id).eq("user_id", user.id).execute()
    return {"deleted": row_id}

@router.get("/history/export.json")
def history_export_json(user: AuthedUser = Depends(get_current_user)):
    supabase.postgrest.auth(user.token)
    res = (
        supabase.table("queries")
        .select("id,prompt,response,created_at")
        .eq("user_id", user.id)
        .order("created_at", desc=True)
        .execute()
    )
    return JSONResponse(
        content=(res.data or []),
        headers={"Content-Disposition": "attachment; filename=history.json"},
        media_type="application/json",
    )

@router.get("/history/export.csv")
def history_export_csv(user: AuthedUser = Depends(get_current_user)):
    supabase.postgrest.auth(user.token)
    res = (
        supabase.table("queries")
        .select("id,prompt,response,created_at")
        .eq("user_id", user.id)
        .order("created_at", desc=True)
        .execute()
    )
    rows = res.data or []
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["id", "created_at", "prompt", "response"])
    for r in rows:
        writer.writerow([r.get("id",""), r.get("created_at",""), r.get("prompt",""), r.get("response","")])
    return Response(
        content=buf.getvalue().encode("utf-8"),
        headers={"Content-Disposition": "attachment; filename=history.csv"},
        media_type="text/csv; charset=utf-8",
    )
