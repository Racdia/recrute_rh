import smtplib
import time
from email.mime.text import MIMEText

def send_email_with_retry(
    to_email: str,
    subject: str,
    body: str,
    host: str,
    port: int,
    username: str,
    password: str,
    retries: int = 3,
    delay: int = 5
):
    msg = MIMEText(body, "html", "utf-8")
    msg["Subject"] = subject
    msg["From"] = username
    msg["To"] = to_email

    for attempt in range(1, retries + 1):
        try:
            with smtplib.SMTP(host, port, timeout=10) as server:
                server.starttls()
                server.login(username, password)
                server.send_message(msg)
            print(f"✅ Email envoyé à {to_email} (tentative {attempt})")
            return True
        except Exception as e:
            print(f"❌ Tentative {attempt} - échec envoi à {to_email} : {e}")
            if attempt < retries:
                time.sleep(delay)

    # ici, enregistrer en base ou loguer la défaillance
    print(f"⚠️ Échec définitif pour l’email à {to_email}")
    return False


def log_failed_email(to_email, subject, body):
    # ici tu peux écrire dans un fichier ou insérer dans une table `failed_emails`
    print(f"[LOG] Enregistrement de l'email échoué pour relance : {to_email}, sujet={subject}")
