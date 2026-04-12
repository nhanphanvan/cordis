from abc import ABC, abstractmethod

from cordis.backend.storage.types import (
    CompletedMultipartUpload,
    ObjectMetadata,
    StorageObjectRef,
    UploadedPart,
)


class StorageAdapter(ABC):
    @abstractmethod
    def stat_object(self, ref: StorageObjectRef) -> ObjectMetadata:
        raise NotImplementedError

    @abstractmethod
    def put_object(self, ref: StorageObjectRef, *, body: bytes, checksum: str | None = None) -> str:
        raise NotImplementedError

    @abstractmethod
    def delete_object(self, ref: StorageObjectRef) -> None:
        raise NotImplementedError

    @abstractmethod
    def get_download_url(self, ref: StorageObjectRef, *, expires_in: int) -> str:
        raise NotImplementedError

    @abstractmethod
    def get_public_url(self, ref: StorageObjectRef, *, storage_version_id: str) -> str:
        raise NotImplementedError

    @abstractmethod
    def ensure_repository_public_access(self, *, repository_id: int) -> bool:
        raise NotImplementedError

    @abstractmethod
    def disable_repository_public_access(self, *, repository_id: int) -> bool:
        raise NotImplementedError

    @abstractmethod
    def create_multipart_upload(self, ref: StorageObjectRef) -> str:
        raise NotImplementedError

    @abstractmethod
    def upload_part(
        self,
        ref: StorageObjectRef,
        *,
        upload_id: str,
        part_number: int,
        body: bytes,
    ) -> UploadedPart:
        raise NotImplementedError

    @abstractmethod
    def complete_multipart_upload(
        self,
        ref: StorageObjectRef,
        *,
        upload_id: str,
        parts: list[UploadedPart],
    ) -> CompletedMultipartUpload:
        raise NotImplementedError

    @abstractmethod
    def abort_multipart_upload(self, ref: StorageObjectRef, *, upload_id: str) -> None:
        raise NotImplementedError
