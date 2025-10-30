# 🧠 Agent Builder 01 — FastAPI + Supabase

Full-stack backend API napravljen pomoću **FastAPI** i **Supabase** koji omogućava registraciju, prijavu i upravljanje korisničkim zadacima (*items*).

---

## 🚀 Deployment

Aplikacija je aktivna na:

🔗 **Live API:** [https://agent-builder-01.onrender.com](https://agent-builder-01.onrender.com)  
📘 **Docs (Swagger UI):** [https://agent-builder-01.onrender.com/docs](https://agent-builder-01.onrender.com/docs)

---

## ⚙️ Tehnologije

- **FastAPI** — Python web framework
- **Supabase** — baza podataka i autentifikacija (PostgreSQL + Auth)
- **Render.com** — hosting platforma
- **Pydantic** — validacija modela i schema
- **HTTPBearer** — sigurnosni mehanizam za JWT tokene

---

## 🔐 Autentifikacija

Korisnici se autentificiraju putem **Supabase Auth** servisa (Email + Password).

JWT token (`access_token`) se dobiva nakon uspješnog logina i koristi se za pristup zaštićenim endpointima.

### Signup (registracija)
