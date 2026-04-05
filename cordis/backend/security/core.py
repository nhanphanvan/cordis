from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, cast

from jose import ExpiredSignatureError, JWTError, jwt
from passlib.context import CryptContext

from cordis.backend.config import build_config
from cordis.backend.exceptions import AppStatus, UnauthorizedError

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class _Settings:
    secret_key: str | None = None
    jwt_algorithm: str | None = None
    access_token_expire_minutes: int | None = None


def setup(*, secret_key: str, jwt_algorithm: str, access_token_expire_minutes: int) -> None:
    _Settings.secret_key = secret_key
    _Settings.jwt_algorithm = jwt_algorithm
    _Settings.access_token_expire_minutes = access_token_expire_minutes


def _ensure_setup() -> None:
    if (
        _Settings.secret_key is not None
        and _Settings.jwt_algorithm is not None
        and _Settings.access_token_expire_minutes is not None
    ):
        return
    config = build_config()
    setup(
        secret_key=config.security.secret_key,
        jwt_algorithm=config.security.jwt_algorithm,
        access_token_expire_minutes=config.security.access_token_expire_minutes,
    )


def create_access_token(obj: dict[str, Any], expires_delta: timedelta | None = None) -> str:
    _ensure_setup()
    to_encode = dict(obj)
    ttl = expires_delta or timedelta(minutes=cast(int, _Settings.access_token_expire_minutes))
    expire = datetime.now(timezone.utc) + ttl
    to_encode["exp"] = expire
    token = jwt.encode(to_encode, cast(str, _Settings.secret_key), algorithm=cast(str, _Settings.jwt_algorithm))
    return cast(str, token)


def verify_access_token(token: str) -> dict[str, Any]:
    _ensure_setup()
    try:
        payload_raw = jwt.decode(
            token,
            cast(str, _Settings.secret_key),
            algorithms=[cast(str, _Settings.jwt_algorithm)],
        )
    except ExpiredSignatureError as error:
        raise UnauthorizedError("Expired bearer token", app_status=AppStatus.ERROR_EXPIRED_BEARER_TOKEN) from error
    except JWTError as error:
        raise UnauthorizedError("Invalid bearer token", app_status=AppStatus.ERROR_INVALID_BEARER_TOKEN) from error

    payload = cast(dict[str, Any], payload_raw)
    subject = payload.get("sub")
    if subject is None:
        raise UnauthorizedError("Invalid bearer token", app_status=AppStatus.ERROR_INVALID_BEARER_TOKEN)
    return payload


def get_password_hash(password: str) -> str:
    hashed: str = pwd_context.hash(password)
    return hashed


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bool(pwd_context.verify(plain_password, hashed_password))
