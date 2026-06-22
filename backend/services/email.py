"""Transactional email via Brevo API."""
import json
import os
import urllib.error
import urllib.request

BREVO_API_URL = "https://api.brevo.com/v3/smtp/email"


def email_service_configured():
    return bool(
        os.environ.get("BREVO_API_KEY", "").strip()
        and os.environ.get("MAIL_FROM", "").strip()
    )


def send_password_reset_email(to_email, reset_url):
    api_key = os.environ.get("BREVO_API_KEY", "").strip()
    mail_from = os.environ.get("MAIL_FROM", "").strip()
    if not api_key or not mail_from:
        return False, "Email service is not configured"

    html = f"""
    <div style="font-family:Arial,sans-serif;max-width:520px;margin:0 auto;color:#1a1a2e;">
      <h2 style="color:#1a1a2e;">Reset your password</h2>
      <p>We received a request to reset the password for your Ashritha Jewellers account.</p>
      <p style="margin:28px 0;">
        <a href="{reset_url}"
           style="background:#c9a227;color:#fff;text-decoration:none;padding:12px 24px;
                  border-radius:4px;font-weight:bold;display:inline-block;">
          Reset Password
        </a>
      </p>
      <p style="color:#666;font-size:14px;">This link expires in 15 minutes and can only be used once.</p>
      <p style="color:#666;font-size:14px;">If you did not request this, you can safely ignore this email.</p>
      <hr style="border:none;border-top:1px solid #eee;margin:24px 0;">
      <p style="color:#999;font-size:12px;">Ashritha Jewellers</p>
    </div>
    """

    payload = {
        "sender": {"name": "Ashritha Jewellers", "email": mail_from},
        "to": [{"email": to_email}],
        "subject": "Reset your Ashritha Jewellers password",
        "htmlContent": html,
    }

    req = urllib.request.Request(
        BREVO_API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "accept": "application/json",
            "content-type": "application/json",
            "api-key": api_key,
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            if 200 <= resp.status < 300:
                return True, None
            return False, f"Brevo returned status {resp.status}"
    except urllib.error.HTTPError as exc:
        try:
            body = json.loads(exc.read().decode("utf-8"))
            message = body.get("message") or body.get("error") or str(exc)
        except Exception:
            message = str(exc)
        return False, message
    except Exception as exc:
        return False, str(exc)
