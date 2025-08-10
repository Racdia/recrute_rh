from pydantic import BaseModel, EmailStr


class RefuseRequest(BaseModel):
    email: EmailStr
    name: str
    job: str
    feedback: str