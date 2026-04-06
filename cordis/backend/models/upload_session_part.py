from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from cordis.backend.models.base import DatabaseModel

if TYPE_CHECKING:
    from cordis.backend.models.upload_session import UploadSession


class UploadSessionPart(DatabaseModel):
    __tablename__ = "upload_session_parts"
    __table_args__ = (UniqueConstraint("session_id", "part_number", name="uq_upload_session_parts_session_part"),)

    id: Mapped[int] = mapped_column(Integer(), primary_key=True, autoincrement=True)
    session_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("upload_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    part_number: Mapped[int] = mapped_column(Integer(), nullable=False)
    etag: Mapped[str] = mapped_column(String(255), nullable=False)

    session: Mapped[UploadSession] = relationship(
        back_populates="parts",
        passive_deletes=True,
    )
