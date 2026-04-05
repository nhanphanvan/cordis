from uuid import uuid4

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from cordis.backend.models.base import TimestampedModel


class UploadSession(TimestampedModel):
    __tablename__ = "upload_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    repository_id: Mapped[int] = mapped_column(ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False)
    version_id: Mapped[str] = mapped_column(ForeignKey("versions.id", ondelete="CASCADE"), nullable=False)
    artifact_id: Mapped[str] = mapped_column(String(36), nullable=False, default=lambda: str(uuid4()))
    path: Mapped[str] = mapped_column(String(1024), nullable=False)
    checksum: Mapped[str] = mapped_column(String(255), nullable=False)
    size: Mapped[int] = mapped_column(Integer(), nullable=False)
    upload_id: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    error_message: Mapped[str | None] = mapped_column(String(255), nullable=True)

    repository = relationship("Repository")
    version = relationship("Version")
