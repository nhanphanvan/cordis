import logging

from cordis.backend.exceptions import AppStatus, NotFoundError, UnauthorizedError
from cordis.backend.models import User
from cordis.backend.repositories.unit_of_work import UnitOfWork
from cordis.backend.schemas.requests.auth import LoginRequest
from cordis.backend.schemas.responses.auth import TokenResponse
from cordis.backend.security import create_access_token, decode_access_token, verify_password

logger = logging.getLogger(__name__)


class AuthService:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    async def login(self, credentials: LoginRequest) -> TokenResponse:
        user = await self.uow.users.get_by_email(credentials.email)
        if user is None or not user.is_active:
            logger.warning("Authentication failed for email=%s reason=missing_or_inactive", credentials.email)
            raise UnauthorizedError("Invalid credentials", app_status=AppStatus.ERROR_INVALID_CREDENTIALS)
        if not verify_password(credentials.password, user.password_hash):
            logger.warning("Authentication failed for email=%s reason=invalid_password", credentials.email)
            raise UnauthorizedError("Invalid credentials", app_status=AppStatus.ERROR_INVALID_CREDENTIALS)

        logger.info("Authentication succeeded user_id=%s email=%s", user.id, user.email)
        return TokenResponse(access_token=create_access_token(subject=str(user.id), is_admin=user.is_admin))

    async def get_current_user(self, token: str) -> User:
        payload = decode_access_token(token)
        subject = payload["sub"]
        user = await self.uow.users.get(int(subject))
        if user is None:
            logger.warning("Bearer token rejected user_id=%s reason=missing", subject)
            raise NotFoundError("User not found", app_status=AppStatus.ERROR_USER_NOT_FOUND)
        if not user.is_active:
            logger.warning("Bearer token rejected user_id=%s reason=missing_or_inactive", subject)
            raise UnauthorizedError("Invalid bearer token", app_status=AppStatus.ERROR_INVALID_BEARER_TOKEN)
        return user
