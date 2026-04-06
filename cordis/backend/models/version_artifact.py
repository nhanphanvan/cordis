from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import ForeignKey, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from cordis.backend.models.base import DatabaseModel

if TYPE_CHECKING:
    from cordis.backend.models.artifact import Artifact
    from cordis.backend.models.version import Version


class VersionArtifact(DatabaseModel):
    __tablename__ = "version_artifacts"
    __table_args__ = (UniqueConstraint("version_id", "artifact_id", name="uq_version_artifacts_version_artifact"),)

    version_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("versions.id", ondelete="CASCADE"),
        primary_key=True,
    )
    artifact_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("artifacts.id", ondelete="CASCADE"),
        primary_key=True,
    )

    version: Mapped[Version] = relationship(passive_deletes=True)
    artifact: Mapped[Artifact] = relationship(passive_deletes=True)
