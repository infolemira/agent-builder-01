# supabase_service.py
import os
from typing import Optional
from dotenv import load_dotenv
from supabase.client import create_client, Client  # <- OVDJE JE BITNA PROMJENA

# učitaj .env varijable
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")

if not SUPABASE_URL or not SUPABASE_ANON_KEY:
    raise RuntimeError("Missing SUPABASE_URL or SUPABASE_ANON_KEY in environment.")

def get_supabase(token: Optional[str] = None) -> Client:
    """
    Kreira Supabase klijent. Ako pošalješ korisnički JWT token,
    RLS će se automatski primijeniti na sve upite.
    """
    client: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
    if token:
        client.postgrest.auth(token)
    return client

async def get_user_from_token(token: str):
    """
    Dohvaća Supabase korisnika na temelju JWT tokena.
    """
    sb = get_supabase()
    res = await sb.auth.get_user(token)
    return res.user if hasattr(res, "user") else None
