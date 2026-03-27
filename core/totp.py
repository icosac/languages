import base64
import hashlib
import hmac
import struct
import time


def _normalize_secret(secret: str) -> str:
    return "".join((secret or "").strip().split()).upper()


def _hotp(secret: str, counter: int, digits: int = 6) -> str:
    normalized_secret = _normalize_secret(secret)
    key = base64.b32decode(normalized_secret, casefold=True)
    msg = struct.pack(">Q", counter)
    digest = hmac.new(key, msg, hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    code_int = struct.unpack(">I", digest[offset:offset + 4])[0] & 0x7FFFFFFF
    return str(code_int % (10 ** digits)).zfill(digits)


def generate_totp_code(
    secret: str,
    *,
    for_time: int | None = None,
    period: int = 30,
    digits: int = 6,
) -> str:
    ts = int(time.time()) if for_time is None else int(for_time)
    counter = ts // period
    return _hotp(secret, counter, digits=digits)


def verify_totp_code(
    secret: str,
    code: str,
    *,
    for_time: int | None = None,
    period: int = 30,
    digits: int = 6,
    window: int = 1,
) -> bool:
    candidate = (code or "").strip()
    if not candidate.isdigit() or len(candidate) != digits:
        return False

    try:
        ts = int(time.time()) if for_time is None else int(for_time)
        counter = ts // period
        for delta in range(-window, window + 1):
            if hmac.compare_digest(_hotp(secret, counter + delta, digits=digits), candidate):
                return True
    except Exception:
        return False
    return False
