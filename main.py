# main.py
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Path
from pydantic import BaseModel, EmailStr

from supabase_service import supabase


# ---------- Pydantic modeli ----------
class ClientIn(BaseModel):
    name: str
    email: EmailStr


# ---------- FastAPI app ----------
app = FastAPI(title="FastAPI", version="1.0.0")


# ---------- Health ----------
@app.get("/health", tags=["Health"])
def health_check():
    return {"ok": True, "msg": "API radi"}


# ---------- Clients ----------
@app.post("/api/v1/clients", tags=["Clients"])
def add_client(client: ClientIn):
    """
    Kreira novog klijenta u tablici 'clients'.
    Očekuje JSON tijelo: { "name": "...", "email": "..." }
    """
    try:
        payload = client.model_dump()
        res = supabase.table("clients").insert(payload).execute()
        if not res.data:
            raise HTTPException(status_code=500, detail="Insert failed")
        # vraćamo prvi kreirani red
        return res.data[0]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/clients", tags=["Clients"])
def get_clients():
    """
    Vraća sve klijente.
    """
    try:
        res = supabase.table("clients").select("*").order("created_at", desc=True).execute()
        return res.data or []
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/clients/{client_id}", tags=["Clients"])
def get_client_by_id(client_id: str = Path(..., description="Client UUID")):
    """
    Vraća jednog klijenta po ID (UUID iz kolone 'id').
    """
    try:
        res = supabase.table("clients").select("*").eq("id", client_id).single().execute()
        if not res.data:
            raise HTTPException(status_code=404, detail="Client not found")
        return res.data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/v1/clients/{client_id}", tags=["Clients"])
def delete_client(client_id: str = Path(..., description="Client UUID")):
    """
    Briše klijenta po ID (UUID).
    """
    try:
        res = supabase.table("clients").delete().eq("id", client_id).execute()
        # Supabase može vratiti [] ako ništa nije obrisano
        if (not res.data) and (getattr(res, "count", 0) in (0, None)):
            raise HTTPException(status_code=404, detail="Client not found")
        return {"message": "Client deleted"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
