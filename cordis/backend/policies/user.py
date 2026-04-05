from cordis.backend.models import User


class UserPolicy:
    @classmethod
    async def authenticated(cls, actor: User | None) -> bool:
        return actor is not None

    @classmethod
    async def admin(cls, actor: User | None) -> bool:
        return actor is not None and actor.is_admin

    @classmethod
    async def self_or_admin(cls, actor: User | None, target_user_id: int) -> bool:
        return actor is not None and (actor.is_admin or actor.id == target_user_id)
