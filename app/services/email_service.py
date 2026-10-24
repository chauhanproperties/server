"""Email delivery through the Gmail API."""
import base64
from email.message import EmailMessage
import json
from urllib.parse import urlencode
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.config import settings

def send_email(to_email: str, subject: str, text: str) -> None:
    credentials = (settings.gmail_client_id, settings.gmail_client_secret, settings.gmail_refresh_token, settings.gmail_sender)
    if not all(credentials):
        raise RuntimeError("Gmail email is not configured. Set GMAIL_CLIENT_ID, GMAIL_CLIENT_SECRET, GMAIL_REFRESH_TOKEN, and GMAIL_SENDER.")

    token_payload = urlencode({
        "client_id": settings.gmail_client_id,
        "client_secret": settings.gmail_client_secret,
        "refresh_token": settings.gmail_refresh_token,
        "grant_type": "refresh_token",
    }).encode()
    token_request = Request(
        "https://oauth2.googleapis.com/token",
        data=token_payload,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    try:
        with urlopen(token_request, timeout=20) as response:
            access_token = json.loads(response.read()).get("access_token")
        if not access_token:
            raise RuntimeError("Google did not return an access token.")

        message = EmailMessage()
        message["From"] = settings.gmail_sender
        message["To"] = to_email
        message["Subject"] = subject
        message.set_content(text)
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode().rstrip("=")
        payload = json.dumps({"raw": raw_message}).encode()
        request = Request(
            "https://gmail.googleapis.com/gmail/v1/users/me/messages/send",
            data=payload,
            headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(request, timeout=20) as response:
            if response.status >= 300:
                raise RuntimeError(f"Gmail API rejected the message (HTTP {response.status}).")
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:500]
        raise RuntimeError(f"Gmail email request failed (HTTP {exc.code}): {detail}") from exc
    except (URLError, TimeoutError) as exc:
        raise RuntimeError("Could not reach Google's email service.") from exc

