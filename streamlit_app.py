import streamlit as st
from auth import check_password, show_rh_login_button
from pages_candidat import page_candidature
from pages_rh import page_dashboard_rh, page_ajout_poste, page_candidats_acceptes, page_interviews

st.set_page_config(page_title="Plateforme Recrutement", layout="wide")

# Initialisation session
if "auth_ok" not in st.session_state:
    st.session_state.auth_ok = False
if "show_rh_login" not in st.session_state:
    st.session_state.show_rh_login = False
if "logout" not in st.session_state:
    st.session_state.logout = False

# 👤 Affichage login ou espace RH ou page candidature
if not st.session_state.auth_ok:
    show_rh_login_button()

    if st.session_state.get("show_rh_login", False):
        check_password()
    else:
        page_candidature()
else:
    menu = st.sidebar.radio("Navigation RH :", ["Dashboard Recruteur", "Ajouter un poste","candidatur_accepté","Entretiens"])

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
