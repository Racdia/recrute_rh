# routers/rag.py
import os
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException
from dotenv import load_dotenv
import pinecone
from sentence_transformers import SentenceTransformer
from openai import OpenAI  # client OpenAI (ou remplace par ton LLM préféré)

load_dotenv()

router = APIRouter(prefix="/rag", tags=["chatbot-rag"])

# --- ENV ---
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_ENV = os.getenv("PINECONE_ENVIRONMENT", "us-east-1")
PINECONE_INDEX = os.getenv("PINECONE_INDEX", "candidats-rh")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# --- Clients globaux (chargés 1x) ---
pinecone.init(api_key=PINECONE_API_KEY, environment=PINECONE_ENV)
index = pinecone.Index(PINECONE_INDEX)

embed_model = SentenceTransformer("sentence-transformers/all-mpnet-base-v2")
llm = OpenAI(api_key=OPENAI_API_KEY)

class AskPayload(BaseModel):
    query: str
    top_k: int = 5
    min_score: float = 0.2  # filtre de pertinence (0..1), ajuste si besoin
    # éventuellement: language: str, persona: str, etc.

RAG_SYSTEM_PROMPT = (
    "Tu es un assistant RH. Réponds uniquement à partir des extraits (FAQ) fournis.\n"
    "Si l'information n'apparaît pas dans les sources, dis que tu ne la trouves pas.\n"
    "Sois concis, clair et utile. Réponds en français."
)

def format_context(matches):
    blocks = []
    for m in matches:
        meta = m.get("metadata", {})
        q = meta.get("question", "")
        a = meta.get("answer", "")
        blocks.append(f"- [FAQ #{meta.get('faq_id')}] Q: {q}\n  R: {a}")
    return "\n\n".join(blocks)

@router.post("/ask")
def rag_ask(payload: AskPayload):
    query = payload.query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="query vide")

    # 1) Embedding de la question
    q_emb = embed_model.encode([query])[0].tolist()

    # 2) Retrieval (similarité)
    res = index.query(
        vector=q_emb,
        top_k=payload.top_k,
        include_values=False,
        include_metadata=True
    )

    matches = [m for m in res.get("matches", []) if m.get("score", 0) >= payload.min_score]
    if not matches:
        return {
            "answer": "Je n’ai pas trouvé d’information pertinente dans la FAQ. Peux-tu reformuler ta question ?",
            "sources": [],
        }

    # 3) Construit le contexte à donner au LLM
    context_text = format_context(matches)

    # 4) Prompt LLM (OpenAI ici, remplaçable)
    messages = [
        {"role": "system", "content": RAG_SYSTEM_PROMPT},
        {"role": "user", "content": f"Question: {query}\n\nSources:\n{context_text}\n\nRéponse:"}
    ]
    completion = llm.chat.completions.create(
        model="gpt-4o-mini",  # rapide/éco ; change selon ton compte
        messages=messages,
        temperature=0.2,
        max_tokens=350
    )
    answer = completion.choices[0].message.content.strip()

    # 5) Retourne la réponse + les sources citées
    sources = [
        {
            "faq_id": m["metadata"]["faq_id"],
            "question": m["metadata"]["question"],
            "score": m["score"]
        }
        for m in matches
    ]
    return {"answer": answer, "sources": sources}
