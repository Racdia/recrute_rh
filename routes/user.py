from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from passlib.hash import sha256_crypt
from database import SessionLocal
from models import User
from schemas import LoginRequest

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/login")
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == payload.username).first()
    if user and sha256_crypt.verify(payload.password, user.hashed_password):
        return {"message": "Login success"}
    raise HTTPException(status_code=401, detail="Identifiants invalides")
