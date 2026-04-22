from __future__ import annotations

import base64
import shutil
from contextlib import nullcontext
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable

import httpx

from cordis.cli.utils.files import copy_from_cache, iter_file_chunks, iter_files, save_to_cache, sha256_file
from cordis.cli.utils.presentation import create_download_progress, create_upload_progress
from cordis.sdk.errors import ApiError, TransportError, UploadPreflightError

if TYPE_CHECKING:
    from cordis.sdk.client import CordisClient


class TransferHelper:
    def __init__(self, client: CordisClient) -> None:
        self.client = client

    async def _upload_file(
        self,
        *,
        repository_id: int,
        version_id: str,
        file_path: Path,
        target_path: str,
        on_chunk_uploaded: Callable[[int], None] | None = None,
    ) -> None:
        checksum = sha256_file(file_path)
        size = file_path.stat().st_size
        session = await self.client.request(
            method="POST",
            path="/api/v1/uploads/sessions",
            payload={"version_id": version_id, "path": target_path, "checksum": checksum, "size": size},
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
            if on_chunk_uploaded is not None:
                on_chunk_uploaded(len(chunk))
        await self.client.request(method="POST", path=f"/api/v1/uploads/sessions/{session['id']}/complete")
        save_to_cache(str(repository_id), checksum, file_path)

    async def upload_directory(
        self,
        *,
        repository_id: int,
        version_name: str,
        folder_path: str,
        create_version_if_missing: bool = False,
        force: bool = False,
    ) -> dict[str, Any]:
        try:
            version = await self.client.get_version(repository_id=repository_id, name=version_name)
        except ApiError as error:
            if error.http_status != 404 and error.app_status_code != 1400:
                raise
            if not create_version_if_missing:
                raise
            version = await self.client.create_version(repository_id=repository_id, name=version_name)

        if force:
            await self.client.clear_version_artifacts(version_id=str(version["id"]))

        root = Path(folder_path)
        uploaded: list[str] = []
        reused: list[str] = []
        unchanged: list[str] = []
        upload_candidates: list[tuple[Path, str]] = []
        reuse_candidates: list[tuple[str, str]] = []
        conflicts: list[str] = []

        existing_artifacts = await self.client.list_version_artifacts(
            repository_id=repository_id,
            version_name=version_name,
        )
        existing_by_path = {str(artifact["path"]): artifact for artifact in existing_artifacts}

        for file_path, relative_path in sorted(iter_files(root), key=lambda item: item[1]):
            checksum = sha256_file(file_path)
            size = file_path.stat().st_size
            existing = existing_by_path.get(relative_path)
            if existing is not None:
                if str(existing["checksum"]) == checksum and int(existing["size"]) == size:
                    unchanged.append(relative_path)
                else:
                    conflicts.append(relative_path)
                continue
            resource = await self.client.check_resource(
                version_id=str(version["id"]),
                path=relative_path,
                checksum=checksum,
                size=size,
            )
            if resource.get("status") == "exists" and resource.get("artifact_id") is not None:
                reuse_candidates.append((relative_path, str(resource["artifact_id"])))
                continue
            upload_candidates.append((file_path, relative_path))

        if conflicts:
            raise UploadPreflightError(conflicts=sorted(conflicts))

        total_uploads = len(upload_candidates)
        total_upload_bytes = sum(file_path.stat().st_size for file_path, _ in upload_candidates)
        completed_uploads = 0
        progress_context = create_upload_progress() if total_uploads > 0 else nullcontext()

        def upload_description() -> str:
            return f"Uploading version {completed_uploads}/{total_uploads} files"

        with progress_context as progress:
            upload_task_id = None
            console = progress.console if progress is not None else None
            if progress is not None:
                upload_task_id = progress.add_task(upload_description(), total=total_upload_bytes, completed=0)

            for relative_path in unchanged:
                if console is not None:
                    console.print(f"Unchanged: {relative_path}")

            for relative_path, artifact_id in reuse_candidates:
                await self.client.attach_artifact(
                    version_id=str(version["id"]),
                    artifact_id=artifact_id,
                )
                reused.append(relative_path)
                if console is not None:
                    console.print(f"Reused: {relative_path}")

            for file_path, relative_path in upload_candidates:
                def on_chunk_uploaded(delta: int) -> None:
                    if progress is not None and upload_task_id is not None:
                        progress.update(upload_task_id, advance=delta)

                await self._upload_file(
                    repository_id=repository_id,
                    version_id=str(version["id"]),
                    file_path=file_path,
                    target_path=relative_path,
                    on_chunk_uploaded=on_chunk_uploaded,
                )
                uploaded.append(relative_path)
                completed_uploads += 1
                if progress is not None and upload_task_id is not None:
                    progress.update(upload_task_id, advance=0, description=upload_description())
        return {"uploaded": uploaded, "reused": reused, "unchanged": unchanged}

    async def upload_item(
        self,
        *,
        repository_id: int,
        version_name: str,
        source_path: str,
        target_path: str,
        create_version_if_missing: bool = False,
        force: bool = False,
    ) -> dict[str, Any]:
        try:
            version = await self.client.get_version(repository_id=repository_id, name=version_name)
        except ApiError as error:
            if error.http_status != 404 and error.app_status_code != 1400:
                raise
            if not create_version_if_missing:
                raise
            version = await self.client.create_version(repository_id=repository_id, name=version_name)

        file_path = Path(source_path)
        if not file_path.is_file():
            raise FileNotFoundError(f"Upload source file not found: {source_path}")

        normalized_target_path = target_path.strip("/")
        checksum = sha256_file(file_path)
        size = file_path.stat().st_size
        if force:
            try:
                await self.client.request(
                    method="DELETE",
                    path=f"/api/v1/versions/{version['id']}/artifacts/by-path",
                    payload={"path": normalized_target_path},
                )
            except ApiError as error:
                if error.http_status != 404 and error.app_status_code != 1600:
                    raise

        existing_artifacts = await self.client.list_version_artifacts(
            repository_id=repository_id,
            version_name=version_name,
        )
        existing = next(
            (artifact for artifact in existing_artifacts if str(artifact["path"]) == normalized_target_path), None
        )
        if existing is not None and str(existing["checksum"]) == checksum and int(existing["size"]) == size:
            return {"uploaded": [], "reused": [], "unchanged": [normalized_target_path]}
        if existing is not None:
            raise UploadPreflightError(conflicts=[normalized_target_path])

        resource = await self.client.check_resource(
            version_id=str(version["id"]),
            path=normalized_target_path,
            checksum=checksum,
            size=size,
        )
        if resource.get("status") == "exists" and resource.get("artifact_id") is not None:
            await self.client.attach_artifact(version_id=str(version["id"]), artifact_id=str(resource["artifact_id"]))
            return {"uploaded": [], "reused": [normalized_target_path], "unchanged": []}

        await self._upload_file(
            repository_id=repository_id,
            version_id=str(version["id"]),
            file_path=file_path,
            target_path=normalized_target_path,
        )
        return {"uploaded": [normalized_target_path], "reused": [], "unchanged": []}

    async def download_version(
        self,
        *,
        repository_id: int,
        version_name: str,
        save_dir: str,
        force: bool = False,
    ) -> dict[str, Any]:
        artifacts = await self.client.list_version_artifacts(repository_id=repository_id, version_name=version_name)
        total_files = len(artifacts)
        total_bytes = sum(int(artifact["size"]) for artifact in artifacts)
        save_root = Path(save_dir)
        if force:
            if save_root.exists():
                if save_root.is_dir():
                    shutil.rmtree(save_root)
                else:
                    save_root.unlink()
            save_root.mkdir(parents=True, exist_ok=True)
        completed_files = 0
        downloaded: list[str] = []
        from_cache: list[str] = []
        existing: list[str] = []

        def version_description() -> str:
            return f"Downloading version {completed_files}/{total_files} files"

        with create_download_progress() as progress:
            version_task_id = progress.add_task(version_description(), total=total_bytes, completed=0)

            for artifact in artifacts:
                artifact_path = str(artifact["path"])
                checksum = str(artifact["checksum"])
                size = int(artifact["size"])
                destination = save_root / artifact_path

                def mark_completed(*, advance: int) -> None:
                    nonlocal completed_files
                    completed_files += 1
                    progress.update(version_task_id, advance=advance, description=version_description())

                if destination.exists() and destination.is_file() and destination.stat().st_size == size:
                    if sha256_file(destination) == checksum:
                        existing.append(artifact_path)
                        progress.console.print(f"Already present: {artifact_path}")
                        mark_completed(advance=size)
                        continue
                if copy_from_cache(str(repository_id), checksum, destination):
                    from_cache.append(artifact_path)
                    progress.console.print(f"Copied from cache: {artifact_path}")
                    mark_completed(advance=size)
                    continue
                download = await self.client.download_item(
                    repository_id=repository_id,
                    version_name=version_name,
                    path=artifact_path,
                    save_path=str(destination),
                )
                remote_downloaded = 0

                def on_chunk_downloaded(delta: int) -> None:
                    nonlocal remote_downloaded
                    remote_downloaded += delta
                    progress.update(version_task_id, advance=delta)

                try:
                    self.client.transport.stream_download(
                        path=str(download["download_url"]),
                        save_path=destination,
                        show_progress=True,
                        on_chunk_downloaded=on_chunk_downloaded,
                    )
                except httpx.HTTPError as error:
                    raise TransportError("Could not download the artifact", detail=str(error)) from error
                save_to_cache(str(repository_id), checksum, destination)
                downloaded.append(artifact_path)
                mark_completed(advance=max(0, size - remote_downloaded))
        return {
            "downloaded": downloaded,
            "from_cache": from_cache,
            "existing": existing,
        }
