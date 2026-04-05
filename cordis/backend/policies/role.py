from cordis.backend.models import User


class RolePolicy:
    @classmethod
    async def read(cls, actor: User | None) -> bool:
        return actor is not None

    @classmethod
    async def admin(cls, actor: User | None) -> bool:
        return actor is not None and actor.is_admin
