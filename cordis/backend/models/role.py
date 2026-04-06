from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from cordis.backend.models.base import DatabaseModel

if TYPE_CHECKING:
    from cordis.backend.models.repository_member import RepositoryMember


class Role(DatabaseModel):
    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)

    repository_memberships: Mapped[list[RepositoryMember]] = relationship(
        back_populates="role",
        passive_deletes=True,
    )
