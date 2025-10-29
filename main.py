from fastapi import FastAPI, HTTPException
from supabase_service import supabase

app = FastAPI()

@app.get("/health", tags=["Health"])
def health_check():
    return {"ok": True, "msg": "API radi"}

@app.post("/api/v1/clients", tags=["Clients"])
def add_client(client: dict):
    try:
        response = supabase.table("clients").insert(client).execute()
        return response.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 🔹 NOVO: dohvaćanje svih klijenata
@app.get("/api/v1/clients", tags=["Clients"])
def get_clients():
    try:
        response = supabase.table("clients").select("*").execute()
        if not response.data:
            return {"message": "No clients found"}
        return response.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
