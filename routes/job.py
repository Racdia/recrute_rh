import os

import openai
from fastapi import APIRouter, Depends, Form
from sqlalchemy.orm import Session
from database import SessionLocal
from models import JobOffer
import json

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/create/")
def create_job_offer(
    title: str = Form(...),
    description: str = Form(""),
    diploma_type: str = Form(""),
    filiere: str = Form(""),
    education_level: str = Form(""),
    experience_years: int = Form(0),
    requirements: str = Form("[]"),
    db: Session = Depends(get_db)
):
    try:
        requirements_json = json.loads(requirements)
    except Exception:
        return {"error": "Le champ requirements doit être un JSON valide"}
    job = JobOffer(
        title=title,
        description=description,
        diploma_type=diploma_type,
        filiere=filiere,
        education_level=education_level,
        experience_years=experience_years,
        requirements=requirements_json
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return {"id": job.id, "title": job.title, "message": "Poste créé avec succès"}

@router.get("/list/")
def list_job_offers(db: Session = Depends(get_db)):
    jobs = db.query(JobOffer).all()
    return [
        {
            "id": job.id,
            "title": job.title,
            "description": job.description
            # tu peux ajouter plus de champs si besoin
        }
        for job in jobs
    ]

@router.get("/{job_id}/generate-quiz/")
def generate_quiz(job_id: int, db: Session = Depends(get_db)):

    job = db.query(JobOffer).filter(JobOffer.id == job_id).first()
    if not job:
        return {"error": "Job not found"}
    # Prompt LLM pour générer des questions adaptées au poste
    OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
    if not OPENAI_API_KEY:
        raise Exception("La clé API OpenAI n'est pas trouvée dans les variables d'environnement !")

    openai.api_key = OPENAI_API_KEY
    prompt = f"Génère 3 questions QCM de test technique sur le métier '{job.title}'. Prérequis : {job.requirements}. Format JSON: " \
             f'[{{"question":"", "options":["","","",""], "answer":""}}, ...]'
    response = openai.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7
    )
    try:
        quiz = eval(response.choices[0].message.content)
        return {"questions": quiz}
    except Exception as ex:
        return {"error": f"Parsing error: {ex}", "raw": response.choices[0].message.content}
