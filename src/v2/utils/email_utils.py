import os
import smtplib
from email.mime.text import MIMEText
from email.utils import formatdate
from dotenv import load_dotenv

from src.v2.utils.logger import get_logger

logger = get_logger("email_utils")
load_dotenv()  # charge .env si disponible

# Paramètres SMTP (tu peux les surcharger dans .env)
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))

# Identité d’envoi / réception
EMAIL_SENDER = os.getenv("EMAIL_SENDER")          # ex: adolf.allotey@novastarcapital.fr
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")      # mot de passe / app password
EMAIL_RECEIVER = os.getenv("EMAIL_RECEIVER")      # destinataire par défaut

def send_email_report(*, subject: str, body: str, to_email: str | None = None) -> bool:
    """
    Envoie un email texte simple. Retourne True si succès, False sinon.
    Utilise EMAIL_RECEIVER si to_email n'est pas fourni.
    """
    recipient = to_email or EMAIL_RECEIVER
    if not EMAIL_SENDER or not EMAIL_PASSWORD or not recipient:
        logger.error("❌ Paramètres email manquants (EMAIL_SENDER/EMAIL_PASSWORD/EMAIL_RECEIVER).")
        return False

    try:
        msg = MIMEText(body, _charset="utf-8")
        msg["Subject"] = subject
        msg["From"] = EMAIL_SENDER
        msg["To"] = recipient
        msg["Date"] = formatdate(localtime=True)

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.send_message(msg)

        logger.info("✅ Email envoyé avec succès.")
        return True
    except Exception as e:
        logger.exception(f"❌ Erreur envoi email : {e}")
        return False