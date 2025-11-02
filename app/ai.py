# app/ai.py
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse
from sse_starlette.sse import EventSourceResponse
from pydantic import BaseModel, Field
from typing import Optional
import os, json, httpx

from app.auth import get_current_user, AuthedUser
from supabase_service import supabase

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
AI_MODEL = os.getenv("AI_MODEL", "gpt-4o-mini")

router = APIRouter(prefix="/ai", tags=["ai"])

class PromptPayload(BaseModel):
    prompt: str = Field(..., min_length=1, description="Korisnički upit")
    temperature: Optional[float] = Field(0.2, ge=0.0, le=1.0)

async def _save_query(user: AuthedUser, prompt: str, response: str) -> None:
    try:
        supabase.postgrest.auth(user.token)
        supabase.table("queries").insert({
            "user_id": user.id,
            "prompt": prompt,
            "response": response
        }).execute()
    except Exception:
        # Ne ruši odgovor zbog log greške
        pass

@router.get("/health-check")
def ai_health_check():
    if not OPENAI_API_KEY:
        raise HTTPException(status_code=500, detail="Server nema OPENAI_API_KEY")
    return {"ok": True, "model": AI_MODEL}

@router.post("/query")
async def ai_query(payload: PromptPayload, user: AuthedUser = Depends(get_current_user)):
    if not OPENAI_API_KEY:
        raise HTTPException(status_code=500, detail="Server nema OPENAI_API_KEY")
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {OPENAI_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": AI_MODEL,
                    "messages": [
                        {"role": "system", "content": "You are a helpful assistant."},
                        {"role": "user", "content": payload.prompt},
                    ],
                    "temperature": payload.temperature,
                },
            )
        if r.status_code != 200:
            return JSONResponse(status_code=r.status_code, content={"error": "OpenAI error", "detail": r.text})
        data = r.json()
        answer = (data.get("choices") or [{}])[0].get("message", {}).get("content", "") or ""
        await _save_query(user, payload.prompt, answer)
        return {"user_id": user.id, "prompt": payload.prompt, "answer": answer}
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"Upstream error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI failure: {str(e)}")

@router.post("/stream")
async def ai_stream(payload: PromptPayload, user: AuthedUser = Depends(get_current_user)):
    if not OPENAI_API_KEY:
        raise HTTPException(status_code=500, detail="Server nema OPENAI_API_KEY")

    async def event_generator():
        collected = ""
        try:
            async with httpx.AsyncClient(timeout=None) as client:
                async with client.stream(
                    "POST",
                    "https://api.openai.com/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {OPENAI_API_KEY}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": AI_MODEL,
                        "messages": [
                            {"role": "system", "content": "You are a helpful assistant."},
                            {"role": "user", "content": payload.prompt},
                        ],
                        "temperature": payload.temperature,
                        "stream": True,
                    },
                ) as r:
                    if r.status_code != 200:
                        yield {"event": "error", "data": json.dumps({"error": await r.aread().decode()})}
                        return
                    async for line in r.aiter_lines():
                        if not line:
                            continue
                        if line.startswith("data:"):
                            data = line[5:].strip()
                            if data == "[DONE]":
                                if collected:
                                    await _save_query(user, payload.prompt, collected)
                                yield {"event": "end", "data": "{}"}
                                break
                            try:
                                obj = json.loads(data)
                                delta = ((obj.get("choices") or [{}])[0].get("delta") or {}).get("content")
                                if delta:
                                    collected += delta
                                    yield {"event": "token", "data": json.dumps({"token": delta})}
                            except Exception:
                                continue
        except Exception as e:
            yield {"event": "error", "data": json.dumps({"error": str(e)})}

    return EventSourceResponse(event_generator(), media_type="text/event-stream")
