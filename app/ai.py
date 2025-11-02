# app/ai.py — OpenRouter + model per request (picker)
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse
from sse_starlette.sse import EventSourceResponse
from pydantic import BaseModel, Field
from typing import Optional
import os, json, httpx

from app.auth import get_current_user, AuthedUser
from supabase_service import supabase

router = APIRouter(prefix="/ai", tags=["ai"])

OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY")
DEFAULT_MODEL = os.getenv("AI_MODEL", "openrouter/auto")
APP_URL = os.getenv("APP_URL", "https://agent-builder-01-1.onrender.com")
APP_NAME = os.getenv("APP_NAME", "Agent Builder 01")

if not OPENROUTER_KEY:
    raise HTTPException(status_code=500, detail="Server nema OPENROUTER_API_KEY")

class PromptPayload(BaseModel):
    prompt: str = Field(..., min_length=1)
    temperature: Optional[float] = Field(0.2, ge=0.0, le=1.0)
    model: Optional[str] = Field(None, description="npr. meta-llama/llama-3.1-8b-instruct:free")

def _headers():
    return {
        "Authorization": f"Bearer {OPENROUTER_KEY}",
        "HTTP-Referer": APP_URL,
        "X-Title": APP_NAME,
        "Content-Type": "application/json",
    }

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
    return {"ok": True, "provider": "openrouter", "model": DEFAULT_MODEL}

@router.post("/query")
async def ai_query(payload: PromptPayload, user: AuthedUser = Depends(get_current_user)):
    model = (payload.model or DEFAULT_MODEL).strip()
    data = {
        "model": model,
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": payload.prompt},
        ],
        "temperature": payload.temperature,
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
    model = (payload.model or DEFAULT_MODEL).strip()
    data = {
        "model": model,
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": payload.prompt},
        ],
        "temperature": payload.temperature,
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
