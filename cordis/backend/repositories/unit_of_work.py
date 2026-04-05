from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from cordis.backend.db.session import get_session_factory
from cordis.backend.repositories.artifact import ArtifactRepository
from cordis.backend.repositories.repository import RepositoryRepository
from cordis.backend.repositories.repository_member import RepositoryMemberRepository
from cordis.backend.repositories.role import RoleRepository
from cordis.backend.repositories.upload_session import UploadSessionRepository
from cordis.backend.repositories.upload_session_part import UploadSessionPartRepository
from cordis.backend.repositories.user import UserRepository
from cordis.backend.repositories.version import VersionRepository
from cordis.backend.repositories.version_artifact import VersionArtifactRepository
from cordis.backend.repositories.version_tag import VersionTagRepository


class UnitOfWork:
    def __init__(self, session: AsyncSession):
        self._session = session
        self._users: UserRepository | None = None
        self._roles: RoleRepository | None = None
        self._repositories: RepositoryRepository | None = None
        self._repository_members: RepositoryMemberRepository | None = None
        self._versions: VersionRepository | None = None
        self._artifacts: ArtifactRepository | None = None
        self._upload_sessions: UploadSessionRepository | None = None
        self._upload_session_parts: UploadSessionPartRepository | None = None
        self._version_artifacts: VersionArtifactRepository | None = None
        self._version_tags: VersionTagRepository | None = None

    @property
    def session(self) -> AsyncSession:
        return self._session

    async def commit(self) -> None:
        await self._session.commit()

    async def rollback(self) -> None:
        await self._session.rollback()

    async def flush(self) -> None:
        await self._session.flush()

    async def refresh(self, instance: Any) -> None:
        await self._session.refresh(instance)

    @property
    def users(self) -> UserRepository:
        if self._users is None:
            self._users = UserRepository(self._session)
        return self._users

    @property
    def roles(self) -> RoleRepository:
        if self._roles is None:
            self._roles = RoleRepository(self._session)
        return self._roles

    @property
    def repositories(self) -> RepositoryRepository:
        if self._repositories is None:
            self._repositories = RepositoryRepository(self._session)
        return self._repositories

    @property
    def repository_members(self) -> RepositoryMemberRepository:
        if self._repository_members is None:
            self._repository_members = RepositoryMemberRepository(self._session)
        return self._repository_members

    @property
    def versions(self) -> VersionRepository:
        if self._versions is None:
            self._versions = VersionRepository(self._session)
        return self._versions

    @property
    def artifacts(self) -> ArtifactRepository:
        if self._artifacts is None:
            self._artifacts = ArtifactRepository(self._session)
        return self._artifacts

    @property
    def upload_sessions(self) -> UploadSessionRepository:
        if self._upload_sessions is None:
            self._upload_sessions = UploadSessionRepository(self._session)
        return self._upload_sessions

    @property
    def upload_session_parts(self) -> UploadSessionPartRepository:
        if self._upload_session_parts is None:
            self._upload_session_parts = UploadSessionPartRepository(self._session)
        return self._upload_session_parts

    @property
    def version_artifacts(self) -> VersionArtifactRepository:
        if self._version_artifacts is None:
            self._version_artifacts = VersionArtifactRepository(self._session)
        return self._version_artifacts

    @property
    def version_tags(self) -> VersionTagRepository:
        if self._version_tags is None:
            self._version_tags = VersionTagRepository(self._session)
        return self._version_tags


@asynccontextmanager
async def get_unit_of_work() -> AsyncGenerator[UnitOfWork, None]:
    session_factory = get_session_factory()
    async with session_factory() as session:
        uow = UnitOfWork(session)
        try:
            yield uow
        except Exception:
            await uow.rollback()
            raise
