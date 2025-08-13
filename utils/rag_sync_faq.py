# utils/rag_sync_faq.py
import os
import sys
import psycopg2
from sentence_transformers import SentenceTransformer
from pinecone import Pinecone, ServerlessSpec

# --- ENV ---
PG_CONN          = os.getenv("PG_CONN", "dbname=recrut user=recrut_user password=123456 host=52.89.55.119 port=5432")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_INDEX   = os.getenv("PINECONE_INDEX", "candidats-rh-768")
PINECONE_REGION  = os.getenv("PINECONE_REGION", os.getenv("PINECONE_ENVIRONMENT", "us-east-1"))

if not PINECONE_API_KEY:
    print("❌ PINECONE_API_KEY manquant.")
    sys.exit(1)

# --- Pinecone client (v5) ---
pc = Pinecone(api_key=PINECONE_API_KEY)

# --- Modèle d'embedding (768d) ---
# Si tu as un modèle local, passe le chemin dossier à SentenceTransformer(...)
model = SentenceTransformer("sentence-transformers/paraphrase-multilingual-mpnet-base-v2")
#EMBED_MODEL = os.getenv("EMBED_MODEL", "sentence-transformers/paraphrase-multilingual-mpnet-base-v2")

embed_dim = model.get_sentence_embedding_dimension()

def ensure_index(name: str, dim: int):
    """Crée l'index s'il n'existe pas, vérifie la dimension sinon."""
    try:
        desc = pc.describe_index(name)
    except Exception:
        desc = None

    if desc is None:
        print(f"ℹ️ Index '{name}' introuvable, création en {dim} dims…")
        pc.create_index(
            name=name,
            dimension=dim,
            metric="cosine",
            spec=ServerlessSpec(cloud="aws", region=PINECONE_REGION),
        )
        # petit wait implicite : pas obligatoire en serverless
        desc = pc.describe_index(name)
        print(f"✅ Index créé: {name}")

    # Selon la version, desc peut être obj ou dict
    index_dim = getattr(desc, "dimension", None) if hasattr(desc, "dimension") else desc.get("dimension")
    if index_dim != dim:
        raise ValueError(f"❌ Dimension mismatch: modèle={dim}, index={index_dim}. Recrée l’index à {dim}.")

    return pc.Index(name)

index = ensure_index(PINECONE_INDEX, embed_dim)

def fetch_faq_rows():
    conn = psycopg2.connect(PG_CONN)
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, question, answer FROM faq ORDER BY id;")
            return cur.fetchall()
    finally:
        conn.close()

def build_doc(q: str, a: str) -> str:
    return f"Question: {q}\nRéponse: {a}"

def upsert_faq(batch_size: int = 100):
    rows = fetch_faq_rows()
    if not rows:
        print("Aucune FAQ trouvée.")
        return

    texts = [build_doc(q, a) for (_id, q, a) in rows]
    embs = model.encode(texts, batch_size=32, show_progress_bar=True, normalize_embeddings=True)

    vectors = []
    for (row, emb) in zip(rows, embs):
        _id, q, a = row
        vectors.append({
            "id": f"faq-{_id}",
            "values": emb.tolist(),
            "metadata": {"faq_id": int(_id), "question": q, "answer": a}
        })

    print(f"⬆️ Upsert {len(vectors)} vecteurs vers '{PINECONE_INDEX}'…")
    for i in range(0, len(vectors), batch_size):
        index.upsert(vectors=vectors[i:i+batch_size])
    print("✅ Upsert terminé.")

if __name__ == "__main__":
    upsert_faq()
