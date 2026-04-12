from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from cordis.backend.enums import RepositoryVisibility
from cordis.backend.models.base import DatabaseModel

if TYPE_CHECKING:
    from cordis.backend.models.repository_member import RepositoryMember


class Repository(DatabaseModel):
    __tablename__ = "repositories"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    visibility: Mapped[str] = mapped_column(String(32), default=RepositoryVisibility.PRIVATE.value, nullable=False)
    allow_public_object_urls: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    members: Mapped[list[RepositoryMember]] = relationship(
        back_populates="repository",
        passive_deletes=True,
        cascade="all, delete-orphan",
    )
