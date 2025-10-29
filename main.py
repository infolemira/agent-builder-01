# GET ruta za dohvaćanje svih klijenata
from fastapi import HTTPException

@app.get("/api/v1/clients", tags=["Clients"])
def get_clients():
    try:
        response = supabase.table("clients").select("*").execute()
        if not response.data:
            return {"message": "No clients found"}
        return response.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
