from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import ForeignKey, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from cordis.backend.models.base import DatabaseModel

if TYPE_CHECKING:
    from cordis.backend.models.repository import Repository
    from cordis.backend.models.upload_session_part import UploadSessionPart
    from cordis.backend.models.version import Version


class UploadSession(DatabaseModel):
    __tablename__ = "upload_sessions"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    repository_id: Mapped[int] = mapped_column(ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False)
    version_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("versions.id", ondelete="CASCADE"),
        nullable=False,
    )
    artifact_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, default=uuid4)
    path: Mapped[str] = mapped_column(String(1024), nullable=False)
    checksum: Mapped[str] = mapped_column(String(255), nullable=False)
    size: Mapped[int] = mapped_column(Integer(), nullable=False)
    upload_id: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    error_message: Mapped[str | None] = mapped_column(String(255), nullable=True)

    repository: Mapped[Repository] = relationship(passive_deletes=True)
    version: Mapped[Version] = relationship(passive_deletes=True)
    parts: Mapped[list[UploadSessionPart]] = relationship(
        back_populates="session",
        passive_deletes=True,
        cascade="all, delete-orphan",
    )
