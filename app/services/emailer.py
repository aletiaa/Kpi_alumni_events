import smtplib
from email.message import EmailMessage

from app.config import (
    APP_NAME,
    EMAIL_ENABLED,
    SMTP_HOST,
    SMTP_PORT,
    SMTP_TLS,
    SMTP_USERNAME,
    SMTP_PASSWORD,
    EMAIL_FROM_NAME,
    EMAIL_FROM_EMAIL,
)
from app.services.email_service import send_email
from app.config import APP_NAME, EMAIL_ENABLED, SMTP_HOST, SMTP_USERNAME, SMTP_PASSWORD, EMAIL_FROM_EMAIL

def send_verification_email(to_email: str, verify_link: str) -> None:
    if not EMAIL_ENABLED:
        return

    missing = []
    if not SMTP_HOST: missing.append("SMTP_HOST")
    if not SMTP_USERNAME: missing.append("SMTP_USERNAME")
    if not SMTP_PASSWORD: missing.append("SMTP_PASSWORD")
    if not EMAIL_FROM_EMAIL: missing.append("EMAIL_FROM_EMAIL")
    if missing:
        raise RuntimeError(f"SMTP not configured. Missing: {', '.join(missing)}")

    subject = f"Verify your email for {APP_NAME}"
    html_body = f"""
    <html>
      <body style="font-family: Arial, sans-serif; line-height: 1.5;">
        <h2>{APP_NAME}</h2>
        <p>Thanks for registering.</p>
        <p>Please verify your email by clicking the button below:</p>
        <p>
          <a href="{verify_link}" style="
            display:inline-block;
            padding:10px 16px;
            background:#0d6efd;
            color:white;
            text-decoration:none;
            border-radius:6px;">
            Verify email
          </a>
        </p>
        <p>If the button does not work, copy and paste this link into your browser:</p>
        <p><a href="{verify_link}">{verify_link}</a></p>
        <hr/>
        <p style="color:#666; font-size:12px;">
          If you did not create this account, you can ignore this email.
        </p>
      </body>
    </html>
    """
    send_email(to_email=to_email, subject=subject, html_body=html_body)

def send_reset_password_email(to_email: str, reset_link: str) -> None:
    """
    Sends a password reset email via SMTP (Gmail App Password).
    Deployment-ready and consistent with verification email.
    """

    if not EMAIL_ENABLED:
        return

    missing = []
    if not SMTP_HOST: missing.append("SMTP_HOST")
    if not SMTP_USERNAME: missing.append("SMTP_USERNAME")
    if not SMTP_PASSWORD: missing.append("SMTP_PASSWORD")
    if not EMAIL_FROM_EMAIL: missing.append("EMAIL_FROM_EMAIL")
    if missing:
        raise RuntimeError(f"SMTP not configured. Missing: {', '.join(missing)}")

    subject = f"Reset your password for {APP_NAME}"

    html_body = f"""
    <html>
      <body style="font-family: Arial, sans-serif; line-height: 1.5;">
        <h2>{APP_NAME}</h2>

        <p>We received a request to reset your password.</p>

        <p>
          <a href="{reset_link}" style="
            display:inline-block;
            padding:10px 16px;
            background:#dc3545;
            color:white;
            text-decoration:none;
            border-radius:6px;">
            Reset password
          </a>
        </p>

        <p>If the button does not work, copy and paste this link:</p>
        <p><a href="{reset_link}">{reset_link}</a></p>

        <p><b>This link is valid for 30 minutes.</b></p>

        <hr/>
        <p style="color:#666; font-size:12px;">
          If you did not request a password reset, you can safely ignore this email.
        </p>
      </body>
    </html>
    """

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = f"{EMAIL_FROM_NAME} <{EMAIL_FROM_EMAIL}>"
    msg["To"] = to_email

    msg.set_content(f"Reset your password: {reset_link}")
    msg.add_alternative(html_body, subtype="html")

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=20) as server:
        if SMTP_TLS:
            server.starttls()
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        server.send_message(msg)
