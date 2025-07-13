from fastapi import FastAPI, File, UploadFile
from PyPDF2 import PdfReader
from docx import Document
import pytesseract
from pdf2image import convert_from_bytes
import io

from llm_parser import llm_extract_cv_info, client

app = FastAPI()

@app.post("/upload-cv/")
async def upload_cv(file: UploadFile = File(...)):
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

    # Nettoie le texte
    text = text.strip().replace("\x00", "")

    # Appel du LLM pour extraction structurée
    try:
        print("Clé API utilisée :", client.api_key[:10] + "...")

        infos_cv = llm_extract_cv_info(text)
    except Exception as ex:
        return {"error": f"Erreur parsing via LLM: {str(ex)}"}

    return {
        "filename": filename,
        "size": len(content),
        "cv_info": infos_cv,
        "text_excerpt": text[:2000]
    }
