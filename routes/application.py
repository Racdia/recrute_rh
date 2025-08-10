from datetime import datetime
from http.client import HTTPException
from fastapi import Path

import openai
import os
import shutil
import time

from fastapi import APIRouter, Form, UploadFile, File, Depends, Body
from sqlalchemy import func
from sqlalchemy.orm import Session

from llm_parser import compute_cv_score, analyze_soft_skills_llm, generate_candidate_summary_openai, \
    generate_learning_suggestions_openai
from models import Application, Candidate, JobOffer, Interview
from database import SessionLocal
from routes.interview import InterviewRequest
from utils.email_utils import  send_email_with_retry
from utils.refuseRequest import RefuseRequest
from utils.schemas import AcceptRequest

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
openai.api_key = OPENAI_API_KEY
VIDEO_FOLDER = "./data/videos"
os.makedirs(VIDEO_FOLDER, exist_ok=True)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def transcribe_video_openai(video_path):
    with open(video_path, "rb") as audio_file:
        transcript = openai.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file,
            response_format="text"
        )
    return transcript

router = APIRouter()

@router.post("/apply/")
async def apply(
    candidate_id: int = Form(...),
    job_id: int = Form(...),
    tech_score: float = Form(...),
    video: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    # 1. Upload vidéo + transcription
    video_filename = f"{candidate_id}_{job_id}_{video.filename}"
    video_path = os.path.abspath(os.path.join(VIDEO_FOLDER, video_filename))
    with open(video_path, "wb") as buffer:
        shutil.copyfileobj(video.file, buffer)
    time.sleep(1)
    transcript = ""
    try:
        transcript = transcribe_video_openai(video_path)
    except Exception as e:
        print("Erreur transcription OpenAI :", e)

    # 2. Charger les données nécessaires
    candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
    job = db.query(JobOffer).filter(JobOffer.id == job_id).first()

    if not candidate or not job:
        return {"error": "Candidat ou Job introuvable"}

    # 3. Notation automatique
    cv_score = compute_cv_score(candidate, job)
    softskills_infos = analyze_soft_skills_llm(transcript, job)
    global_score = 0.4 * cv_score + 0.3 * softskills_infos["softskills_score"] + 0.3 * tech_score

    scores = {
        "cv_score": cv_score,
        "softskills_score": softskills_infos["softskills_score"],
        "tech_score": tech_score,
        "global_score": global_score,
        "softskills": softskills_infos["softskills"],
        "feedback": softskills_infos["feedback"],
    }

    # 4. Génération du mini-rapport IA
    mini_report = generate_candidate_summary_openai(candidate, job, scores, transcript)

    # 5. Création Application (mini_report inclus)
    application = Application(
        candidate_id=candidate_id,
        job_id=job_id,
        video_path=video_path,
        transcript=transcript,
        softskills=softskills_infos["softskills"],
        softskills_score=softskills_infos["softskills_score"],
        feedback=softskills_infos["feedback"],
        cv_score=cv_score,
        tech_score=tech_score,
        global_score=global_score,
        mini_report=mini_report
    )
    db.add(application)
    db.commit()
    db.refresh(application)

    return {
        "application_id": application.id,
        "cv_score": cv_score,
        "softskills": softskills_infos["softskills"],
        "softskills_score": softskills_infos["softskills_score"],
        "feedback": softskills_infos["feedback"],
        "global_score": global_score,
        "transcript": transcript,
        "mini_report": mini_report,
        "message": "Candidature créée avec notation automatique et mini-rapport IA."
    }



@router.post("/submit-tech-test/")
async def submit_tech_test(
    application_id: int = Form(...),
    score: float = Form(...),
    feedback: str = Form(""),
    db: Session = Depends(get_db)
):
    application = db.query(Application).filter(Application.id == application_id).first()
    if not application:
        return {"error": "Application non trouvée"}

    application.tech_score = score
    if feedback:
        application.feedback = (application.feedback or "") + f"\n[TECH TEST] {feedback}"
    db.commit()
    db.refresh(application)
    return {
        "application_id": application.id,
        "tech_score": application.tech_score,
        "feedback": application.feedback,
        "message": "Test technique enregistré"
    }

@router.get("/list/")
def list_applications(
    job_id: int = None,
    status: str = None,
    db: Session = Depends(get_db)
):
    query = db.query(Application, Candidate, JobOffer)\
        .join(Candidate, Application.candidate_id == Candidate.id)\
        .join(JobOffer, Application.job_id == JobOffer.id)

    if job_id:
        query = query.filter(Application.job_id == job_id)
    if status:
        query = query.filter(func.lower(Application.status) == status.lower())  # ✅ filtrage insensible à la casse

    results = query.all()
    apps = []
    for app, cand, job in results:
        apps.append({
            "application_id": app.id,
            "candidate_id": cand.id,
            "candidate_name": cand.name,
            "email": (
                        ''.join(cand.emails).replace('"', '').replace('[', '').replace(']', '').strip()
                        if isinstance(cand.emails, list)
                        else str(cand.emails).strip()
                    ),
            "job_id": job.id,
            "job_title": job.title,
            "cv_score": app.cv_score,
            "softskills_score": app.softskills_score,
            "tech_score": app.tech_score,
            "global_score": app.global_score,
            "feedback": app.feedback,
            "status": app.status,
            "softskills": app.softskills,
            "transcript": app.transcript,
            "mini_report": app.mini_report,
            "date_applied":app.date_applied,
            "video_path": app.video_path,
        })
    return apps

@router.post("/{app_id}/accept/")
def accept_application(
    app_id: int = Path(...),
    payload: AcceptRequest = Body(...),
    db: Session = Depends(get_db)
):
    application = db.query(Application).filter(Application.id == app_id).first()
    if not application:
        return {"error": "Application not found"}

    application.status = "validé"
    db.commit()
    db.refresh(application)

    # ✅ Envoi d'email de convocation avec les données reçues
    subject = "🎉 Votre candidature a été retenue"
    body = f"""
        <h3>Bonjour {payload.name},</h3>
        <p>Nous avons le plaisir de vous informer que votre candidature au poste de <b>{payload.job}</b> a été <b style="color:green;">acceptée</b>.</p>
        <p>Nous souhaiterions vous rencontrer pour un entretien. Merci de consulter vos e-mails prochainement pour plus de détails.</p>
        <p>À bientôt,<br>L'équipe RH</p>
    """

    SMTP_HOST = os.getenv("SMTP_HOST", "smtp.mailtrap.io")
    SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
    SMTP_USER = os.getenv("SMTP_USER", "votre_user_mailtrap")
    SMTP_PASS = os.getenv("SMTP_PASS", "votre_pass_mailtrap")
    sent = send_email_with_retry(
        payload.email,
        subject,
        body,
        SMTP_HOST,
        SMTP_PORT,
        SMTP_USER,
        SMTP_PASS,
        3,
        5
    )

    if not sent:
        return {"message": "Entretien enregistré, email en attente d'envoi (échec SMTP)"}

    return {"message": "Entretien enregistré et email envoyé avec succès"}



@router.post("/{app_id}/refuse/")
def refuse_application(
    app_id: int = Path(...),
    payload: RefuseRequest = Body(...),
    db: Session = Depends(get_db)
):
    application = db.query(Application).filter(Application.id == app_id).first()
    if not application:
        return {"error": "Application not found"}

    application.status = "refusé"
    db.commit()
    db.refresh(application)

    # 💡 Suggestions dynamiques via LLM
    suggestions = generate_learning_suggestions_openai(payload.name, payload.job, payload.feedback)

    subject = "❌ Votre candidature n'a pas été retenue"
    body = f"""
        <h3>Bonjour {payload.name},</h3>
        <p>Merci d’avoir postulé pour le poste de <b>{payload.job}</b>. Après analyse de votre profil, nous ne pouvons pas donner une suite favorable à votre candidature.</p>
        <p><b>Commentaire RH :</b><br>{payload.feedback}</p>
        <p><b>Suggestions de formation :</b><br>{suggestions}</p>
        <p>Nous vous souhaitons plein succès dans vos projets professionnels.<br>L'équipe RH</p>
    """

    SMTP_HOST = os.getenv("SMTP_HOST", "smtp.mailtrap.io")
    SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
    SMTP_USER = os.getenv("SMTP_USER", "votre_user_mailtrap")
    SMTP_PASS = os.getenv("SMTP_PASS", "votre_pass_mailtrap")
    sent = send_email_with_retry(
        payload.email,
        subject,
        body,
        SMTP_HOST,
        SMTP_PORT,
        SMTP_USER,
        SMTP_PASS,
        3,
        5
    )

    if not sent:
        return {"message": "Entretien enregistré, email en attente d'envoi (échec SMTP)"}

    return {"message": "Entretien enregistré et email envoyé avec succès"}


@router.post("/{app_id}/add-note/")
def add_rh_note(app_id: int, note: str, db: Session = Depends(get_db)):
    application = db.query(Application).filter(Application.id == app_id).first()
    if not application:
        return {"error": "Application not found"}
    application.rh_note = note
    db.commit()
    db.refresh(application)
    return {"message": "Note added", "application_id": app_id}

@router.post("/{app_id}/schedule-interview/")
def schedule_interview(
    app_id: int = Path(...),
    payload: InterviewRequest = Body(...),
    db: Session = Depends(get_db)
):
    application = db.query(Application).filter(Application.id == app_id).first()
    if not application:
        return {"error": "Application not found"}

    # Parse datetime (depuis string comme "2025-08-10 10:00")
    try:
        dt = datetime.strptime(payload.interview_datetime, "%d/%m/%Y à %H:%M")
    except Exception as e:
        return {"error": "Format de date invalide"}

    # Enregistre l’entretien
    interview = Interview(
        application_id=app_id,
        interview_datetime=dt,
        location=payload.location
    )
    db.add(interview)
    db.commit()

    # Envoie l’email
    subject = "📅 Convocation à un entretien"
    body = f"""
        <h3>Bonjour {payload.name},</h3>
        <p>Vous êtes convoqué à un entretien pour le poste de <b>{payload.job}</b>.</p>
        <p><b>Date et heure :</b> {payload.interview_datetime}<br>
        <b>Lieu :</b> {payload.location}</p>
        <p>Merci de confirmer votre présence.</p>
    """
    SMTP_HOST = os.getenv("SMTP_HOST", "smtp.mailtrap.io")
    SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
    SMTP_USER = os.getenv("SMTP_USER", "votre_user_mailtrap")
    SMTP_PASS = os.getenv("SMTP_PASS", "votre_pass_mailtrap")
    print(SMTP_HOST)
    print(SMTP_USER)
    sent = send_email_with_retry(
        payload.email,
        subject,
        body,
        SMTP_HOST,
        SMTP_PORT,
        SMTP_USER,
        SMTP_PASS,
        3,
        5
    )

    if not sent:
        return {"message": "Entretien enregistré, email en attente d'envoi (échec SMTP)"}

    return {"message": "Entretien enregistré et email envoyé avec succès"}
