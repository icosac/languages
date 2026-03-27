from __future__ import annotations

import requests
from django.conf import settings


def build_invite_url(raw_token: str) -> str:
    base_url = getattr(settings, "SITE_BASE_URL", "http://localhost:8000").rstrip("/")
    return f"{base_url}/invite/{raw_token}/"


def build_admin_access_url(raw_token: str) -> str:
    base_url = getattr(settings, "SITE_BASE_URL", "http://localhost:8000").rstrip("/")
    return f"{base_url}/admin/?access_token={raw_token}"


def send_invite_email(recipient_email: str, invite_url: str) -> None:
    api_key = getattr(settings, "MAILJET_API_KEY", "")
    api_secret = getattr(settings, "MAILJET_API_SECRET", "")
    sender_email = getattr(settings, "MAILJET_SENDER_EMAIL", "")
    sender_name = getattr(settings, "MAILJET_SENDER_NAME", "Lumina Lexicon")

    if not api_key or not api_secret or not sender_email:
        raise RuntimeError("Mailjet credentials/sender are not configured.")

    payload = {
        "Messages": [
            {
                "From": {"Email": sender_email, "Name": sender_name},
                "To": [{"Email": recipient_email}],
                "Subject": "Your invitation to Lumina Lexicon",
                "TextPart": (
                    "You have been invited to join Lumina Lexicon. "
                    f"Use this link to complete your account setup: {invite_url}"
                ),
                "HTMLPart": (
                    "<p>You have been invited to join Lumina Lexicon.</p>"
                    f"<p><a href=\"{invite_url}\">Accept invitation</a></p>"
                ),
            }
        ]
    }

    response = requests.post(
        "https://api.mailjet.com/v3.1/send",
        auth=(api_key, api_secret),
        json=payload,
        timeout=20,
    )
    response.raise_for_status()


def send_admin_access_email(recipient_email: str, access_url: str) -> None:
    api_key = getattr(settings, "MAILJET_API_KEY", "")
    api_secret = getattr(settings, "MAILJET_API_SECRET", "")
    sender_email = getattr(settings, "MAILJET_SENDER_EMAIL", "")
    sender_name = getattr(settings, "MAILJET_SENDER_NAME", "Lumina Lexicon")

    if not api_key or not api_secret or not sender_email:
        raise RuntimeError("Mailjet credentials/sender are not configured.")

    payload = {
        "Messages": [
            {
                "From": {"Email": sender_email, "Name": sender_name},
                "To": [{"Email": recipient_email}],
                "Subject": "Admin access link for Lumina",
                "TextPart": (
                    "Use this one-time link to continue admin access login: "
                    f"{access_url}"
                ),
                "HTMLPart": (
                    "<p>Use this one-time link to continue admin access login.</p>"
                    f"<p><a href=\"{access_url}\">Open admin access</a></p>"
                ),
            }
        ]
    }

    response = requests.post(
        "https://api.mailjet.com/v3.1/send",
        auth=(api_key, api_secret),
        json=payload,
        timeout=20,
    )
    response.raise_for_status()
