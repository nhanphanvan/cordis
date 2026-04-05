import base64
import hashlib
import hmac
import json
import time
from typing import TypedDict

from cordis.shared.errors import AuthenticationError
from cordis.shared.settings import get_settings


class TokenPayload(TypedDict):
    sub: str
    is_admin: bool
    exp: int


def _b64encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("utf-8").rstrip("=")


def _b64decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode((value + padding).encode("utf-8"))


def create_access_token(*, subject: str, is_admin: bool) -> str:
    settings = get_settings()
    payload = {
        "sub": subject,
        "is_admin": is_admin,
        "exp": int(time.time()) + (60 * 60),
    }
    payload_bytes = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    payload_token = _b64encode(payload_bytes)
    signature = hmac.new(
        settings.app_name.encode("utf-8"),
        payload_token.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    return f"{payload_token}.{_b64encode(signature)}"


def decode_access_token(token: str) -> TokenPayload:
    try:
        payload_token, signature_token = token.split(".", maxsplit=1)
    except ValueError as error:
        raise AuthenticationError("Invalid bearer token") from error

    settings = get_settings()
    expected_signature = hmac.new(
        settings.app_name.encode("utf-8"),
        payload_token.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    actual_signature = _b64decode(signature_token)
    if not hmac.compare_digest(expected_signature, actual_signature):
        raise AuthenticationError("Invalid bearer token")

    payload = json.loads(_b64decode(payload_token).decode("utf-8"))
    if int(payload["exp"]) < int(time.time()):
        raise AuthenticationError("Expired bearer token")
    return {
        "sub": str(payload["sub"]),
        "is_admin": bool(payload["is_admin"]),
        "exp": int(payload["exp"]),
    }
