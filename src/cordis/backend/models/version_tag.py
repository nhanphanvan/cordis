from uuid import uuid4

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from cordis.backend.models.base import TimestampedModel


class VersionTag(TimestampedModel):
    __tablename__ = "version_tags"
    __table_args__ = (UniqueConstraint("repository_id", "name", name="uq_version_tags_repository_name"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    repository_id: Mapped[int] = mapped_column(ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False)
    version_id: Mapped[str] = mapped_column(ForeignKey("versions.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    version = relationship("Version")
