import os
import resend
from app.config import settings

resend.api_key = settings.RESEND_API_KEY

async def send_reset_email(to_email: str, token: str):
    if not settings.RESEND_API_KEY:
        print(f"STUB EMAIL: Password reset token for {to_email} is {token}")
        return

    try:
        r = resend.Emails.send({
            "from": "onboarding@resend.dev",
            "to": to_email,
            "subject": "Password Reset",
            "html": f"<p>Your password reset token is: <strong>{token}</strong></p>"
        })
        print(f"Email sent: {r}")
    except Exception as e:
        print(f"Error sending email: {e}")
