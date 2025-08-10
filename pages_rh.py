import streamlit as st
import pandas as pd
import requests
import json
import re
import datetime



@st.cache_data
def fetch_all_accepted_applications():
    url = "http://localhost:8000/application/list/?status=validé"
    resp = requests.get(url)
    if resp.ok:
        df = pd.DataFrame(resp.json())

        # Nettoyage email
        def clean_email(x):
            if isinstance(x, list):
                return ''.join(x).replace('[', '').replace(']', '').replace('"', '').strip()
            return str(x).strip()

        df["email"] = df["email"].apply(clean_email)
        return df.convert_dtypes()
    return pd.DataFrame()

@st.cache_data
def fetch_applications():
    resp = requests.get("http://localhost:8000/application/list/")
    if resp.ok:
        data = resp.json()
        df = pd.DataFrame(data)

        if "email" in df.columns:
            df["email"] = df["email"].apply(
                lambda x: x[0] if isinstance(x, list) and len(x) > 0 else str(x)
            )

        for col in df.columns:
            df[col] = df[col].apply(lambda x: str(x) if isinstance(x, (list, dict)) else x)

        return df.convert_dtypes()
    return pd.DataFrame()

@st.cache_data
def fetch_interviews():
    resp = requests.get("http://localhost:8000/interviews/")
    if not resp.ok:
        st.error(f"Erreur récupération entretiens : {resp.status_code}")
        return pd.DataFrame()
    data = resp.json()
    df = pd.DataFrame(data)
    if "interview_datetime" in df.columns:
        df["interview_datetime"] = pd.to_datetime(df["interview_datetime"])
    return df

def page_dashboard_rh():

    st.markdown("""
        <style>
            html, body {
                background-color: #f9fafc;
                font-family: 'Segoe UI', sans-serif;
            }
            .stButton>button {
                background-color: #4a90e2;
                color: white;
                padding: 0.6em 1.2em;
                border-radius: 8px;
                font-weight: bold;
                transition: 0.3s ease;
            }
            .stButton>button:hover {
                background-color: #357ab8;
            }
            .stTextInput>div>input,
            .stTextArea>div>textarea,
            .stSelectbox>div>div {
                background-color: #eef3f9;
                border-radius: 8px;
            }
            .block-container {
                padding: 2rem;
            }
            .card {
                background: white;
                padding: 2rem;
                border-radius: 16px;
                box-shadow: 0 2px 12px rgba(0,0,0,0.06);
                margin-bottom: 2rem;
            }
        </style>
    """, unsafe_allow_html=True)

    st.title("👨‍💼 Dashboard Recruteur – Suivi des Candidatures")

    data = fetch_applications()
    if data.empty:
        st.warning("Aucune candidature disponible pour l’instant.")
        st.stop()

    df = data

    job_list = df["job_title"].unique().tolist()
    kpi1, kpi2, kpi3 = st.columns(3)
    kpi1.metric("👤 Candidats", len(df))
    kpi2.metric("📋 Postes", len(job_list))
    kpi3.metric("⚙️ Test moyen", f"{df['tech_score'].mean():.1f}%")

    with st.expander("🔎 Filtres avancés", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            search_name = st.text_input("Nom du candidat")
        with col2:
            job_select = st.selectbox("Offre d'emploi", ["Tous"] + job_list)

    if job_select != "Tous":
        df = df[df["job_title"] == job_select]
    if search_name:
        df = df[df["candidate_name"].str.lower().str.contains(search_name.lower())]

    df = df.sort_values(by="global_score", ascending=False)
    top_n = min(3, len(df))
    top_candidates = df.head(top_n)

    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.subheader("🏆 Meilleurs profils candidats")
    cols = st.columns(top_n)
    for col, (_, row) in zip(cols, top_candidates.iterrows()):
        with col:
            st.image("https://api.dicebear.com/6.x/adventurer/svg?seed=" + row['candidate_name'], width=80)
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
    st.markdown("</div>", unsafe_allow_html=True)

    def highlight_best(val):
        if pd.isnull(val): return ""
        try: v = float(val)
        except: return ""
        if v >= 70: return "background-color: #52b788; color:white"
        elif v >= 40: return "background-color: #ffd166; color:black"
        else: return "background-color: #ef476f; color:white"

    styled_df = df[["candidate_name", "job_title", "cv_score", "softskills_score", "tech_score", "global_score"]] \
        .style.applymap(highlight_best, subset=["cv_score", "softskills_score", "tech_score", "global_score"]) \
        .format(precision=1)

    tab1, tab2 = st.tabs(["🔍 Détail d'une candidature", "📁 Toutes les candidatures"])

    with tab1:
        if len(df) > 0:
            selected_name = st.selectbox("Choisir un candidat :", df["candidate_name"].tolist())
            row = df[df["candidate_name"] == selected_name].iloc[0]

            color = "#52b788" if row['global_score'] >= 70 else "#ffd166" if row['global_score'] >= 40 else "#ef476f"
            mini_report = row.get("mini_report", "")
            feedback = row.get("feedback", "—")

            if mini_report:
                mini_report_display = re.sub(r'<(?!br\s*/?)>', '', mini_report).replace('\n', '<br>')
                st.markdown(f"""
                    <div style="background:#f3f7fa;border-left: 8px solid {color}; border-radius: 14px; padding: 18px; box-shadow: 0 2px 6px #ededed;">
                        <h5 style="color:{color};margin-bottom:12px;">🧠 Rapport IA – Profil Candidat</h5>
                        <div style="font-size: 1.1em; color:#222; line-height:1.7;">{mini_report_display}</div>
                    </div>
                """, unsafe_allow_html=True)

            left, right = st.columns([1, 1])
            with left:
                st.image("https://api.dicebear.com/6.x/adventurer/svg?seed=" + row['candidate_name'], width=80)
                st.markdown(f"""
                    <div style="background: #e3eefa; border-radius: 22px; padding: 28px; box-shadow: 0 2px 16px #d2e3fa;">
                        <h3 style="color:#228be6">{row['candidate_name']}</h3>
                        <p><b>Poste :</b> {row['job_title']}</p>
                        <ul style="list-style: none; padding-left: 0;">
                            <li>🌟 <b>Score global :</b> <span style='font-size:1.3em; color:{color}'>{row['global_score']}</span></li>
                            <li>📄 <b>CV :</b> <b style="color:#40916c">{row['cv_score']}</b></li>
                            <li>🤝 <b>Soft skills :</b> <b style="color:#f8961e">{row['softskills_score']}</b></li>
                            <li>💻 <b>Test technique :</b> <b style="color:#0077b6">{row['tech_score']}</b></li>
                        </ul>
                        <b>Soft skills détectées :</b><br>
                        <span style="color:#228be6">{', '.join(row.get('softskills', [])) if row.get('softskills') else '—'}</span>
                    </div>
                """, unsafe_allow_html=True)

            with right:
                st.markdown(f"""
                    <div style="background: #fff6e0; border-left: 6px solid #f4a261; border-radius:10px; padding: 18px 20px; font-size:1em">
                        <h4 style="color:#e76f51">💬 Feedback RH</h4>
                        {feedback}
                    </div>
                """, unsafe_allow_html=True)

            st.markdown("### 🛠️ Actions RH")
            col1, col2, col3 = st.columns(3)
            app_id = row.get('application_id')
            with col1:
                if st.button("✅ Valider", key="valide_" + str(app_id)):
                    try:
                        r = requests.post(
                            f"http://localhost:8000/application/{app_id}/accept/",
                            json={"email": row["email"], "name": row["candidate_name"], "job": row["job_title"]}
                        )
                        st.success("Candidat validé !" if r.ok else f"Erreur : {r.status_code} – {r.text}")
                    except Exception as e:
                        st.error(str(e))

            with col2:
                if st.button("❌ Refuser", key="refuse_" + str(app_id)):
                    try:
                        r = requests.post(
                            f"http://localhost:8000/application/{app_id}/refuse/",
                            json={
                                "email": row["email"],
                                "name": row["candidate_name"],
                                "job": row["job_title"],
                                "feedback": row.get("feedback", "Nous vous encourageons à développer vos compétences.")
                            }
                        )
                        st.success("Candidat refusé." if r.ok else f"Erreur : {r.status_code} – {r.text}")
                    except Exception as e:
                        st.error(str(e))

            with col3:
                note = st.text_input("Note privée RH", key="note_" + str(app_id))
                if st.button("📏 Enregistrer la note", key="note_btn_" + str(app_id)):
                    try:
                        r = requests.post(
                            f"http://localhost:8000/application/{app_id}/add-note/",
                            json={"note": note}
                        )
                        st.info("Note enregistrée !" if r.ok else "Erreur enregistrement note.")
                    except Exception as e:
                        st.error(str(e))

    with tab2:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.subheader("📋 Liste complète des candidatures")
        st.markdown("<p style='color:#666'>Les couleurs indiquent la qualité des scores (vert = excellent, jaune = moyen, rouge = faible).</p>", unsafe_allow_html=True)
        st.dataframe(styled_df, use_container_width=True, height=400)
        st.markdown("</div>", unsafe_allow_html=True)


def page_candidats_acceptes():
    st.title("✅ Candidatures acceptées par poste")

    df = fetch_all_accepted_applications()

    if df.empty:
        st.info("Aucune candidature acceptée.")
        return

    # 🔎 Liste des postes uniques
    job_titles = df["job_title"].unique().tolist()
    selected_job = st.selectbox("📋 Filtrer par poste :", ["Tous"] + job_titles)

    if selected_job != "Tous":
        df = df[df["job_title"] == selected_job]

    st.write(f"Nombre de candidatures acceptées : {len(df)}")

    st.dataframe(
        df[["candidate_name", "email", "job_title", "global_score"]],
        use_container_width=True
    )

    # ⬇️ Export CSV
    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button("📥 Exporter au format CSV", data=csv, file_name="candidats_acceptes.csv", mime="text/csv")

    st.markdown("---")
    st.subheader("📅 Programmer un entretien")

    # Sélection du candidat accepté
    selected_app = st.selectbox("👤 Sélectionnez un candidat :", df["candidate_name"].unique())
    selected_row = df[df["candidate_name"] == selected_app].iloc[0]

    # 📆 Date et ⏰ Heure
    date = st.date_input("Date de l'entretien", value=datetime.date.today())
    time = st.time_input("Heure de l'entretien", value=datetime.time(10, 0))  # 10h par défaut
    location = st.text_input("📍 Lieu de l'entretien", placeholder="Ex: Salle 304, Campus Dakar")

    # Formatage final de la date et de l'heure
    datetime_str = f"{date.strftime('%d/%m/%Y')} à {time.strftime('%H:%M')}"

    # ✅ Bouton d’envoi
    if st.button("📨 Envoyer la convocation", key="send_invite"):
        payload = {
            "email": selected_row["email"],
            "name": selected_row["candidate_name"],
            "job": selected_row["job_title"],
            "interview_datetime": datetime_str,
            "location": location
        }

        try:
            r = requests.post(
                f"http://localhost:8000/application/{selected_row['application_id']}/schedule-interview/",
                json=payload
            )
            if r.ok:
                st.success("✅ Convocation envoyée avec succès !")
            else:
                st.error(f"❌ Erreur serveur : {r.status_code} – {r.text}")
        except Exception as e:
            st.error(f"Erreur d’envoi : {e}")

def page_interviews():
    st.title("📅 Entretiens prévus")

    df = fetch_interviews()
    if df.empty:
        st.info("Aucun entretien planifié.")
        return

    # Filtre par date
    min_date = df["interview_datetime"].dt.date.min()
    max_date = df["interview_datetime"].dt.date.max()
    date_filter = st.date_input(
        "Afficher les entretiens du",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date
    )
    start, end = date_filter if isinstance(date_filter, tuple) else (date_filter, date_filter)

    mask = (df["interview_datetime"].dt.date >= start) & (df["interview_datetime"].dt.date <= end)
    df_filtered = df.loc[mask]

    # Affichage
    st.write(f"Entretiens du **{start.strftime('%d/%m/%Y')}** au **{end.strftime('%d/%m/%Y')}** : {len(df_filtered)}")
    st.dataframe(
        df_filtered[[
            "interview_id",
            "application_id",
            "candidate_name",
            "job_title",
            df["interview_datetime"].dt.strftime("%d/%m/%Y %H:%M").name,
            "location"
        ]].rename(columns={"interview_datetime": "Date & Heure"}),
        use_container_width=True,
        height=400
    )


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


