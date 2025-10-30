from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware

# -------------------------------------------------
# INIT
# -------------------------------------------------
app = FastAPI(
    title="Agent Builder 01 — FastAPI + Supabase",
    description="API service for managing users and items with Supabase authentication",
    version="0.1.0"
)

# -------------------------------------------------
# SECURITY (ovo dodaje 🔒 Authorize u Swagger)
# -------------------------------------------------
security = HTTPBearer()

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    Dummy provjera tokena – ovdje možeš kasnije dodati pravu verifikaciju sa Supabase-om.
    """
    token = credentials.credentials
    if not token or len(token) < 20:  # samo primjer validacije
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing token"
        )
    return token

# -------------------------------------------------
# CORS (dozvoljava pozive izvana)
# -------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------------------------------
# ROUTES
# -------------------------------------------------
@app.get("/health", tags=["default"])
def health():
    return {"status": "ok"}

@app.get("/items", tags=["default"], dependencies=[Depends(verify_token)])
def list_items():
    return {"items": ["example_item_1", "example_item_2"]}

@app.post("/items", tags=["default"], dependencies=[Depends(verify_token)])
def create_item():
    return {"message": "Item created successfully!"}

@app.get("/")
def root():
    return {"message": "Welcome to Agent Builder 01 API"}
