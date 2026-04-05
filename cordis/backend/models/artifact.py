from uuid import uuid4

from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from cordis.backend.models.base import TimestampedModel


class Artifact(TimestampedModel):
    __tablename__ = "artifacts"
    __table_args__ = (UniqueConstraint("repository_id", "path", name="uq_artifacts_repository_path"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    repository_id: Mapped[int] = mapped_column(ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False)
    path: Mapped[str] = mapped_column(String(1024), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    checksum: Mapped[str] = mapped_column(String(255), nullable=False)
    size: Mapped[int] = mapped_column(Integer(), nullable=False)

    repository = relationship("Repository")
