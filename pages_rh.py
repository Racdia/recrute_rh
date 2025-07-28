import streamlit as st
import pandas as pd
import requests
import json
import re

@st.cache_data
def fetch_applications():
    resp = requests.get("http://localhost:8000/application/list/")
    if resp.ok:
        return resp.json()
    return []

def page_dashboard_rh():
    st.title("👨‍💼 Dashboard Recruteur – Suivi et Classement des Candidatures")

    data = fetch_applications()
    if not data:
        st.warning("Aucune candidature disponible pour l’instant.")
        st.stop()

    df = pd.DataFrame(data)

    # ---- Filtrage par poste/job ----
    job_list = df["job_title"].unique().tolist()
    job_select = st.selectbox("🔎 Filtrer par offre d'emploi :", ["Tous"] + job_list)
    if job_select != "Tous":
        df = df[df["job_title"] == job_select]

    # ---- Recherche par nom ----
    search_name = st.text_input("Rechercher un candidat par nom :")
    if search_name:
        df = df[df["candidate_name"].str.lower().str.contains(search_name.lower())]

    # ---- Classement Top 3 ----
    df = df.sort_values(by="global_score", ascending=False)
    top_n = 3 if len(df) > 3 else len(df)
    top_candidates = df.head(top_n)

    st.subheader("🏆 Top Candidats")
    cols = st.columns(top_n)
    for idx, (col, (_, row)) in enumerate(zip(cols, top_candidates.iterrows())):
        with col:
            st.markdown(f"""
            <div style="background-color: #f3f7fa; border-radius: 18px; padding: 18px; box-shadow: 0 2px 6px #ddd;">
                <h4 style='color:#228be6'>{row['candidate_name']}</h4>
                <b>Poste :</b> <span style="color:#666">{row['job_title']}</span><br>
                <b>Global Score :</b> <span style='font-size:1.3em; color:#52b788'><b>{row['global_score']}</b></span>
                <hr>
                <span style="color:#888">CV : <b>{row['cv_score']}</b> | Softskills : <b>{row['softskills_score']}</b> | Test tech. : <b>{row['tech_score']}</b></span>
            </div>
            """, unsafe_allow_html=True)
            st.progress(int(row['global_score']))

    st.markdown("---")

    # ---- Tableau de ranking général (affichage stylé) ----
    st.subheader("📊 Classement général des candidats")

    def highlight_best(val):
        if pd.isnull(val): return ""
        try:
            v = float(val)
        except: return ""
        color = ""
        if v >= 70:
            color = "#52b788"
        elif v >= 40:
            color = "#ffd166"
        else:
            color = "#ef476f"
        return f"background-color: {color}; color:white"

    styled_df = df[["candidate_name", "job_title", "cv_score", "softskills_score", "tech_score", "global_score"]]\
        .style.applymap(highlight_best, subset=["cv_score", "softskills_score", "tech_score", "global_score"])\
        .format(precision=1)

    st.dataframe(styled_df, use_container_width=True, height=400)

    # ---- Vue détaillée d’un candidat ----
    if len(df) > 0:
        st.markdown("---")
        st.subheader("🔍 Détail d'une candidature")
        detail_names = df["candidate_name"].tolist()
        selected_name = st.selectbox("Choisir un candidat :", detail_names)
        row = df[df["candidate_name"] == selected_name].iloc[0]

        global_score = float(row.get('global_score', 0))
        if global_score >= 70:
            color = "#52b788"
        elif global_score >= 40:
            color = "#ffd166"
        else:
            color = "#ef476f"

        def clean_html_tags(text):
            clean = re.compile(r'<(?!br\s*\/?)[^>]+>')
            return re.sub(clean, '', text)

        mini_report = row.get("mini_report", None)
        mini_report_html = ""
        if mini_report and str(mini_report).strip():
            mini_report_clean = clean_html_tags(str(mini_report))
            mini_report_display = (
                mini_report_clean
                .replace('\r\n', '<br>')
                .replace('\r', '<br>')
                .replace('\n', '<br>')
            )
            mini_report_html = f"""
                <div style='margin-top:18px;'>
                    <div style="
                        background: linear-gradient(90deg, {color}10 90%, #f3f7fa 100%);
                        border-left: 8px solid {color};
                        border-radius: 14px;
                        padding: 18px 20px 14px 18px;
                        box-shadow: 0 2px 6px #ededed;">
                        <h5 style="color:{color};margin:0 0 8px 0;">📝 Mini-rapport IA généré</h5>
                        <div style="font-size: 1.06em; color:#222; line-height:1.7;">
                            {mini_report_display}
                        </div>
                    </div>
                </div>
            """

        col_left, col_right = st.columns([1, 1])
        with col_left:
            st.markdown(
                f"""
                <div style="background: linear-gradient(90deg, #e3eefa 70%, #f3f7fa 100%);
                            border-radius: 22px; padding: 28px 20px 20px 32px; box-shadow: 0 2px 16px #d2e3fa; min-height:340px;">
                    <h2 style="color:#228be6; margin-bottom:0px;">{row.get('candidate_name', '')}</h2>
                    <h4 style="margin: 0; color: #888;">Poste : {row.get('job_title', '—')}</h4>
                    <ul style="list-style: none; padding-left: 0; margin-top:12px;">
                        <li>🌟 <b>Score global</b> : <span style='font-size:1.3em; color:#52b788;'>{row.get('global_score', '—')}</span></li>
                        <li>📄 <b>CV</b> : <b style="color:#40916c">{row.get('cv_score', '—')}</b></li>
                        <li>🤝 <b>Soft skills</b> : <b style="color:#f8961e">{row.get('softskills_score', '—')}</b></li>
                        <li>💻 <b>Test technique</b> : <b style="color:#0077b6">{row.get('tech_score', '—')}</b></li>
                    </ul>
                    <div style="margin:8px 0 4px 0;">
                        <b>Soft skills détectées :</b><br>
                        <span style="color:#228be6">{', '.join(row.get('softskills', [])) if row.get('softskills') else '—'}</span>
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )

        with col_right:
            st.markdown(
                f"""
                <div style="background: #f6f8fa; border-radius:18px; padding:24px 18px; color:#333; box-shadow: 0 2px 10px #e0e9fa; min-height:340px; display: flex; flex-direction: column; justify-content: flex-start;">
                    <h4 style="margin-top:0;color:#228be6">Feedback RH</h4>
                    <div>{row.get('feedback', '—')}</div>
                </div>
                """,
                unsafe_allow_html=True
            )

        # --- Mini rapport tout en bas, hors colonnes ---
        if mini_report_html:
            st.markdown(
                f"<div style='display:flex; justify-content:center;'>{mini_report_html}</div>", unsafe_allow_html=True
            )

        # Actions RH
        st.markdown("#### Actions RH")
        col1, col2, col3 = st.columns(3)
        app_id = row.get('application_id')

        with col1:
            if st.button("✅ Valider", key="valide_" + str(app_id)):
                try:
                    r = requests.post(f"http://localhost:8000/application/{app_id}/accept/")
                    if r.ok:
                        st.success("Candidat validé !")
                    else:
                        st.error("Erreur lors de la validation.")
                except Exception as e:
                    st.error(str(e))

        with col2:
            if st.button("❌ Refuser", key="refuse_" + str(app_id)):
                try:
                    r = requests.post(f"http://localhost:8000/application/{app_id}/refuse/")
                    if r.ok:
                        st.success("Candidat refusé.")
                    else:
                        st.error("Erreur lors du refus.")
                except Exception as e:
                    st.error(str(e))

        with col3:
            note = st.text_input("Note privée RH", key="note_" + str(app_id))
            if st.button("💾 Enregistrer la note", key="note_btn_" + str(app_id)):
                try:
                    r = requests.post(
                        f"http://localhost:8000/application/{app_id}/add-note/",
                        json={"note": note}
                    )
                    if r.ok:
                        st.info("Note enregistrée !")
                    else:
                        st.error("Erreur lors de l'enregistrement de la note.")
                except Exception as e:
                    st.error(str(e))

    st.markdown("""
        <style>
            .stDataFrame thead tr th { background-color: #e3eefa !important; }
        </style>
        """, unsafe_allow_html=True)

def page_ajout_poste():
    st.title("Ajouter un nouveau poste")

    title = st.text_input("Intitulé du poste")
    description = st.text_area("Description du poste")

    diploma_type = st.selectbox("Type de diplôme requis", ["", "Licence", "Master", "Doctorat", "BTS", "Autre"])
    filiere = st.text_input("Filière/Spécialité")
    education_level = st.selectbox("Niveau d'études minimal", ["", "Bac", "Bac+2", "Bac+3", "Bac+5", "Doctorat"])
    experience_years = st.number_input("Années d'expérience requises", min_value=0, max_value=40, value=0, step=1)

    if "skills" not in st.session_state:
        st.session_state.skills = []

    with st.form(key="skills_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            skill = st.text_input("Compétence (ex : Python)", key="skill_input")
        with col2:
            level = st.selectbox("Niveau", ["débutant", "intermédiaire", "avancé"], key="level_select")
        submit_skill = st.form_submit_button("Ajouter cette compétence")
        if submit_skill:
            if skill:
                st.session_state.skills.append({"skill": skill, "level": level})
                st.success(f"Compétence {skill} ({level}) ajoutée.")
            else:
                st.warning("Merci de renseigner une compétence.")

    if st.session_state.skills:
        st.write("Compétences ajoutées :")
        st.json(st.session_state.skills)

    if st.button("Créer le poste"):
        if not title:
            st.warning("L'intitulé du poste est obligatoire.")
        else:
            data = {
                "title": title,
                "description": description,
                "diploma_type": diploma_type,
                "filiere": filiere,
                "education_level": education_level,
                "experience_years": int(experience_years),
                "requirements": json.dumps(st.session_state.skills)
            }
            try:
                response = requests.post("http://localhost:8000/job/create/", data=data)
                if response.ok:
                    st.success("Poste ajouté avec succès !")
                    st.json(response.json())
                    st.session_state.skills = []
                else:
                    st.error(f"Erreur serveur : {response.status_code} / {response.text}")
            except Exception as ex:
                st.error(f"Erreur lors de l'envoi : {str(ex)}")
