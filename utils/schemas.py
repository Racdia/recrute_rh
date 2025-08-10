from pydantic import BaseModel, EmailStr

class AcceptRequest(BaseModel):
    email: EmailStr
    name: str
    job: str