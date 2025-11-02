# app/history.py
from fastapi import APIRouter, HTTPException, Depends, Query
from supabase_service import supabase
from app.auth import get_current_user, AuthedUser

router = APIRouter(prefix="/ai", tags=["ai"])

@router.get("/history")
def list_history(limit: int = Query(50, ge=1, le=200), user: AuthedUser = Depends(get_current_user)):
    try:
        supabase.postgrest.auth(user.token)
        res = (
            supabase.table("queries")
            .select("id,prompt,response,created_at")
            .eq("user_id", user.id)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return {"items": res.data or []}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"History read failed: {str(e)}")

@router.delete("/history")
def delete_all_history(user: AuthedUser = Depends(get_current_user)):
    try:
        supabase.postgrest.auth(user.token)
        supabase.table("queries").delete().eq("user_id", user.id).execute()
        return {"ok": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"History delete failed: {str(e)}")

@router.delete("/history/{qid}")
def delete_one(qid: str, user: AuthedUser = Depends(get_current_user)):
    try:
        supabase.postgrest.auth(user.token)
        supabase.table("queries").delete().eq("id", qid).eq("user_id", user.id).execute()
        return {"ok": True, "id": qid}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"History delete failed: {str(e)}")
