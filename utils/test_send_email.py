from email_utils import send_email

if __name__ == "__main__":
    destinataire = "diallomamadouracine84@gmail.com"  # Remplace par ton email de test
    sujet = "✅ Test d'envoi d'e-mail depuis FastAPI"
    corps = """
    <h3 style="color:#228be6;">Bonjour !</h3>
    <p>Ceci est un <b>test</b> d'envoi d'e-mail depuis mon projet FastAPI/Streamlit.</p>
    <p>Tout fonctionne correctement 🚀</p>
    """

    success = send_email(subject=sujet, body=corps, to_email=destinataire)
    print("✅ Envoi réussi" if success else "❌ Échec de l'envoi")
