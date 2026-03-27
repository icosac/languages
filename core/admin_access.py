import hashlib
import secrets
from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from .models import AdminAccessToken


def make_raw_token() -> str:
    return secrets.token_urlsafe(32)


def token_hash(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def issue_admin_access_token(email: str) -> tuple[AdminAccessToken, str]:
    raw_token = make_raw_token()
    hashed = token_hash(raw_token)
    expiry_hours = max(1, int(getattr(settings, "ADMIN_ACCESS_TOKEN_HOURS", 1)))
    token = AdminAccessToken.objects.create(
        email=email.strip().lower(),
        token_hash=hashed,
        expires_at=timezone.now() + timedelta(hours=expiry_hours),
    )
    return token, raw_token


def resolve_admin_access_token(raw_token: str):
    hashed = token_hash(raw_token)
    now = timezone.now()
    return (
        AdminAccessToken.objects.filter(
            token_hash=hashed,
            revoked_at__isnull=True,
            used_at__isnull=True,
            expires_at__gt=now,
        )
        .order_by("-id")
        .first()
    )
