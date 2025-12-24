# src/utils/email_utils.py

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os

def send_email_report(subject, message):
    """
    Envoie un email avec le sujet et le message spécifié en utilisant les variables d'environnement suivantes :
    - SMTP_SERVER
    - SMTP_PORT
    - EMAIL_USER
    - EMAIL_PASSWORD
    - EMAIL_TO
    """
    smtp_server = os.getenv("SMTP_SERVER")
    smtp_port = int(os.getenv("SMTP_PORT", "465"))
    email_user = os.getenv("EMAIL_USER")
    email_password = os.getenv("EMAIL_PASSWORD")
    email_to = os.getenv("EMAIL_TO")

    if not all([smtp_server, smtp_port, email_user, email_password, email_to]):
        raise ValueError("❌ Une ou plusieurs variables d'environnement sont manquantes pour l'envoi d'email.")

    msg = MIMEMultipart()
    msg["From"] = email_user
    msg["To"] = email_to
    msg["Subject"] = subject
    msg.attach(MIMEText(message, "plain"))

    try:
        with smtplib.SMTP_SSL(smtp_server, smtp_port) as server:
            server.login(email_user, email_password)
            server.send_message(msg)
        print("✅ Email envoyé avec succès.")
    except Exception as e:
        print(f"❌ Échec de l'envoi de l'email : {e}")