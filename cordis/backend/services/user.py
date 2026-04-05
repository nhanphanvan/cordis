from cordis.backend.models import User
from cordis.backend.repositories.unit_of_work import UnitOfWork
from cordis.backend.security import get_password_hash


class UserService:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    async def get_user(self, user_id: int) -> User | None:
        return await self.uow.users.get(user_id)

    async def get_user_by_email(self, email: str) -> User | None:
        return await self.uow.users.get_by_email(email)

    async def list_users(self) -> list[User]:
        users, _ = await self.uow.users.list()
        return list(users)

    async def update_user(
        self,
        user: User,
        *,
        email: str | None = None,
        is_active: bool | None = None,
        is_admin: bool | None = None,
    ) -> User:
        if email is not None and email != user.email:
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
        user = await self.uow.users.create(
            email=email,
            password_hash=get_password_hash(password),
            is_active=is_active,
            is_admin=is_admin,
        )
        await self.uow.commit()
        return user

    async def delete_user(self, user: User) -> User:
        await self.uow.users.delete(user)
        await self.uow.commit()
        return user
