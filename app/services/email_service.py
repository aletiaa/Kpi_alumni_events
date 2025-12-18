import smtplib
from email.message import EmailMessage

from app.config import (
    EMAIL_ENABLED,
    SMTP_HOST,
    SMTP_PORT,
    SMTP_TLS,
    SMTP_USERNAME,
    SMTP_PASSWORD,
    EMAIL_FROM_NAME,
    EMAIL_FROM_EMAIL,
)


def send_email(to_email: str, subject: str, html_body: str) -> None:
    """
    Sends HTML email via SMTP. Designed for deployment environments.
    If EMAIL_ENABLED=false, this function returns without sending.
    """
    if not EMAIL_ENABLED:
        return

    if not (SMTP_HOST and SMTP_USERNAME and SMTP_PASSWORD and EMAIL_FROM_EMAIL):
        raise RuntimeError("SMTP is not configured (missing env vars).")

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = f"{EMAIL_FROM_NAME} <{EMAIL_FROM_EMAIL}>"
    msg["To"] = to_email

    # Plain fallback + HTML
    msg.set_content("Please use an email client that supports HTML.")
    msg.add_alternative(html_body, subtype="html")

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=20) as server:
        if SMTP_TLS:
            server.starttls()
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        server.send_message(msg)
