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
