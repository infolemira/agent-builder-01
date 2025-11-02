# app/history.py — /ai/history endpoints (list + delete)
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from app.auth import get_current_user, AuthedUser
from supabase_service import supabase

router = APIRouter(prefix="/ai", tags=["ai-history"])

class HistoryItem(BaseModel):
    id: str
    user_id: str
    prompt: str
    response: str
    created_at: Optional[str] = None

@router.get("/history")
def list_history(limit: int = 20, user: AuthedUser = Depends(get_current_user)) -> dict:
    supabase.postgrest.auth(user.token)
    res = (
        supabase.table("queries")
        .select("*")
        .eq("user_id", user.id)
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    return {"items": res.data or []}

@router.delete("/history/{item_id}")
def delete_one(item_id: str, user: AuthedUser = Depends(get_current_user)) -> dict:
    supabase.postgrest.auth(user.token)
    res = (
        supabase.table("queries")
        .delete()
        .eq("id", item_id)
        .eq("user_id", user.id)
        .execute()
    )
    if res.data == []:
        raise HTTPException(status_code=404, detail="Not found or not yours")
    return {"deleted": item_id}

@router.delete("/history")
def delete_all(user: AuthedUser = Depends(get_current_user)) -> dict:
    supabase.postgrest.auth(user.token)
    # meki limit: brišemo max 200 da izbjegnemo greške
    res = (
        supabase.table("queries")
        .select("id")
        .eq("user_id", user.id)
        .limit(200)
        .execute()
    )
    ids = [r["id"] for r in (res.data or [])]
    if not ids:
        return {"deleted": 0}
    supabase.table("queries").delete().in_("id", ids).execute()
    return {"deleted": len(ids)}
