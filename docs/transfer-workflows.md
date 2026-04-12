# Transfer Workflows

This guide is the detailed reference for Cordis upload and download behavior across the CLI, backend API, storage adapter, and local cache.

It documents the current implementation, not a future design.

## Why This Exists

Cordis splits transfer behavior across clear boundaries:

- the CLI owns local file discovery, workspace context, cache reuse, terminal presentation, and streamed remote download behavior
- the backend owns authorization, validation, upload-session state, artifact metadata, version attachment, mediated download URLs, and storage integration
- the storage adapter owns multipart upload and presigned-download primitives against MinIO or AWS S3

That split is why the transfer flow is more than a single HTTP request.

## Main Components

### CLI side

- `cordis.cli.commands.resource`
  Runs the operator-facing `resource upload`, `resource download`, and `resource download-item` commands.
- `cordis.cli.sdk.transfers.TransferHelper`
  Orchestrates upload and download workflows after command input has been resolved.
- `cordis.cli.transfer.files`
  Handles local file iteration, `.cordisignore` filtering, multipart chunk iteration, checksums, and cache path management.
- `cordis.cli.transfer.constants`
  Defines shared transfer constants such as the canonical `8 MiB` chunk size used by both upload and download paths.
- `cordis.cli.utils.httpx_service.HttpxService`
  Owns remote HTTP transport, including streamed artifact downloads with retry, resume, and Rich progress.

### Backend side

- `cordis.backend.api.v1.uploads`
  Exposes upload-session lifecycle routes.
- `cordis.backend.api.v1.versions`
  Exposes artifact listing, artifact lookup by path, and mediated download URL creation.
- `cordis.backend.validators.upload`
  Validates upload request shape, version existence, path normalization, duplicate-path rules, and completion preconditions.
- `cordis.backend.services.upload.UploadService`
  Creates or resumes upload sessions, records parts, completes multipart uploads, attaches artifact metadata, and handles aborts.
- `cordis.backend.services.download.DownloadService`
  Produces the mediated download URL for an artifact.

### Persisted entities involved

- `Version`
  The repository-scoped version that upload and download workflows target.
- `Artifact`
  Metadata about stored content. Persisted artifacts always require `storage_version_id`.
- `VersionArtifact`
  The association that makes an artifact part of a specific version.
- `UploadSession`
  Tracks in-progress, finalizing, completed, failed, or aborted upload lifecycle state.
- `UploadSessionPart`
  Tracks uploaded multipart pieces for resumable upload completion.

## Upload Workflow

Cordis upload is session-based and uses real multipart behavior from the CLI side. Files are chunked locally, uploaded sequentially, and resumed by reusing the backend's persisted uploaded-part state.

### Operator entrypoint

The main operator command is:

```bash
cordis resource upload --path <folder> [--create-version] [--repo-id <id>] [--version <name>]
```

The command resolves repository and version context first:

- `--repo-id` and `--version` can be provided explicitly
- otherwise the CLI reads `<cwd>/.cordis/config.json`
- if `--create-version` is enabled and the target version lookup fails with backend app status `1400`, the CLI creates the version and continues

### Local file discovery

The CLI walks the upload root with `iter_files(root)` and only yields upload candidates that survive ignore filtering.

Upload filtering rules:

- `.cordisignore` is the only ignore file consulted
- matching uses Gitignore-style rules through `pathspec`
- `.cordis/` is always excluded
- `.cordisignore` itself is always excluded
- yielded paths are stored as relative POSIX-style paths such as `models/file.bin`

For each yielded file, the CLI computes:

- `checksum`
  A SHA-256 digest in the form `sha256:<hex>`
- `size`
  The byte length from the local file system
- `path`
  The relative artifact path inside the version

Before creating an upload session, the CLI now performs a reuse check against the backend for the target version and file metadata. If the backend finds an existing repository artifact at the same path with the same checksum and size, the CLI attaches that artifact to the target version directly and skips multipart upload entirely.

### Upload request sequence

For each file, the CLI executes this sequence:

1. `POST /api/v1/resources/check`
   The payload includes:
   - `version_id`
   - `path`
   - `checksum`
   - `size`
2. if the backend returns an existing matching artifact ID, `POST /api/v1/versions/{version_id}/artifacts` and skip upload
3. otherwise `POST /api/v1/uploads/sessions`
4. inspect the returned session's `parts` list and build the set of already-uploaded `part_number` values
5. read the local file in `8 MiB` chunks
6. `POST /api/v1/uploads/sessions/{session_id}/parts` once per missing chunk
7. `POST /api/v1/uploads/sessions/{session_id}/complete`
8. on successful multipart upload, store the local file in the cache under the repository/checksum key

Each part request still uses `content_base64`, but only for the current chunk rather than the entire file.

### Backend validation at session creation

When the backend receives `POST /uploads/sessions`, it validates:

- the version exists
- `size` is non-negative
- the provided path is not empty after trimming `/`
- the path resolves to a file name, not just a directory-like prefix
- the target version does not already contain a path collision

Version path collision rules are important:

- if the target version already has the same path with the same checksum and size, creation fails with an artifact-already-exists conflict
- if the target version already has the same path with different metadata, creation fails with a metadata-conflict error

After validation, the route checks repository access and requires upload mutation permission through `UploadPolicy.mutate`.

### Session creation vs resume

`UploadService.create_or_resume_session(...)` does not blindly create a new row.

It first asks the upload-session repository for a resumable session matching:

- `version_id`
- normalized `path`
- `checksum`
- `size`

If a matching resumable session exists:

- the backend returns the existing session
- the HTTP status becomes `200 OK`
- previously recorded parts are returned

The CLI uses those returned parts directly. A resumed upload skips part numbers already present in the session and only uploads the missing chunks.

If no matching session exists:

- a new `upload_sessions` row is created with status `created`
- the storage adapter creates a multipart upload and returns `upload_id`
- the new session is committed and returned with `201 Created`

### Part upload behavior

`POST /uploads/sessions/{session_id}/parts` accepts either:

- `content_base64`
- `content`

The current CLI sends `content_base64` per chunk.

On the backend:

- the session must exist
- the caller must still have upload mutation permission
- the session must not already be terminal
- the storage adapter uploads the part
- the backend upserts the `(session_id, part_number)` record in `upload_session_parts`
- the session status becomes `in_progress`

The response returns the updated session plus the current list of uploaded parts.

On the CLI side, parts are uploaded sequentially in ascending `part_number` order. This first-pass design intentionally does not use parallel part upload. The value is correctness and resumability with lower complexity:

- interrupted uploads can continue from the last persisted part set
- large files are no longer read fully into memory before upload
- the client and backend stay aligned on one source of truth for uploaded part state

### Completion behavior

Completion uses `POST /uploads/sessions/{session_id}/complete`.

Before finalization, the backend verifies:

- the session exists
- the caller is authorized
- the session is not terminal
- the session has at least one uploaded part

`UploadService.complete_session(...)` then:

1. marks the session as `finalizing`
2. asks the storage adapter to complete the multipart upload using the recorded parts
3. validates the completed object checksum against the expected session checksum
4. requires the storage adapter to return a real `version_id`
5. resolves or creates the repository-scoped artifact
6. attaches the artifact to the target version
7. stores the artifact ID back on the session
8. marks the session `completed`

### Artifact resolution during completion

Completion can reuse an existing repository artifact, but only under strict rules.

The backend checks whether the repository already has an artifact at the same normalized path:

- if the existing artifact has the same checksum and size, it can be reused
- if it has the same path but different metadata, completion fails with a checksum conflict
- if no repository artifact exists, a new artifact row is created

When a new artifact is created, it persists:

- `repository_id`
- `path`
- `name`
- `checksum`
- `size`
- `storage_version_id`

That `storage_version_id` is mandatory. Cordis treats it as durable lineage to the exact stored object version behind the artifact.

### Pre-upload repository reuse

The backend now supports a cheaper path for unchanged files across versions.

If the target version does not already contain the path, the reuse check looks for an existing repository artifact at the same normalized path:

- if checksum and size also match, the CLI can attach that artifact to the target version and skip storage upload
- if no repository artifact exists, the file proceeds through normal upload-session handling
- if a repository artifact exists at the same path with different metadata, the file still proceeds to normal upload handling, which preserves the current repository-path conflict behavior

### Upload failure paths

Important upload failure cases include:

- version not found
- invalid path
- negative size
- duplicate artifact already present in the version
- session already terminal
- session has no parts at completion time
- multipart state invalid in storage
- completed checksum mismatch
- missing storage `version_id` from the storage adapter

Failure effects vary by stage:

- validation failures are returned immediately as handled backend errors
- multipart-state, checksum, and storage-version failures mark the session `failed` and record an `error_message`
- abort explicitly marks the session `aborted`

If the CLI fails mid-upload, the backend session remains the resumable source of truth. A later `resource upload` run for the same version, path, checksum, and size will reuse that session and skip already-recorded parts.

### Abort behavior

`POST /uploads/sessions/{session_id}/abort` asks the storage adapter to abort the multipart upload and then marks the session aborted.

Special cases:

- aborting an already aborted session is idempotent and returns the current session
- aborting a completed session is a conflict because the session is already terminal

## Download Workflow

Cordis download is version-oriented and cache-aware. The CLI tries to avoid remote network transfer when a matching local cached object already exists.

### Operator entrypoints

There are two different operator flows:

1. `cordis resource download`
   Downloads every artifact in a version to a local folder.
2. `cordis resource download-item`
   Resolves a single artifact download URL and prints it. It does not currently stream the file to disk.

The deeper end-to-end workflow described below applies to `cordis resource download`.

### Version download sequence

For `cordis resource download --path <folder> ...`, the CLI does this:

1. resolve repository and version from flags or workspace config
2. call `list_version_artifacts(...)`
3. for each returned artifact:
   - compute the target destination under the requested folder
   - attempt cache reuse by `(repository_id, checksum)`
   - if cached, copy the file locally and continue
   - if not cached, request a mediated download URL from the backend
   - stream the remote object to disk through `HttpxService.stream_download(...)`
   - save the completed local file back into the cache
4. return the list of downloaded relative paths

### Artifact listing

The CLI begins with:

- `GET /versions/{version_id}/artifacts`

That requires successful version resolution and download authorization. The response includes artifact metadata such as:

- `id`
- `path`
- `checksum`
- `size`
- `storage_version_id`

The CLI uses:

- `path` to determine local destination
- `checksum` to look up the local cache

### Cache behavior

Cache reuse happens before any remote download request.

The cache key is derived from:

- repository ID
- artifact checksum

If a cached object exists:

- the CLI copies it into the destination path
- no mediated download URL is requested
- no progress bar is shown

If the cache misses:

- the CLI falls through to the remote download flow

### Mediated download URL creation

For a cache miss, the CLI calls `download_item(...)`, which resolves:

- the version
- the artifact by path
- `POST /versions/{version_id}/artifacts/{artifact_id}/download`

The backend:

- validates version existence
- validates repository access for the current user based on repository `visibility` and membership
- validates that the artifact belongs to the requested version
- asks `DownloadService` to build a presigned or mediated storage URL

The response returns:

- `artifact_id`
- `download_url`
- `expires_in`

The CLI then streams from `download_url`.

### Remote streaming behavior

Remote download streaming is owned by `cordis.cli.utils.httpx_service.HttpxService`.

That transport is responsible for:

- issuing the `GET` request to the mediated URL
- writing the file in chunks
- retrying transient HTTP failures
- resuming interrupted streams with `Range` when a partial file already exists
- restarting cleanly if the server ignores the resume request and returns `200 OK`
- showing Rich progress during active remote download

This is intentionally not handled in `cordis.cli.transfer.files`. The transfer layer owns local behaviors like file discovery and cache paths, while the transport layer owns remote HTTP streaming.

### Resume behavior

If a streamed download is interrupted by a remote protocol failure:

- the partial destination file is left on disk
- the transport measures its current size
- the next request sends `Range: bytes=<downloaded>-`
- the response is appended in `ab` mode if the server honors resume with `206 Partial Content`

If a server ignores the range request and returns a full-body `200 OK`:

- the partial file is deleted
- the stream restarts from scratch
- the final file is rewritten cleanly instead of being corrupted by an append

### Progress behavior

Remote downloads show Rich progress output.

Progress is displayed only for remote streaming, not for:

- cache hits
- local cache copies

If the server exposes enough size metadata, progress tracks total size and speed. If total size is incomplete or unknown, the progress rendering still stays inside the shared Rich-based CLI presentation model.

### Download failure paths

Important download failures include:

- missing workspace repository or version registration in the CLI
- version not found
- artifact not found in the target version
- missing or invalid bearer token when required
- repository access denied
- transport failures while streaming the mediated URL

Failure surfacing is layered:

- CLI config issues become typed `ConfigurationError`
- backend failures become typed `ApiError`
- remote stream failures become typed `TransportError`

The command layer renders those through the shared CLI error panel path.

## `download-item` Workflow

`cordis resource download-item` is related to download behavior, but it is not the same workflow as `resource download`.

Current behavior:

- the CLI resolves repository and version context
- it asks the backend for the artifact-specific mediated download URL
- it prints the URL in a detail view

It does not currently:

- download the file
- reuse the local cache
- call the streamed download transport
- write anything to `--save-path`

The backend response still includes the URL and expiry metadata, so this command is effectively a URL-resolution helper at the moment.

## End-to-End Sequence Summaries

### Upload sequence

1. Operator runs `cordis resource upload`.
2. CLI resolves repository/version context.
3. CLI walks the local folder with `.cordisignore` filtering.
4. CLI computes checksum and size for each file.
5. Backend validates the upload request and creates or resumes an upload session.
6. CLI uploads part content to the session.
7. Backend records uploaded parts and finalizes multipart state.
8. Backend validates checksum and storage version metadata.
9. Backend creates or reuses the repository artifact and attaches it to the version.
10. CLI saves the local file into the cache.

### Download sequence

1. Operator runs `cordis resource download`.
2. CLI lists version artifacts.
3. CLI checks the local cache for each checksum.
4. Cache hits are copied locally and finish immediately.
5. Cache misses ask the backend for mediated download URLs.
6. CLI streams remote content through the shared HTTP transport.
7. Transport retries or resumes if the remote stream is interrupted.
8. CLI stores the finished file in the cache.

## Operational Invariants

The following rules are important to preserve when changing transfer code:

- `.cordisignore` is the only upload ignore file in the current design
- upload-session state is the backend source of truth for multipart ingest
- completed artifacts require `storage_version_id`
- version download is cache-aware and checksum-based
- remote artifact downloads stream through `HttpxService`, not ad-hoc network helpers in the transfer layer
- the CLI should keep human-friendly output and typed error behavior around transfer failures
- the backend storage adapter must preserve provider object version IDs so completed artifacts keep durable storage lineage

## Related Guides

- [CLI Guide](./cli.md)
- [Backend API](./backend-api.md)
- [Architecture](./architecture.md)
- [Configuration](./configuration.md)
- [Data Model](./data-model.md)
