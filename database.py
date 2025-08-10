from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "postgresql://recrut_user:123456@52.89.55.119:5432/recrut"

#DATABASE_URL = "postgresql://postgres:racine60%40@127.0.0.1:5432/recrut"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
