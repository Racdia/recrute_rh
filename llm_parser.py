import openai
import os
import json
import re

# Initialise le client OpenAI avec une clé sécurisée depuis l'environnement
client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def llm_extract_cv_info(cv_text):
    prompt = f"""
    Tu es un assistant de recrutement. Analyse le texte de ce CV et retourne les informations structurées au format JSON suivant :
    {{
      "name": "",
      "emails": [],
      "phones": [],
      "linkedin": [],
      "address": null,
      "education": [],
      "experience": [],
      "skills": [],
      "languages": []
    }}

    Essaye d'extraire l'adresse postale (même incomplète : ville, quartier, etc. si c'est écrit dans le CV).
    Voici le CV :
    \"\"\"{cv_text}\"\"\"

    Retourne uniquement le JSON.
    """
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.0,
        max_tokens=1024
    )

    json_text = response.choices[0].message.content
    json_text = re.sub(r"^```json|```$", "", json_text.strip(), flags=re.MULTILINE)
    return json.loads(json_text)


import json


def compute_cv_score(candidate, job):
    # Parsing des champs JSON stockés en string
    required_skills = [req['skill'] for req in (job.requirements or [])] if job.requirements else []

    # skills
    candidate_skills = candidate.skills
    if isinstance(candidate_skills, str):
        try:
            candidate_skills = json.loads(candidate_skills)
        except Exception:
            candidate_skills = []
    candidate_skills = candidate_skills or []

    # experience
    candidate_experience = candidate.experience
    if isinstance(candidate_experience, str):
        try:
            candidate_experience = json.loads(candidate_experience)
        except Exception:
            candidate_experience = []
    candidate_experience = candidate_experience or []

    # education
    candidate_education = candidate.education
    if isinstance(candidate_education, str):
        try:
            candidate_education = json.loads(candidate_education)
        except Exception:
            candidate_education = []
    candidate_education = candidate_education or []

    # 1. Matching skills
    match_count = 0
    for skill in required_skills:
        if skill.lower() in [c.lower() for c in candidate_skills]:
            match_count += 1
    score_skills = match_count / len(required_skills) if required_skills else 0

    # 2. Diplôme
    # On vérifie si le diplôme requis se retrouve dans l'éducation du candidat (basique)
    score_diploma = 0
    if job.diploma_type:
        job_diploma = job.diploma_type.lower()
        for ed in candidate_education:
            if job_diploma in json.dumps(ed).lower():
                score_diploma = 1
                break

    # 3. Expérience (MVP : 1 point par expérience trouvée, ou mieux si tu ajoutes "years")
    total_years = 0
    for exp in candidate_experience:
        # Si tu as le champ "years" sinon, tu peux parser les dates…
        total_years += exp.get("years", 1)  # Par défaut 1 an par expérience si pas d'info
    score_exp = min(1, (total_years / (job.experience_years or 1)))

    # 4. Score global pondéré
    score = 0.6 * score_skills + 0.2 * score_diploma + 0.2 * score_exp
    return round(100 * score, 2)


def analyze_soft_skills_llm(transcript, job):
    prompt = f"""À partir de ce texte (transcription d'une vidéo de présentation) :
---
{transcript}
---
Voici les soft skills clés demandés pour ce poste : {json.dumps(job.requirements)}.
Donne-moi une analyse JSON avec :
- "softskills": une liste des soft skills détectés dans la présentation.
- "softskills_score": une note de 0 à 100.
- "feedback": un court feedback RH personnalisé."""

    llm_response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "system", "content": prompt}],
        temperature=0.3,
    )
    out = json.loads(llm_response.choices[0].message.content)
    return out

def compute_global_score(cv_score, softskills_score, tech_score, weights=None):
    if weights is None:
        weights = {"cv": 0.4, "soft": 0.3, "tech": 0.3}
    return round(
        weights["cv"] * (cv_score or 0) +
        weights["soft"] * (softskills_score or 0) +
        weights["tech"] * (tech_score or 0), 2
    )

def generate_candidate_summary_openai(candidate, job, scores, transcript):
    prompt = f"""
    Tu es un assistant RH expert en recrutement. Voici les informations d'un candidat :
    ---
    • CV (texte) : {getattr(candidate, 'cv_text', '')}
    • Transcript vidéo : {transcript}
    • Poste ciblé : {job.title} - {job.description}
    • Scores : CV {scores['cv_score']}/100, Softskills {scores['softskills_score']}/100, Test technique {scores['tech_score']}/100, Global {scores['global_score']}/100
    • Softskills détectées : {', '.join(scores.get('softskills', []))}
    • Feedback RH : {scores.get('feedback', '')}
    ---
    Génère un mini-rapport synthétique (5 à 10 lignes) pour le recruteur, comprenant :
    - Pourquoi ce candidat ressort ou non pour ce poste (selon le score global)
    - Points forts
    - Axes d'amélioration ou points à approfondir
    Utilise un ton professionnel, constructif, et va droit au but.
    """

    response = openai.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "Tu es un assistant RH expert."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=400,
        temperature=0.5,
    )
    return response.choices[0].message.content.strip()

def generate_learning_suggestions_openai(name: str, job_title: str, feedback: str) -> str:
    prompt = f"""
    Tu es un assistant RH et formateur expert. Tu dois conseiller un candidat qui a été refusé pour un poste donné, en lui proposant :

    - 1 à 2 cours ou MOOCs en ligne pertinents (avec plateforme et lien si possible)
    - Les compétences/matières à renforcer
    - Un ton bienveillant, constructif, professionnel, pour l'encourager à progresser

    ---
    • Nom du candidat : {name}
    • Poste visé : {job_title}
    • Feedback RH reçu : {feedback}
    ---

    Fournis des suggestions pratiques, utiles, et bien formatées (avec bullet points HTML si utile).
    """

    response = openai.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "Tu es un expert RH et formateur professionnel."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=400,
        temperature=0.7,
    )

    return response.choices[0].message.content.strip()
