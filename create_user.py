from passlib.hash import sha256_crypt
from database import SessionLocal
from models import User

def create_user():
    db = SessionLocal()

    password = "123456"
    hashed = sha256_crypt.hash(password)
    new_user = User(username="admin", hashed_password=hashed)
    db.add(new_user)
    db.commit()
    db.close()
    print("✅ Utilisateur RH créé avec succès")

if __name__ == "__main__":
    create_user()
