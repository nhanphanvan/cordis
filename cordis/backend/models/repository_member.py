from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from cordis.backend.models.base import DatabaseModel

if TYPE_CHECKING:
    from cordis.backend.models.repository import Repository
    from cordis.backend.models.role import Role
    from cordis.backend.models.user import User


class RepositoryMember(DatabaseModel):
    __tablename__ = "repository_members"

    repository_id: Mapped[int] = mapped_column(
        ForeignKey("repositories.id", ondelete="CASCADE"),
        primary_key=True,
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    role_id: Mapped[int] = mapped_column(ForeignKey("roles.id", ondelete="RESTRICT"), nullable=False)

    repository: Mapped[Repository] = relationship(
        back_populates="members",
        passive_deletes=True,
    )
    user: Mapped[User] = relationship(
        back_populates="repository_memberships",
        passive_deletes=True,
    )
    role: Mapped[Role] = relationship(
        back_populates="repository_memberships",
        passive_deletes=True,
    )
