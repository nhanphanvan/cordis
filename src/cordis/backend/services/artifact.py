from pathlib import PurePosixPath

from cordis.backend.models import Artifact
from cordis.backend.repositories.unit_of_work import UnitOfWork
from cordis.shared.errors import ConflictError, NotFoundError, ValidationError


class ArtifactService:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    async def create_artifact(
        self,
        *,
        repository_id: int,
        path: str,
        checksum: str,
        size: int,
        artifact_id: str | None = None,
    ) -> Artifact:
        repository = await self.uow.repositories.get(repository_id)
        if repository is None:
            raise NotFoundError("Repository not found")

        if size < 0:
            raise ValidationError("Artifact size must be non-negative")

        normalized_path = path.strip("/")
        if not normalized_path:
            raise ValidationError("Artifact path must not be empty")

        existing = await self.uow.artifacts.get_by_repository_and_path(
            repository_id=repository_id,
            path=normalized_path,
        )
        if existing is not None:
            raise ConflictError("Artifact path already exists in repository")

        name = PurePosixPath(normalized_path).name
        if not name:
            raise ValidationError("Artifact path must include a file name")

        values = {
            "repository_id": repository_id,
            "path": normalized_path,
            "name": name,
            "checksum": checksum,
            "size": size,
        }
        if artifact_id is not None:
            values["id"] = artifact_id

        artifact = await self.uow.artifacts.create(**values)
        await self.uow.commit()
        return artifact

    async def resolve_or_create_artifact(
        self,
        *,
        repository_id: int,
        artifact_id: str,
        path: str,
        checksum: str,
        size: int,
    ) -> Artifact:
        existing = await self.uow.artifacts.get_by_repository_and_path(
            repository_id=repository_id,
            path=path.strip("/"),
        )
        if existing is not None:
            if existing.checksum == checksum and existing.size == size:
                return existing
            raise ConflictError("Artifact path already exists in repository with different metadata")
        return await self.create_artifact(
            repository_id=repository_id,
            path=path,
            checksum=checksum,
            size=size,
            artifact_id=artifact_id,
        )

    async def get_artifact(self, artifact_id: str) -> Artifact:
        artifact = await self.uow.artifacts.get(artifact_id)
        if artifact is None:
            raise NotFoundError("Artifact not found")
        return artifact
