from datetime import timedelta

import pytest


def test_security_package_exposes_reference_style_modules() -> None:
    from cordis.backend.security import core
    from cordis.backend.security.authentication.bearer_token_backend import BearerTokenAuthenticationBackend
    from cordis.backend.security.userinfo import UserInfo

    assert callable(core.setup)
    assert callable(core.create_access_token)
    assert callable(core.verify_access_token)
    assert callable(core.get_password_hash)
    assert callable(core.verify_password)
    assert BearerTokenAuthenticationBackend is not None
    assert UserInfo is not None


def test_security_core_creates_and_verifies_jwt_tokens() -> None:
    from cordis.backend.security import core

    core.setup(secret_key="secret-key", jwt_algorithm="HS256", access_token_expire_minutes=60)

    token = core.create_access_token({"sub": "42", "is_admin": True})
    payload = core.verify_access_token(token)

    assert payload["sub"] == "42"
    assert payload["is_admin"] is True
    assert "exp" in payload


def test_security_core_rejects_expired_tokens() -> None:
    from cordis.backend.exceptions import AppStatus, UnauthorizedError
    from cordis.backend.security import core

    core.setup(secret_key="secret-key", jwt_algorithm="HS256", access_token_expire_minutes=60)
    token = core.create_access_token(
        {"sub": "42", "is_admin": False},
        expires_delta=timedelta(seconds=-1),
    )

    with pytest.raises(UnauthorizedError) as error:
        core.verify_access_token(token)

    assert error.value.app_status == AppStatus.ERROR_EXPIRED_BEARER_TOKEN


def test_security_core_hashes_and_verifies_passwords() -> None:
    from cordis.backend.security import core

    password_hash = core.get_password_hash("secret123")

    assert password_hash != "secret123"
    assert core.verify_password("secret123", password_hash) is True
    assert core.verify_password("wrong", password_hash) is False


def test_userinfo_exposes_email_and_identity_properties() -> None:
    from cordis.backend.security.userinfo import UserInfo

    userinfo = UserInfo(email="admin@example.com", identity="7", is_admin=True)

    assert userinfo.is_authenticated is True
    assert userinfo.email == "admin@example.com"
    assert userinfo.identity == "7"
    assert userinfo.display_name == "admin@example.com"
