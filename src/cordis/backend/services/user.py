from cordis.backend.errors import ConflictError, NotFoundError
from cordis.backend.models import User
from cordis.backend.repositories.unit_of_work import UnitOfWork
from cordis.backend.security.passwords import hash_password


class UserService:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    async def get_user(self, user_id: int) -> User:
        user = await self.uow.users.get(user_id)
        if user is None:
            raise NotFoundError("User not found")
        return user

    async def get_user_by_email(self, email: str) -> User:
        user = await self.uow.users.get_by_email(email)
        if user is None:
            raise NotFoundError("User not found")
        return user

    async def list_users(self) -> list[User]:
        users, _ = await self.uow.users.list()
        return list(users)

    async def update_user(
        self,
        user_id: int,
        *,
        email: str | None = None,
        is_active: bool | None = None,
        is_admin: bool | None = None,
    ) -> User:
        user = await self.get_user(user_id)
        if email is not None and email != user.email:
            existing = await self.uow.users.get_by_email(email)
            if existing is not None and existing.id != user.id:
                raise ConflictError("User email already exists")
            user.email = email
        if is_active is not None:
            user.is_active = is_active
        if is_admin is not None:
            user.is_admin = is_admin
        await self.uow.commit()
        return user

    async def create_user(
        self,
        *,
        email: str,
        password: str,
        is_active: bool,
        is_admin: bool,
    ) -> User:
        existing = await self.uow.users.get_by_email(email)
        if existing is not None:
            raise ConflictError("User email already exists")
        user = await self.uow.users.create(
            email=email,
            password_hash=hash_password(password),
            is_active=is_active,
            is_admin=is_admin,
        )
        await self.uow.commit()
        return user

    async def delete_user(self, user_id: int) -> User:
        user = await self.get_user(user_id)
        await self.uow.users.delete(user)
        await self.uow.commit()
        return user
