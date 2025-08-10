from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, Float, JSON, ARRAY, DateTime, Text, ForeignKey
from datetime import datetime

from sqlalchemy.orm import relationship

Base = declarative_base()

class Candidate(Base):
    __tablename__ = "candidates"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    emails = Column(ARRAY(String))
    phones = Column(ARRAY(String))
    linkedin = Column(ARRAY(String))
    address = Column(String)
    education = Column(JSON)
    experience = Column(JSON)
    skills = Column(ARRAY(String))
    languages = Column(ARRAY(String))
    video_path = Column(String, nullable=True)   # <--- AJOUT ICI


from sqlalchemy import Column, Integer, String, Float, JSON, Text, DateTime, ForeignKey
from datetime import datetime

class Application(Base):
    __tablename__ = "applications"
    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(Integer, ForeignKey("candidates.id"))
    job_id = Column(Integer)
    video_path = Column(String)             # <--- AJOUT ICI !
    softskills = Column(JSON)
    cv_score = Column(Float)
    softskills_score = Column(Float)
    tech_score = Column(Float)
    global_score = Column(Float)
    feedback = Column(Text)
    transcript = Column(Text)
    status = Column(String, default="en attente")  # "en attente", "validé", "refusé"
    rh_note = Column(String, nullable=True)
    mini_report = Column(Text, nullable=True)
    date_applied = Column(DateTime, default=datetime.utcnow)
    interview = relationship("Interview", uselist=False, back_populates="application")


from sqlalchemy import Column, Integer, String, Text, JSON


class JobOffer(Base):
    __tablename__ = "job_offers"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(Text)
    diploma_type = Column(String)      # Type de diplôme (Licence, Master, etc.)
    filiere = Column(String)           # Filière ou spécialité
    education_level = Column(String)   # Niveau d'études (optionnel)
    experience_years = Column(Integer) # Années d'expérience (optionnel)
    requirements = Column(JSON)


class User(Base):
    __tablename__ = "users"  # ou "rh_users" si tu veux restreindre à RH uniquement

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(String, default="rh")  # optionnel : "rh", "admin", etc.

class Interview(Base):
        __tablename__ = "interviews"

        id = Column(Integer, primary_key=True, index=True)
        application_id = Column(Integer, ForeignKey("applications.id"), nullable=False)
        interview_datetime = Column(DateTime, nullable=False)
        location = Column(String, nullable=False)

        # Relation vers Application
        application = relationship("Application", back_populates="interview")

class FAQ(Base):
    __tablename__ = "faq"

    id = Column(Integer, primary_key=True, index=True)
    question = Column(Text, nullable=False)
    answer   = Column(Text, nullable=False)