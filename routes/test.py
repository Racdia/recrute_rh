from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from models import JobOffer
from database import SessionLocal
import openai  # ou ton LLM préféré

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/job/{job_id}/generate-quiz/")
def generate_quiz(job_id: int, db: Session = Depends(get_db)):
    job = db.query(JobOffer).filter(JobOffer.id == job_id).first()
    if not job:
        return {"error": "Job not found"}
    # Prompt LLM pour générer des questions adaptées au poste
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
