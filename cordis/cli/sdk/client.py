from dataclasses import dataclass, field
from typing import Any

from cordis.cli.config.files import ensure_global_config, get_global_config_path, read_config
from cordis.cli.sdk.apis import AuthAPI, RepositoriesAPI, TagsAPI, UsersAPI, VersionsAPI
from cordis.cli.sdk.transfers import TransferHelper
from cordis.cli.utils.httpx_service import HttpxService


@dataclass(slots=True)
class CordisClient:
    base_url: str
    token: str | None = None
    transport: HttpxService = field(init=False)
    auth: AuthAPI = field(init=False)
    users: UsersAPI = field(init=False)
    repositories: RepositoriesAPI = field(init=False)
    versions: VersionsAPI = field(init=False)
    tags: TagsAPI = field(init=False)
    transfers: TransferHelper = field(init=False)

    def __post_init__(self) -> None:
        self.transport = HttpxService(base_url=self.base_url.rstrip("/"))
        self.auth = AuthAPI(client=self)
        self.users = UsersAPI(client=self)
        self.repositories = RepositoriesAPI(client=self)
        self.versions = VersionsAPI(client=self)
        self.tags = TagsAPI(client=self)
        self.transfers = TransferHelper(client=self)

    async def login(self, *, email: str, password: str) -> str:
        return await self.auth.login(email=email, password=password)

    async def get_me(self) -> dict[str, Any]:
        return await self.users.get_me()

    async def list_users(self) -> list[dict[str, Any]]:
        return await self.users.list_users()

    async def get_user(self, *, user_id: int) -> dict[str, Any]:
        return await self.users.get_user(user_id=user_id)

    async def get_user_by_email(self, *, email: str) -> dict[str, Any]:
        return await self.users.get_user_by_email(email=email)

    async def list_my_repositories(self) -> list[dict[str, Any]]:
        return await self.users.list_my_repositories()

    async def create_repository(self, *, name: str, is_public: bool) -> dict[str, Any]:
        return await self.repositories.create_repository(name=name, is_public=is_public)

    async def update_repository(self, *, repository_id: int, is_public: bool) -> dict[str, Any]:
        return await self.repositories.update_repository(repository_id=repository_id, is_public=is_public)

    async def delete_repository(self, *, repository_id: int) -> dict[str, Any]:
        return await self.repositories.delete_repository(repository_id=repository_id)

    async def list_repository_versions(self, *, repository_id: int) -> list[dict[str, Any]]:
        return await self.repositories.list_repository_versions(repository_id=repository_id)

    async def list_repository_members(self, *, repository_id: int) -> list[dict[str, Any]]:
        return await self.repositories.list_repository_members(repository_id=repository_id)

    async def add_repository_member(self, *, repository_id: int, email: str, role: str) -> dict[str, Any]:
        return await self.repositories.add_repository_member(repository_id=repository_id, email=email, role=role)

    async def update_repository_member(self, *, repository_id: int, email: str, role: str) -> dict[str, Any]:
        return await self.repositories.update_repository_member(repository_id=repository_id, email=email, role=role)

    async def delete_repository_member(self, *, repository_id: int, email: str) -> dict[str, Any]:
        return await self.repositories.delete_repository_member(repository_id=repository_id, email=email)

    async def get_version(self, *, repository_id: int, name: str) -> dict[str, Any]:
        return await self.versions.get_version(repository_id=repository_id, name=name)

    async def create_version(self, *, repository_id: int, name: str) -> dict[str, Any]:
        return await self.versions.create_version(repository_id=repository_id, name=name)

    async def delete_version(self, *, repository_id: int, name: str) -> None:
        await self.versions.delete_version(repository_id=repository_id, name=name)

    async def list_tags(self, *, repository_id: int) -> list[dict[str, Any]]:
        return await self.tags.list_tags(repository_id=repository_id)

    async def get_tag(self, *, repository_id: int, name: str) -> dict[str, Any]:
        return await self.tags.get_tag(repository_id=repository_id, name=name)

    async def create_tag(self, *, repository_id: int, version_name: str, name: str) -> dict[str, Any]:
        return await self.tags.create_tag(repository_id=repository_id, version_name=version_name, name=name)

    async def delete_tag(self, *, repository_id: int, name: str) -> None:
        await self.tags.delete_tag(repository_id=repository_id, name=name)

    async def download_item(
        self,
        *,
        repository_id: int,
        version_name: str,
        path: str,
        save_path: str,
    ) -> dict[str, Any]:
        return await self.versions.download_item(
            repository_id=repository_id,
            version_name=version_name,
            path=path,
            save_path=save_path,
        )

    async def list_version_artifacts(self, *, repository_id: int, version_name: str) -> list[dict[str, Any]]:
        return await self.versions.list_version_artifacts(repository_id=repository_id, version_name=version_name)

    async def upload_directory(
        self,
        *,
        repository_id: int,
        version_name: str,
        folder_path: str,
        create_version_if_missing: bool = False,
    ) -> dict[str, Any]:
        return await self.transfers.upload_directory(
            repository_id=repository_id,
            version_name=version_name,
            folder_path=folder_path,
            create_version_if_missing=create_version_if_missing,
        )

    async def download_version(self, *, repository_id: int, version_name: str, save_dir: str) -> dict[str, Any]:
        return await self.transfers.download_version(
            repository_id=repository_id,
            version_name=version_name,
            save_dir=save_dir,
        )

    async def request(self, *, method: str, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        response = await self.transport.request(method=method, path=path, json=payload, headers=headers)
        if response.status_code >= 400:
            detail = response.text
            raise RuntimeError(detail or f"Request failed with status {response.status_code}")
        return response.json() if response.content else {}


def get_client() -> CordisClient:
    ensure_global_config()
    config = read_config(get_global_config_path())
    base_url = str(config.get("endpoint") or "http://127.0.0.1:8000")
    token = config.get("token")
    return CordisClient(base_url=base_url, token=None if token is None else str(token))
