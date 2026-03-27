import base64
import hashlib

from cryptography.fernet import Fernet
from django.conf import settings
from django.db import models


def _build_fernet() -> Fernet:
    # Use an explicit key when provided; fallback derives from SECRET_KEY for dev.
    raw_key = getattr(settings, "DATA_ENCRYPTION_KEY", "")
    if raw_key:
        key = raw_key.encode("utf-8")
    else:
        digest = hashlib.sha256(settings.SECRET_KEY.encode("utf-8")).digest()
        key = base64.urlsafe_b64encode(digest)
    return Fernet(key)


class EncryptedTextField(models.TextField):
    def get_prep_value(self, value):
        value = super().get_prep_value(value)
        if value in (None, ""):
            return value
        return _build_fernet().encrypt(str(value).encode("utf-8")).decode("utf-8")

    def from_db_value(self, value, expression, connection):
        if value in (None, ""):
            return value
        return _build_fernet().decrypt(value.encode("utf-8")).decode("utf-8")

    def to_python(self, value):
        if value in (None, "") or not isinstance(value, str):
            return value
        try:
            return _build_fernet().decrypt(value.encode("utf-8")).decode("utf-8")
        except Exception:
            return value
