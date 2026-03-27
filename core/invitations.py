import hashlib
import secrets
from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from .models import Invitation


def make_raw_token() -> str:
    return secrets.token_urlsafe(32)


def token_hash(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def issue_invite(email: str, invited_by=None) -> tuple[Invitation, str]:
    raw_token = make_raw_token()
    hashed = token_hash(raw_token)
    expiry_hours = max(1, int(getattr(settings, "INVITE_EXPIRY_HOURS", 168)))
    invite = Invitation.objects.create(
        email=email.strip().lower(),
        token_hash=hashed,
        invited_by=invited_by,
        expires_at=timezone.now() + timedelta(hours=expiry_hours),
    )
    return invite, raw_token


def resolve_invite(raw_token: str):
    hashed = token_hash(raw_token)
    now = timezone.now()
    invite = (
        Invitation.objects.filter(token_hash=hashed, revoked_at__isnull=True, used_at__isnull=True)
        .filter(expires_at__gt=now)
        .first()
    )
    return invite
