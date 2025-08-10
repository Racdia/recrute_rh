import streamlit as st
import requests

# --- STYLES CSS ---
def inject_background_style():
    st.markdown("""
    <style>
        .stApp {
            background-image: url("https://images.unsplash.com/photo-1607746882042-944635dfe10e"); 
            background-size: cover;
            background-position: center;
            background-repeat: no-repeat;  
        }
        .custom-container {
            background-color: rgba(255, 255, 255, 0.9);
            padding: 2rem;
            border-radius: 10px;
        }
    </style>
    """, unsafe_allow_html=True)

@st.cache_data
def fetch_jobs():
    try:
        response = requests.get("http://localhost:8000/job/list/")
        if response.ok:
            return response.json()
        else:
            return []
    except Exception as e:
        st.error(f"Erreur lors de la récupération des postes : {e}")
        return []

def page_candidature():
    inject_background_style()

    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown("<div class='custom-container'>", unsafe_allow_html=True)
        st.markdown("<h1 style='color:#3B82F6;'>📄 Candidature Spontanée</h1>", unsafe_allow_html=True)

        job_list = fetch_jobs()
        if not job_list:
            st.warning("Aucun poste n'est disponible actuellement.")
            st.stop()

        job_options = {f"{job['title']} (id: {job['id']})": job['id'] for job in job_list}
        selected_label = st.selectbox("🧑‍💼 Sélectionnez un poste :", list(job_options.keys()))

        if not selected_label:
            st.info("Veuillez sélectionner un poste pour continuer.")
            st.stop()

        selected_id = job_options[selected_label]
        selected_job = next((j for j in job_list if j["id"] == selected_id), None)
        if selected_job:
            st.markdown("### 📝 Description du poste")
            st.info(selected_job.get("description", "Aucune description."))
            st.markdown("### Diplôme")
            st.info(selected_job.get("diploma_type", "Non précisé"))
            st.markdown("### Niveau d'études")
            st.info(selected_job.get("education_level", "Non précisé"))
            st.markdown("### Années d'expérience")
            st.info(selected_job.get("experience_years", "Non précisé"))
        st.markdown("</div>", unsafe_allow_html=True)

    with col2:
        st.image("https://cdn-icons-png.flaticon.com/512/3135/3135755.png", width=200, caption="Votre profil")

    # --- TEST TECHNIQUE ---
    if "quiz_done" not in st.session_state:
        st.session_state.quiz_done = False

    with st.expander("🧪 Étape 1 : Passer le test technique", expanded=not st.session_state.quiz_done):
        if not st.session_state.quiz_done:
            if st.button("🎯 Générer le test"):
                with st.spinner("Création du test..."):
                    try:
                        r = requests.get(f"http://localhost:8000/job/{selected_id}/generate-quiz/")
                        if r.ok:
                            questions = r.json().get("questions", [])
                            st.session_state["quiz_questions"] = questions
                            st.session_state["quiz_answers"] = [None] * len(questions)
                            st.session_state["tech_score"] = None
                        else:
                            st.error("Erreur génération quiz : " + r.text)
                    except Exception as e:
                        st.error(f"Erreur serveur : {e}")

        if "quiz_questions" in st.session_state:
            st.markdown("#### Répondez aux questions suivantes :")
            for idx, q in enumerate(st.session_state["quiz_questions"]):
                answer = st.radio(f"**Q{idx+1}: {q['question']}**", q["options"], key=f"q_{idx}")
                st.session_state["quiz_answers"][idx] = answer

            if st.button("✅ Valider mes réponses"):
                score = sum(
                    1 for i, q in enumerate(st.session_state["quiz_questions"])
                    if st.session_state["quiz_answers"][i] == q["answer"]
                )
                tech_score = round(score / len(st.session_state["quiz_questions"]) * 100, 2)
                st.session_state["tech_score"] = tech_score
                st.session_state.quiz_done = True
                st.success(f"🎉 Test réussi avec un score de {tech_score} % !")

    # --- UPLOAD CV & VIDÉO ---
    if st.session_state.quiz_done and st.session_state.get("tech_score") is not None:
        st.divider()
        st.markdown("### 📤 Étape 2 : Déposez vos fichiers")

        if "cv_upload_success" not in st.session_state:
            st.session_state.cv_upload_success = False
            st.session_state.cv_result = None
            st.session_state.video_file = None

        with st.form("upload_form"):
            cv_file = st.file_uploader("📎 CV (PDF/DOCX)", type=["pdf", "docx"])
            video_file = st.file_uploader("🎥 Vidéo de présentation", type=["mp4", "mov", "avi"])
            submitted = st.form_submit_button("📨 Soumettre ma candidature")

            if submitted:
                if not cv_file:
                    st.warning("Merci de déposer votre CV.")
                elif not video_file:
                    st.warning("Merci de déposer votre vidéo.")
                else:
                    try:
                        files = {"file": (cv_file.name, cv_file, cv_file.type)}
                        data = {"job_id": selected_id}
                        r = requests.post("http://localhost:8000/candidate/upload-cv/", files=files, data=data)

                        if r.ok:
                            st.session_state.cv_result = r.json()
                            st.session_state.cv_upload_success = True
                            st.session_state.video_file = video_file
                        else:
                            st.error(f"Erreur CV : {r.status_code} / {r.text}")
                    except Exception as e:
                        st.error(f"Erreur d'envoi : {e}")

        if st.session_state.cv_upload_success and st.session_state.cv_result:
            result = st.session_state.cv_result
            info = result.get("infos", {})
            video_file = st.session_state.video_file

            st.success("✅ CV envoyé ! Voici les informations extraites :")
            with st.form("cv_info_form"):
                nom = st.text_input("👤 Nom", value=info.get("name", result.get("name", "")))
                email = st.text_input("📧 Email", value=info.get("emails", [""])[0])
                phone = st.text_input("📞 Téléphone", value=info.get("phones", [""])[0])
                experiences = st.text_area("💼 Expérience", value=", ".join(
                    [exp.get("position", "") + " @ " + exp.get("company", "") for exp in info.get("experience", [])]
                ))
                langues = st.text_area("🌍 Langues", value=", ".join(
                    [f"{lang['language']} ({lang['level']})" for lang in info.get("languages", [])]
                ))
                skills = st.text_area("🛠️ Compétences", value=", ".join(info.get("skills", [])))
                confirm_infos = st.form_submit_button("✅ Confirmer les informations")

            if confirm_infos:
                candidate_id = result.get("candidate_id")
                if not candidate_id:
                    st.warning("ID du candidat introuvable.")
                    st.stop()

                files_video = {"video": (video_file.name, video_file, video_file.type)}
                data_video = {
                    "candidate_id": candidate_id,
                    "job_id": selected_id,
                    "tech_score": st.session_state["tech_score"],
                    "name": nom,
                    "email": email,
                    "phone": phone,
                    "skills": skills
                }

                try:
                    rv = requests.post("http://localhost:8000/application/apply/", files=files_video, data=data_video)
                    if rv.ok:
                        st.success("🎬 Vidéo envoyée avec succès !")
                        st.json(rv.json())
                        for k in ["quiz_done", "quiz_questions", "quiz_answers", "tech_score",
                                  "cv_upload_success", "cv_result", "video_file"]:
                            st.session_state.pop(k, None)
                    else:
                        st.error(f"Erreur vidéo : {rv.status_code} / {rv.text}")
                except Exception as e:
                    st.error(f"Erreur d'envoi vidéo : {e}")
