import json
import os
import shutil

from fastapi import APIRouter, UploadFile, File, Depends, Form
from sqlalchemy.orm import Session
from database import SessionLocal
from llm_parser import llm_extract_cv_info
from models import Candidate
import io
from PyPDF2 import PdfReader
from docx import Document
import pytesseract
from pdf2image import convert_from_bytes

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/upload-cv/")
async def upload_cv(
    file: UploadFile = File(...),
    job_id: int = Form(None),
    db: Session = Depends(get_db)
):
    content = await file.read()
    filename = file.filename
    text = ""
    if filename.lower().endswith(".pdf"):
        try:
            reader = PdfReader(io.BytesIO(content))
            for page in reader.pages:
                txt = page.extract_text()
                if txt:
                    text += txt + "\n"
        except Exception as e:
            print("Erreur extraction texte PDF:", e)
        if not text.strip():
            images = convert_from_bytes(content)
            for image in images:
                text += pytesseract.image_to_string(image)
    elif filename.lower().endswith(".docx"):
        try:
            doc = Document(io.BytesIO(content))
            for para in doc.paragraphs:
                text += para.text + "\n"
        except Exception as e:
            print("Erreur extraction docx:", e)
    else:
        return {"error": "Format non supporté (PDF ou DOCX uniquement)"}

    text = text.strip().replace("\x00", "")

    try:
        infos_cv = llm_extract_cv_info(text)
    except Exception as ex:
        return {"error": f"Erreur parsing via LLM: {str(ex)}"}

    candidate = Candidate(
        name=infos_cv.get("name"),
        emails=json.dumps(infos_cv.get("emails", [])),
        phones=json.dumps(infos_cv.get("phones", [])),
        linkedin=json.dumps(infos_cv.get("linkedin", [])),
        address=infos_cv.get("address"),
        education=json.dumps(infos_cv.get("education", [])),
        experience=json.dumps(infos_cv.get("experience", [])),
        skills=json.dumps(infos_cv.get("skills", [])),
        languages=json.dumps(infos_cv.get("languages", []))
    )

    db.add(candidate)
    db.commit()
    db.refresh(candidate)

    return {
        "candidate_id": candidate.id,
        "name": candidate.name,
        "infos": infos_cv,
        "message": "Candidat ajouté en base avec succès !"
    }


VIDEO_FOLDER = "./data/videos"
os.makedirs(VIDEO_FOLDER, exist_ok=True)

@router.post("/upload-video/")
async def upload_video(
    candidate_id: int = Form(...),
    video: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    filename = f"{candidate_id}_{video.filename}"
    save_path = os.path.join(VIDEO_FOLDER, filename)
    with open(save_path, "wb") as buffer:
        shutil.copyfileobj(video.file, buffer)

    # 1. Récupérer le candidat dans la base
    candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
    if not candidate:
        return {"error": "Candidat non trouvé"}

    # 2. Mettre à jour le champ video_path
    candidate.video_path = save_path

    # 3. Commit des modifications
    db.commit()
    db.refresh(candidate)

    return {
        "status": "ok",
        "video_path": save_path,
        "candidate_id": candidate.id,
        "message": "Vidéo enregistrée et liée au candidat avec succès !"
    }
