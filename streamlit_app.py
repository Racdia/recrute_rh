import streamlit as st
import requests
from auth import check_password, show_rh_login_button
from pages_candidat import page_candidature
from pages_rh import page_dashboard_rh, page_ajout_poste, page_candidats_acceptes, page_interviews

st.set_page_config(page_title="Plateforme Recrutement", layout="wide")

# ---------------------------
# Chatbot en sidebar (RAG)
# ---------------------------
def sidebar_chatbot():
    API_URL = "http://localhost:8000/chatbot/ask"
    # Historique minimal en mémoire de session
    if "chatbot_history" not in st.session_state:
        st.session_state.chatbot_history = []  # liste de dicts [{"role":"user"/"assistant", "text": "..."}]

    with st.sidebar.expander("💬 Chatbot RH", expanded=False):
        # Affiche 2-3 derniers échanges
        if st.session_state.chatbot_history:
            st.caption("Derniers échanges :")
            for msg in st.session_state.chatbot_history[-4:]:
                bullet = "👤" if msg["role"] == "user" else "🤖"
                st.markdown(f"- {bullet} {msg['text']}")

        q = st.text_input("Votre question :", key="chatbot_q")
        col_send, col_reset = st.columns([1, 1])
        send = col_send.button("Envoyer", key="chatbot_send")
        reset = col_reset.button("Effacer", key="chatbot_clear")

        if reset:
            st.session_state.chatbot_history = []
            st.toast("Historique effacé.", icon="🧹")

        if send and q:
            st.session_state.chatbot_history.append({"role": "user", "text": q})
            try:
                r = requests.post(API_URL, json={"question": q, "top_k": 5}, timeout=60)
                if r.ok:
                    data = r.json()
                    answer = data.get("answer", "Désolé, je n’ai pas trouvé d’information pertinente.")
                    st.session_state.chatbot_history.append({"role": "assistant", "text": answer})
                    st.success("Réponse reçue ✅")

                    # Affiche la réponse
                    st.markdown("**Réponse :**")
                    st.write(answer)

                    # Affiche les sources (si le backend les renvoie)
                    sources = data.get("sources") or []
                    if sources:
                        with st.expander("Sources (FAQ)"):
                            for s in sources:
                                score = s.get("score")
                                score_txt = f" _(score: {score:.3f})_" if isinstance(score, (int, float)) else ""
                                st.markdown(f"- **Q** : {s.get('question','')}\n\n  **R** : {s.get('answer','')}{score_txt}")
                else:
                    st.error(f"Erreur API: {r.status_code} – {r.text}")
            except Exception as e:
                st.error(f"Erreur de connexion au chatbot : {e}")

# ---------------------------
# État session
# ---------------------------
if "auth_ok" not in st.session_state:
    st.session_state.auth_ok = False
if "show_rh_login" not in st.session_state:
    st.session_state.show_rh_login = False
if "logout" not in st.session_state:
    st.session_state.logout = False

# ---------------------------
# Affichage : public vs RH
# ---------------------------
if not st.session_state.auth_ok:
    # Bouton pour révéler le formulaire RH
    show_rh_login_button()

    # Chatbot dispo aussi côté public
    sidebar_chatbot()

    if st.session_state.get("show_rh_login", False):
        check_password()
    else:
        page_candidature()
else:
    # Menu RH
    menu = st.sidebar.radio(
        "Navigation RH :",
        ["Dashboard Recruteur", "Ajouter un poste", "candidatur_accepté", "Entretiens"]
    )

    # Chatbot (toujours visible en sidebar)
    sidebar_chatbot()

    if st.sidebar.button("Déconnexion"):
        st.session_state.auth_ok = False
        st.session_state.logout = True
        st.rerun()

    if menu == "Dashboard Recruteur":
        page_dashboard_rh()
    elif menu == "candidatur_accepté":
        page_candidats_acceptes()
    elif menu == "Entretiens":
        page_interviews()
    else:
        page_ajout_poste()
