# auth.py
import requests
import streamlit as st


def check_password():
    if "auth_ok" not in st.session_state:
        st.session_state.auth_ok = False
    if "logout" in st.session_state and st.session_state.logout:
        st.session_state.auth_ok = False
        st.session_state.logout = False

    # ✅ Si déjà connecté
    if st.session_state.auth_ok:
        if st.button("⬅️ Retour à la candidature"):
            st.session_state["show_rh_login"] = False
            st.rerun()
        return True

    # 🔐 Page de login RH
    st.title("🔐 Connexion RH")

    # ✅ Ajout du bouton de retour candidature
    if st.button("⬅️ Retour à la candidature"):
        st.session_state["show_rh_login"] = False
        st.rerun()

    with st.form("login_form"):
        username = st.text_input("Nom d'utilisateur")
        password = st.text_input("Mot de passe", type="password")
        submit = st.form_submit_button("Se connecter")

        if submit:
            try:
                response = requests.post("http://localhost:8000/user/login", json={
                    "username": username,
                    "password": password
                })
                if response.ok:
                    st.session_state.auth_ok = True
                    st.success("Connexion réussie !")
                    st.rerun()
                else:
                    st.error("Identifiants incorrects.")
            except Exception as e:
                st.error(f"Erreur de connexion : {e}")
    st.stop()


def show_rh_login_button():
    """Affiche un bouton RH fixe en haut à droite."""
    st.markdown(
        """<style>
        .rh-button-container { position: absolute; top: 10px; right: 28px; z-index:1000; }
        </style>""",
        unsafe_allow_html=True,
    )
    with st.container():
        col1, col2 = st.columns([5, 1])
        with col2:
            if st.button("Connexion RH"):
                st.session_state["show_rh_login"] = True
                st.rerun()
