"""Email delivery through Resend's HTTP API."""
import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.config import settings

def send_email(to_email: str, subject: str, text: str) -> None:
    if not settings.email_api_key or not settings.email_sender:
        raise RuntimeError("Email is not configured. Add EMAIL_API_KEY and EMAIL_SENDER to server/.env.")
    if settings.email_provider != "resend":
        raise RuntimeError("EMAIL_PROVIDER currently supports 'resend'.")
    payload = json.dumps({"from": settings.email_sender, "to": [to_email], "subject": subject, "text": text}).encode()
    req = Request("https://api.resend.com/emails", data=payload, headers={"Authorization": f"Bearer {settings.email_api_key}", "Content-Type": "application/json"}, method="POST")
    try:
        with urlopen(req, timeout=20) as response:
            if response.status >= 300:
                raise RuntimeError("The email provider rejected the message.")
    except (HTTPError, URLError, TimeoutError) as exc:
        raise RuntimeError("The email provider could not send the message.") from exc

def send_login_code(to_email: str, code: str) -> None:
    if settings.debug:
        print(f"Local development login code for {to_email}: {code}")
        return
    send_email(to_email, "Your admin login code", f"Your one-time 8-digit login code is {code}. It expires in 10 minutes.")
