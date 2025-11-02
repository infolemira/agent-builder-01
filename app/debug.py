# app/debug.py
from fastapi import APIRouter
import os, urllib.parse

router = APIRouter(prefix="/debug", tags=["debug"])

def tail(x: str, n: int = 6):
    return x[-n:] if x else None

def host(u: str):
    try:
        return urllib.parse.urlparse(u).netloc
    except Exception:
        return u

@router.get("/env", include_in_schema=False)
def env():
    supa_url = os.getenv("SUPABASE_URL") or ""
    anon = os.getenv("SUPABASE_ANON_KEY") or os.getenv("SUPABASE_KEY") or ""
    openai = os.getenv("OPENAI_API_KEY") or ""
    return {
        "supabase_url_host": host(supa_url),
        "supabase_url_redacted": (supa_url[:24] + "...") if supa_url else None,
        "supabase_anon_tail": tail(anon),
        "openai_key_tail": tail(openai),
    }
