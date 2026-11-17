"""Send password reset links through the Gmail HTTPS API."""

import base64
import json
import os
from email.message import EmailMessage
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen


def gmail_reset_sender():
    origin = (os.getenv("TEMPO_PUBLIC_URL") or os.getenv("RENDER_EXTERNAL_URL") or "").rstrip("/")
    sender = os.getenv("TEMPO_RESET_FROM")
    credentials = {
        "client_id": os.getenv("TEMPO_GMAIL_CLIENT_ID"),
        "client_secret": os.getenv("TEMPO_GMAIL_CLIENT_SECRET"),
        "refresh_token": os.getenv("TEMPO_GMAIL_REFRESH_TOKEN"),
        "grant_type": "refresh_token",
    }
    parsed = urlsplit(origin)
    if (not sender or not all(credentials.values()) or parsed.scheme != "https" or
            not parsed.netloc or parsed.path or parsed.query or parsed.fragment or parsed.username):
        return None

    def send(email, token):
        auth = Request("https://oauth2.googleapis.com/token", data=urlencode(credentials).encode(),
                       headers={"Content-Type": "application/x-www-form-urlencoded"})
        with urlopen(auth, timeout=8) as response:
            access_token = json.load(response)["access_token"]

        message = EmailMessage()
        message["From"] = sender
        message["To"] = email
        message["Subject"] = "Reset your TEMPO password"
        message.set_content(
            f"To reset your TEMPO password, open this link within 30 minutes:\n\n"
            f"{origin}/#/reset-password/{token}\n\n"
            "If you didn't request this, you can ignore this email."
        )
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
        request = Request("https://gmail.googleapis.com/gmail/v1/users/me/messages/send",
                          data=json.dumps({"raw": raw}).encode(),
                          headers={"Content-Type": "application/json", "Authorization": f"Bearer {access_token}"})
        with urlopen(request, timeout=8):
            pass

    return send
