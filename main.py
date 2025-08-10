from fastapi import FastAPI, File, UploadFile, Depends
from PyPDF2 import PdfReader
from docx import Document
import pytesseract
from pdf2image import convert_from_bytes
import io

from requests import Session

from database import SessionLocal
from llm_parser import llm_extract_cv_info, client
from models import Candidate
from routes.job import router as job_router
from routes.application import router as  application_router
from routes.candidate import router as candidate_router
from routes.user import router as user_router
from routes.interview import router as interview_router



app = FastAPI()

app.include_router(job_router, prefix="/job", tags=["Job"])
app.include_router(application_router, prefix="/application", tags=["Application"])
app.include_router(candidate_router, prefix="/candidate", tags=["Candidate"])
app.include_router(interview_router, prefix="/interviews", tags=["interviews"])


app.include_router(user_router, prefix="/user", tags=["User"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


