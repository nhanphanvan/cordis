from __future__ import annotations

import base64
from pathlib import Path
from typing import TYPE_CHECKING, Any

import httpx

from cordis.cli.errors import ApiError, TransportError
from cordis.cli.transfer import (
    copy_from_cache,
    iter_file_chunks,
    iter_files,
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
        reused: list[str] = []
        for file_path, relative_path in iter_files(root):
            checksum = sha256_file(file_path)
            size = file_path.stat().st_size
            resource = await self.client.check_resource(
                version_id=str(version["id"]),
                path=relative_path,
                checksum=checksum,
                size=size,
            )
            if resource.get("status") == "exists" and resource.get("artifact_id") is not None:
                await self.client.attach_artifact(
                    version_id=str(version["id"]),
                    artifact_id=str(resource["artifact_id"]),
                )
                reused.append(relative_path)
                continue
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
            uploaded_parts = {
                int(part["part_number"])
                for part in session.get("parts", [])
                if isinstance(part, dict) and "part_number" in part
            }
            for part_number, chunk in iter_file_chunks(file_path):
                if part_number in uploaded_parts:
                    continue
                await self.client.request(
                    method="POST",
                    path=f"/api/v1/uploads/sessions/{session['id']}/parts",
                    payload={"part_number": part_number, "content_base64": base64.b64encode(chunk).decode("ascii")},
                )
            await self.client.request(method="POST", path=f"/api/v1/uploads/sessions/{session['id']}/complete")
            save_to_cache(str(repository_id), checksum, file_path)
            uploaded.append(relative_path)
        return {"uploaded": uploaded, "reused": reused}

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
            try:
                self.client.transport.stream_download(
                    path=str(download["download_url"]),
                    save_path=destination,
                    show_progress=True,
                )
            except httpx.HTTPError as error:
                raise TransportError("Could not download the artifact", detail=str(error)) from error
            save_to_cache(str(repository_id), checksum, destination)
            downloaded.append(artifact_path)
        return {"downloaded": downloaded}
