import streamlit as st
import requests

st.set_page_config(page_title="Chatbot RH", page_icon="💬")
st.title("💬 Chatbot RH (RAG sur la FAQ)")

API_URL = st.secrets.get("API_URL", "http://localhost:8000/chatbot/ask")

if "history" not in st.session_state:
    st.session_state.history = []

for role, content in st.session_state.history:
    with st.chat_message(role):
        st.markdown(content)

q = st.chat_input("Posez une question (ex: Quels formats de CV sont acceptés ?)")
if q:
    st.session_state.history.append(("user", q))
    with st.chat_message("user"):
        st.markdown(q)

    with st.chat_message("assistant"):
        with st.spinner("Je réfléchis…"):
            try:
                r = requests.post(API_URL, json={"question": q, "top_k": 5}, timeout=60)
                if r.ok:
                    data = r.json()
                    st.markdown(data["answer"])
                    if data.get("sources"):
                        with st.expander("Sources (FAQ)"):
                            for s in data["sources"]:
                                st.write(f"- **Q**: {s['question']}\n\n  **R**: {s['answer']}\n\n  _score: {s['score']:.3f}_")
                else:
                    st.error(f"Erreur API: {r.status_code} – {r.text}")
            except Exception as e:
                st.error(str(e))
