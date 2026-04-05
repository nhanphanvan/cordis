import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib import error, request

from cordis.cli.config.files import ensure_global_config, get_global_config_path, read_config
from cordis.cli.transfer import (
    copy_from_cache,
    download_to_path,
    iter_files,
    read_file_base64,
    save_to_cache,
    sha256_file,
)


@dataclass(slots=True)
class CordisClient:
    base_url: str
    token: str | None = None

    def login(self, *, email: str, password: str) -> str:
        response = self._request(
            method="POST",
            path="/api/v1/auth/login",
            payload={"email": email, "password": password},
        )
        return str(response["access_token"])

    def get_me(self) -> dict[str, Any]:
        return self._request(method="GET", path="/api/v1/users/me")

    def list_users(self) -> list[dict[str, Any]]:
        response = self._request(method="GET", path="/api/v1/admin/users")
        return list(response.get("items", []))

    def get_user(self, *, user_id: int) -> dict[str, Any]:
        return self._request(method="GET", path=f"/api/v1/users/{user_id}")

    def get_user_by_email(self, *, email: str) -> dict[str, Any]:
        return self._request(method="GET", path=f"/api/v1/users/emails/{email}")

    def list_my_repositories(self) -> list[dict[str, Any]]:
        response = self._request(method="GET", path="/api/v1/users/me/repositories")
        return list(response.get("items", []))

    def create_repository(self, *, name: str, is_public: bool) -> dict[str, Any]:
        return self._request(
            method="POST",
            path="/api/v1/repositories",
            payload={"name": name, "description": name, "is_public": is_public},
        )

    def update_repository(self, *, repository_id: int, is_public: bool) -> dict[str, Any]:
        return self._request(
            method="PATCH",
            path=f"/api/v1/repositories/{repository_id}",
            payload={"is_public": is_public},
        )

    def delete_repository(self, *, repository_id: int) -> dict[str, Any]:
        return self._request(method="DELETE", path=f"/api/v1/repositories/{repository_id}")

    def list_repository_versions(self, *, repository_id: int) -> list[dict[str, Any]]:
        response = self._request(method="GET", path=f"/api/v1/repositories/{repository_id}/versions")
        return list(response.get("items", []))

    def list_repository_members(self, *, repository_id: int) -> list[dict[str, Any]]:
        response = self._request(method="GET", path=f"/api/v1/repositories/{repository_id}/members")
        return list(response.get("items", []))

    def add_repository_member(self, *, repository_id: int, email: str, role: str) -> dict[str, Any]:
        user = self._request(method="GET", path=f"/api/v1/users/emails/{email}")
        return self._request(
            method="POST",
            path=f"/api/v1/repositories/{repository_id}/members",
            payload={"user_id": user["id"], "role": role},
        )

    def update_repository_member(self, *, repository_id: int, email: str, role: str) -> dict[str, Any]:
        user = self._request(method="GET", path=f"/api/v1/users/emails/{email}")
        return self._request(
            method="PATCH",
            path=f"/api/v1/repositories/{repository_id}/members/{user['id']}",
            payload={"role": role},
        )

    def delete_repository_member(self, *, repository_id: int, email: str) -> dict[str, Any]:
        user = self._request(method="GET", path=f"/api/v1/users/emails/{email}")
        return self._request(
            method="DELETE",
            path=f"/api/v1/repositories/{repository_id}/members/{user['id']}",
        )

    def get_version(self, *, repository_id: int, name: str) -> dict[str, Any]:
        return self._request(
            method="GET",
            path=f"/api/v1/versions?repository_id={repository_id}&name={name}",
        )

    def create_version(self, *, repository_id: int, name: str) -> dict[str, Any]:
        return self._request(
            method="POST",
            path="/api/v1/versions",
            payload={"repository_id": repository_id, "name": name},
        )

    def delete_version(self, *, repository_id: int, name: str) -> None:
        version = self.get_version(repository_id=repository_id, name=name)
        self._request(method="DELETE", path=f"/api/v1/versions/{version['id']}")

    def list_tags(self, *, repository_id: int) -> list[dict[str, Any]]:
        response = self._request(method="GET", path=f"/api/v1/repositories/{repository_id}/tags")
        return list(response.get("items", []))

    def get_tag(self, *, repository_id: int, name: str) -> dict[str, Any]:
        return self._request(
            method="GET",
            path=f"/api/v1/tags?repository_id={repository_id}&name={name}",
        )

    def create_tag(self, *, repository_id: int, version_name: str, name: str) -> dict[str, Any]:
        version = self._request(
            method="GET",
            path=f"/api/v1/versions?repository_id={repository_id}&name={version_name}",
        )
        return self._request(
            method="POST",
            path="/api/v1/tags",
            payload={"repository_id": repository_id, "version_id": version["id"], "name": name},
        )

    def delete_tag(self, *, repository_id: int, name: str) -> None:
        tag = self.get_tag(repository_id=repository_id, name=name)
        self._request(method="DELETE", path=f"/api/v1/tags/{tag['id']}")

    def download_item(
        self,
        *,
        repository_id: int,
        version_name: str,
        path: str,
        save_path: str,
    ) -> dict[str, Any]:
        version = self._request(
            method="GET",
            path=f"/api/v1/versions?repository_id={repository_id}&name={version_name}",
        )
        artifact = self._request(
            method="GET",
            path=f"/api/v1/versions/{version['id']}/artifacts/by-path?path={path}",
        )
        download = self._request(
            method="POST",
            path=f"/api/v1/versions/{version['id']}/artifacts/{artifact['id']}/download",
        )
        download["save_path"] = save_path
        return download

    def list_version_artifacts(self, *, repository_id: int, version_name: str) -> list[dict[str, Any]]:
        version = self._request(
            method="GET",
            path=f"/api/v1/versions?repository_id={repository_id}&name={version_name}",
        )
        response = self._request(method="GET", path=f"/api/v1/versions/{version['id']}/artifacts")
        return list(response.get("items", []))

    def upload_directory(
        self,
        *,
        repository_id: int,
        version_name: str,
        folder_path: str,
        create_version_if_missing: bool = False,
    ) -> dict[str, Any]:
        try:
            version = self.get_version(repository_id=repository_id, name=version_name)
        except RuntimeError:
            if not create_version_if_missing:
                raise
            version = self.create_version(repository_id=repository_id, name=version_name)
        root = Path(folder_path)
        uploaded: list[str] = []
        for file_path, relative_path in iter_files(root):
            checksum = sha256_file(file_path)
            size = file_path.stat().st_size
            session = self._request(
                method="POST",
                path="/api/v1/uploads/sessions",
                payload={
                    "version_id": version["id"],
                    "path": relative_path,
                    "checksum": checksum,
                    "size": size,
                },
            )
            self._request(
                method="POST",
                path=f"/api/v1/uploads/sessions/{session['id']}/parts",
                payload={"part_number": 1, "content_base64": read_file_base64(file_path)},
            )
            self._request(method="POST", path=f"/api/v1/uploads/sessions/{session['id']}/complete")
            save_to_cache(str(repository_id), checksum, file_path)
            uploaded.append(relative_path)
        return {"uploaded": uploaded}

    def download_version(self, *, repository_id: int, version_name: str, save_dir: str) -> dict[str, Any]:
        artifacts = self.list_version_artifacts(repository_id=repository_id, version_name=version_name)
        save_root = Path(save_dir)
        downloaded: list[str] = []
        for artifact in artifacts:
            artifact_path = str(artifact["path"])
            checksum = str(artifact["checksum"])
            destination = save_root / artifact_path
            if copy_from_cache(str(repository_id), checksum, destination):
                downloaded.append(artifact_path)
                continue
            download = self.download_item(
                repository_id=repository_id,
                version_name=version_name,
                path=artifact_path,
                save_path=str(destination),
            )
            download_to_path(str(download["download_url"]), destination)
            save_to_cache(str(repository_id), checksum, destination)
            downloaded.append(artifact_path)
        return {"downloaded": downloaded}

    def _request(self, *, method: str, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        body = None if payload is None else json.dumps(payload).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        req = request.Request(f"{self.base_url.rstrip('/')}{path}", data=body, headers=headers, method=method)
        try:
            with request.urlopen(req) as response:
                content = response.read().decode("utf-8")
        except error.HTTPError as exc:
            detail = exc.read().decode("utf-8")
            raise RuntimeError(detail or f"Request failed with status {exc.code}") from exc
        return json.loads(content) if content else {}


def get_client() -> CordisClient:
    ensure_global_config()
    config = read_config(get_global_config_path())
    base_url = str(config.get("endpoint") or "http://127.0.0.1:8000")
    token = config.get("token")
    return CordisClient(base_url=base_url, token=None if token is None else str(token))
