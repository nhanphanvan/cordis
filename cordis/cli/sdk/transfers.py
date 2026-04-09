from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from cordis.cli.errors import ApiError
from cordis.cli.transfer import (
    copy_from_cache,
    download_to_path,
    iter_files,
    read_file_base64,
    save_to_cache,
    sha256_file,
)

if TYPE_CHECKING:
    from cordis.cli.sdk.client import CordisClient


class TransferHelper:
    def __init__(self, client: CordisClient) -> None:
        self.client = client

    async def upload_directory(
        self,
        *,
        repository_id: int,
        version_name: str,
        folder_path: str,
        create_version_if_missing: bool = False,
    ) -> dict[str, Any]:
        try:
            version = await self.client.get_version(repository_id=repository_id, name=version_name)
        except ApiError as error:
            if error.http_status != 404 and error.app_status_code != 1400:
                raise
            if not create_version_if_missing:
                raise
            version = await self.client.create_version(repository_id=repository_id, name=version_name)

        root = Path(folder_path)
        uploaded: list[str] = []
        for file_path, relative_path in iter_files(root):
            checksum = sha256_file(file_path)
            size = file_path.stat().st_size
            session = await self.client.request(
                method="POST",
                path="/api/v1/uploads/sessions",
                payload={
                    "version_id": version["id"],
                    "path": relative_path,
                    "checksum": checksum,
                    "size": size,
                },
            )
            await self.client.request(
                method="POST",
                path=f"/api/v1/uploads/sessions/{session['id']}/parts",
                payload={"part_number": 1, "content_base64": read_file_base64(file_path)},
            )
            await self.client.request(method="POST", path=f"/api/v1/uploads/sessions/{session['id']}/complete")
            save_to_cache(str(repository_id), checksum, file_path)
            uploaded.append(relative_path)
        return {"uploaded": uploaded}

    async def download_version(self, *, repository_id: int, version_name: str, save_dir: str) -> dict[str, Any]:
        artifacts = await self.client.list_version_artifacts(repository_id=repository_id, version_name=version_name)
        save_root = Path(save_dir)
        downloaded: list[str] = []
        for artifact in artifacts:
            artifact_path = str(artifact["path"])
            checksum = str(artifact["checksum"])
            destination = save_root / artifact_path
            if copy_from_cache(str(repository_id), checksum, destination):
                downloaded.append(artifact_path)
                continue
            download = await self.client.download_item(
                repository_id=repository_id,
                version_name=version_name,
                path=artifact_path,
                save_path=str(destination),
            )
            download_to_path(str(download["download_url"]), destination)
            save_to_cache(str(repository_id), checksum, destination)
            downloaded.append(artifact_path)
        return {"downloaded": downloaded}
