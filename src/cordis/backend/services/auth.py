from cordis.backend.errors import AuthenticationError
from cordis.backend.models import User
from cordis.backend.repositories.unit_of_work import UnitOfWork
from cordis.backend.schemas.auth import LoginRequest, TokenResponse
from cordis.backend.security import create_access_token, decode_access_token, verify_password


class AuthService:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    async def login(self, credentials: LoginRequest) -> TokenResponse:
        user = await self.uow.users.get_by_email(credentials.email)
        if user is None or not user.is_active:
            raise AuthenticationError("Invalid credentials")
        if not verify_password(credentials.password, user.password_hash):
            raise AuthenticationError("Invalid credentials")

        return TokenResponse(access_token=create_access_token(subject=str(user.id), is_admin=user.is_admin))

    async def get_current_user(self, token: str) -> User:
        payload = decode_access_token(token)
        subject = payload.get("sub")
        if subject is None:
            raise AuthenticationError("Invalid bearer token")

        user = await self.uow.users.get(int(subject))
        if user is None or not user.is_active:
            raise AuthenticationError("Invalid bearer token")
        return user
