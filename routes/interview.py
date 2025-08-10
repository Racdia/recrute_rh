from datetime import datetime

from pydantic import BaseModel, EmailStr
from fastapi import Path, Depends, Body, APIRouter
from requests import Session

from database import SessionLocal
from models import Application, Interview, Candidate, JobOffer


router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
class InterviewRequest(BaseModel):
    email: EmailStr
    name: str
    job: str
    interview_datetime: str
    location: str

@router.get("/", summary="Liste de tous les entretiens planifiés")
def list_interviews(db: Session = Depends(get_db)):
    # On joint Interview → Application → Candidate → JobOffer
    results = (
        db.query(Interview, Application, Candidate, JobOffer)
          .join(Application, Interview.application_id == Application.id)
          .join(Candidate, Application.candidate_id == Candidate.id)
          .join(JobOffer, Application.job_id == JobOffer.id)
          .all()
    )

    interviews = []
    for interview, app, cand, job in results:
        interviews.append({
            "interview_id": interview.id,
            "application_id": app.id,
            "candidate_name": cand.name,
            "job_title": job.title,
            "interview_datetime": interview.interview_datetime.isoformat(),
            "location": interview.location,
        })
    return interviews
# @router.post("/{app_id}/schedule-interview/")
# def schedule_interview(
#     app_id: int = Path(...),
#     payload: InterviewRequest = Body(...),
#     db: Session = Depends(get_db)
# ):
#     application = db.query(Application).filter(Application.id == app_id).first()
#     if not application:
#         return {"error": "Application not found"}
#
#     # Parse datetime (depuis string comme "2025-08-10 10:00")
#     try:
#         dt = datetime.strptime(payload.interview_datetime, "%d/%m/%Y à %H:%M")
#     except Exception as e:
#         return {"error": "Format de date invalide"}
#
#     # Enregistre l’entretien
#     interview = Interview(
#         application_id=app_id,
#         interview_datetime=dt,
#         location=payload.location
#     )
#     db.add(interview)
#     db.commit()
#
#     # Envoie l’email
#     subject = "📅 Convocation à un entretien"
#     body = f"""
#         <h3>Bonjour {payload.name},</h3>
#         <p>Vous êtes convoqué à un entretien pour le poste de <b>{payload.job}</b>.</p>
#         <p><b>Date et heure :</b> {payload.interview_datetime}<br>
#         <b>Lieu :</b> {payload.location}</p>
#         <p>Merci de confirmer votre présence.</p>
#     """
#     send_email(subject=subject, body=body, to_email=payload.email)
#
#     return {"message": "Entretien enregistré et email envoyé"}
