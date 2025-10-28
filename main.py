from fastapi import FastAPI
from supabase_service import supabase
from schemas import ClientIn

app = FastAPI()

@app.get('/health')
def health():
    return {'ok': True, 'msg': 'API radi'}

@app.post('/api/v1/clients')
def add_client(data: ClientIn):
    res = supabase.table('clients').insert(data.model_dump()).execute()
    return res.data
