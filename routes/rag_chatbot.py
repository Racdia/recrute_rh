# routes/rag_chatbot.py
import os
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from pinecone import Pinecone

# ── Env config ─────────────────────────────────────────────────────────
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_INDEX   = os.getenv("PINECONE_INDEX", "candidats-rh-768")
os.environ.setdefault("HF_HUB_ENABLE_HF_TRANSFER", "0")          # important on Windows
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")         # force offline
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("HF_HUB_ENABLE_HF_TRANSFER", "0")    # évite le driver spécial
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")

EMBED_MODEL = os.getenv(
    "EMBED_MODEL",
    "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"  # <= même modèle que l’upsert !
)
# ⚠️ Keep the SAME model here as the one you used to upsert into Pinecone.
# If you’re not sure which you used, re-run your upsert script with this one.

if not PINECONE_API_KEY:
    raise RuntimeError("PINECONE_API_KEY manquant")

pc = Pinecone(api_key=PINECONE_API_KEY)
index = pc.Index(PINECONE_INDEX)

# Lazy loader for the SentenceTransformer (download on first use only)
_embedder = None
_embed_dim = None
def get_embedder():
    global _embedder, _embed_dim
    if _embedder is None:
        from sentence_transformers import SentenceTransformer
        _embedder = SentenceTransformer(EMBED_MODEL)
        _embed_dim = _embedder.get_sentence_embedding_dimension()
        print(f"[RAG] Modèle chargé: {EMBED_MODEL} | dim={_embed_dim}")
    return _embedder

# Optional LLM
USE_OPENAI = bool(os.getenv("OPENAI_API_KEY"))
if USE_OPENAI:
    from openai import OpenAI
    oai = OpenAI()

def call_llm(prompt: str, temperature: float = 0.2, max_tokens: int = 600) -> str:
    if USE_OPENAI:
        resp = oai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Tu es un assistant RH. Réponds en français de manière précise et utile."},
                {"role": "user", "content": prompt},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return resp.choices[0].message.content.strip()
    return "⚠️ LLM non configuré (ajoute OPENAI_API_KEY pour activer la génération)."

SIM_THRESHOLD = float(os.getenv("RAG_SIM_THRESHOLD", "0.30"))
TOP_K = int(os.getenv("RAG_TOP_K", "5"))

class AskRequest(BaseModel):
    question: str
    top_k: Optional[int] = None

class Source(BaseModel):
    faq_id: int
    question: str
    answer: str
    score: float

class AskResponse(BaseModel):
    answer: str
    sources: List[Source]

router = APIRouter(prefix="/chatbot", tags=["chatbot"])

def build_rag_prompt(user_q: str, contexts: List[Source]) -> str:
    ctx_txt = "\n\n".join(f"[{i+1}] Q: {c.question}\nR: {c.answer}" for i, c in enumerate(contexts))
    return f"""Tu es un assistant RH. Utilise UNIQUEMENT le contexte ci-dessous pour répondre clairement à la question.
Si l'information n'est pas présente, dis-le et propose la démarche à suivre.

# Question
{user_q}

# Contexte (FAQ)
{ctx_txt}

# Consignes
- Réponds en français
- Sois précis, utile et concis
- Liste des étapes en puces si pertinent
- Ne fabrique pas d’informations hors du contexte
"""

@router.post("/ask", response_model=AskResponse)
def ask_faq(req: AskRequest):
    q = (req.question or "").strip()
    if not q:
        raise HTTPException(status_code=400, detail="Question vide")

    embedder = get_embedder()  # triggers 1st download here (single process)
    try:
        q_vec = embedder.encode([q], normalize_embeddings=True)[0].tolist()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur d'embedding: {e}")

    k = req.top_k or TOP_K
    try:
        res = index.query(vector=q_vec, top_k=k, include_values=False, include_metadata=True)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur Pinecone: {e}")

    matches = getattr(res, "matches", []) or res.get("matches", [])
    if not matches:
        return AskResponse(answer="Je n’ai rien trouvé dans la FAQ pour cette question.", sources=[])

    picked: List[Source] = []
    for m in matches:
        score = getattr(m, "score", None) or m.get("score", 0.0)
        meta  = getattr(m, "metadata", None) or m.get("metadata", {}) or {}
        if score is not None and score < SIM_THRESHOLD:
            continue
        picked.append(Source(
            faq_id=int(meta.get("faq_id", -1)),
            question=str(meta.get("question", "")),
            answer=str(meta.get("answer", "")),
            score=float(score or 0.0),
        ))

    if not picked:
        return AskResponse(answer="Je n’ai rien trouvé de suffisamment pertinent dans la FAQ.", sources=[])

    prompt = build_rag_prompt(q, picked)
    answer = call_llm(prompt)
    return AskResponse(answer=answer, sources=picked[:3])
