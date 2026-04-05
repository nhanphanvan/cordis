from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from cordis.backend.models.base import TimestampedModel


class VersionArtifact(TimestampedModel):
    __tablename__ = "version_artifacts"
    __table_args__ = (UniqueConstraint("version_id", "artifact_id", name="uq_version_artifacts_version_artifact"),)

    version_id: Mapped[str] = mapped_column(ForeignKey("versions.id", ondelete="CASCADE"), primary_key=True)
    artifact_id: Mapped[str] = mapped_column(ForeignKey("artifacts.id", ondelete="CASCADE"), primary_key=True)

    version = relationship("Version")
    artifact = relationship("Artifact")
