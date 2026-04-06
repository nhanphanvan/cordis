from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import ForeignKey, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from cordis.backend.models.base import DatabaseModel

if TYPE_CHECKING:
    from cordis.backend.models.version import Version


class VersionTag(DatabaseModel):
    __tablename__ = "version_tags"
    __table_args__ = (UniqueConstraint("repository_id", "name", name="uq_version_tags_repository_name"),)

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    repository_id: Mapped[int] = mapped_column(ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False)
    version_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("versions.id", ondelete="CASCADE"),
        nullable=False,
    )

    version: Mapped[Version] = relationship(passive_deletes=True)
