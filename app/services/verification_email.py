from app.config import APP_NAME


def build_verification_email(full_name: str, verify_url: str) -> tuple[str, str]:
    subject = f"Verify your email for {APP_NAME}"

    safe_name = full_name.strip() or "there"
    html = f"""
    <html>
      <body style="font-family: Arial, sans-serif; line-height: 1.5;">
        <h2>{APP_NAME}</h2>
        <p>Hi {safe_name},</p>
        <p>Thanks for registering. Please verify your email address by clicking the button below:</p>
        <p>
          <a href="{verify_url}" style="
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
        <p><a href="{verify_url}">{verify_url}</a></p>
        <hr/>
        <p style="color:#666; font-size:12px;">
          If you did not create an account, you can ignore this email.
        </p>
      </body>
    </html>
    """
    return subject, html
