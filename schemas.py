from pydantic import BaseModel, EmailStr

class ClientIn(BaseModel):
    name: str
    email: EmailStr
