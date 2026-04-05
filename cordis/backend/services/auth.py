import logging

from cordis.backend.models import User
from cordis.backend.repositories.unit_of_work import UnitOfWork
from cordis.backend.schemas.responses.auth import TokenResponse
from cordis.backend.security import create_access_token

logger = logging.getLogger(__name__)


class AuthService:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    async def login(self, user: User) -> TokenResponse:
        logger.info("Authentication succeeded user_id=%s email=%s", user.id, user.email)
        return TokenResponse(access_token=create_access_token({"sub": str(user.id), "is_admin": user.is_admin}))
