from sqlalchemy import create_engine

DATABASE_URL = "postgresql://recrut_user:123456@52.89.55.119:5432/recrut"


if __name__ == "__main__":
    try:
        engine = create_engine(DATABASE_URL)
        with engine.connect() as connection:
            print("✅ Connexion réussie à la base PostgreSQL EC2 !")
    except Exception as e:
        print("❌ Erreur de connexion :", e)