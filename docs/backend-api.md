# Backend API

Cordis exposes a versioned HTTP API under `/api/v1`.

This guide is intentionally workflow-oriented. It covers the current route groups and the main request patterns without duplicating the entire schema layer as a static reference.

## Health and App Composition

Useful health endpoints:

- `GET /healthz`
- `GET /api/v1/healthz`

The FastAPI application mounts common routes plus the versioned API router.

## Authentication

Auth routes live under `/api/v1/auth`.

Current flows:

- `POST /auth/login`
- `GET /auth/me`
- `GET /auth/admin-check`

Typical login request:

```json
{
  "email": "user@example.com",
  "password": "password123"
}
```

Login returns a bearer token. Protected routes expect that token in the `Authorization` header.

## Repositories and Membership

Repository routes are the main authorization boundary.

Core routes:

- `POST /repositories`
- `GET /repositories`
- `GET /repositories/{repository_id}`
- `PATCH /repositories/{repository_id}`
- `DELETE /repositories/{repository_id}`
- `GET /repositories/{repository_id}/members`
- `POST /repositories/{repository_id}/members`
- `PATCH /repositories/{repository_id}/members/{user_id}`
- `DELETE /repositories/{repository_id}/members/{user_id}`
- `GET /repositories/{repository_id}/versions`
- `GET /repositories/{repository_id}/tags`

Authorization model:

- viewers can read repository-scoped content
- developers can create versions and write version content
- owners and admins can manage membership and repository policy

## Versions

Version routes group artifacts within a repository.

Core routes:

- `POST /versions`
- `GET /versions/{version_id}`
- `GET /versions?repository_id=<id>&name=<name>`
- `DELETE /versions/{version_id}`

Version lookup by repository and name is the main resolution pattern used by the CLI.

## Tags

Tags bind stable names to repository-scoped versions.

Core routes:

- `POST /tags`
- `GET /tags/{tag_id}`
- `GET /tags?repository_id=<id>&name=<name>`
- `DELETE /tags/{tag_id}`

Repository tag listing is available through `GET /repositories/{repository_id}/tags`.

## Artifacts and Version Contents

Artifacts represent content metadata and version attachment state.

Core routes:

- `POST /artifacts`
- `GET /artifacts/{artifact_id}`
- `POST /versions/{version_id}/artifacts`
- `DELETE /versions/{version_id}/artifacts`
- `DELETE /versions/{version_id}/artifacts/by-path`
- `GET /versions/{version_id}/artifacts`
- `GET /versions/{version_id}/artifacts/by-path?path=<path>`

Resource existence checks are exposed through:

- `POST /resources/check`

This allows the backend to answer whether a proposed file already matches content registered in the target version, or whether an existing repository artifact at the same path can be reused for the target version without uploading again.
`DELETE /versions/{version_id}/artifacts` clears the target version contents by deleting only version-to-artifact associations. It does not delete artifact records themselves and is used by `resource upload --force`.
`DELETE /versions/{version_id}/artifacts/by-path` clears only one version-to-artifact association for the provided path. It is used by `resource upload-item --force` and also leaves shared artifact records intact.

Artifact creation does not require storage-provider version metadata. Cordis treats the artifact record and its immutable storage key as the durable reference to the stored object behind the artifact metadata.

## Upload Sessions

Cordis uses session-based upload flows for resource ingestion.

Core routes:

- `POST /uploads/sessions`
- `GET /uploads/sessions/{session_id}`
- `POST /uploads/sessions/{session_id}/parts`
- `POST /uploads/sessions/{session_id}/complete`
- `POST /uploads/sessions/{session_id}/abort`

Upload sessions track the target version, path, checksum, size, upload state, and uploaded parts. Finalization creates or resolves artifact metadata and associates it to the target version. Completion does not depend on storage-provider object version metadata; immutable object keys are the durable storage identity.

Before creating an upload session, the CLI may call `POST /resources/check` and, when the backend finds a repository-scoped artifact at the same path with identical checksum and size, attach that artifact directly to the target version through `POST /versions/{version_id}/artifacts` instead of uploading the file again. When the operator uses `resource upload --force`, the CLI first calls `DELETE /versions/{version_id}/artifacts` so upload starts from an empty version. When the operator uses `resource upload-item --force`, the CLI first calls `DELETE /versions/{version_id}/artifacts/by-path` so only the requested path is replaced.

Read [Transfer Workflows](./transfer-workflows.md) for the detailed upload sequence from CLI file discovery through backend session completion.

## Download and Retrieval

Download workflows are version-oriented.

Core routes:

- `GET /versions/{version_id}/artifacts`
- `GET /versions/{version_id}/artifacts/by-path?path=<path>`
- `POST /versions/{version_id}/artifacts/{artifact_id}/download`

The backend returns a mediated download URL plus expiry metadata, so the client does not need direct knowledge of storage-provider internals. The CLI only requests that URL when neither the destination file nor the local cache already satisfies the artifact.

Read [Transfer Workflows](./transfer-workflows.md) for the detailed download sequence, including cache reuse, mediated download URL creation, and CLI-side streamed download behavior.

## Users and Roles

Current user and role surfaces include:

- `/users`
- `/roles`

These routes support self-service inspection plus admin-gated user and role management workflows on shared resource paths.

## Error and Access Behavior

In broad terms:

- unauthenticated requests fail on protected routes
- unauthorized requests fail when the current user lacks the required repository or admin access
- repository `visibility=private` requires membership for reads, while `visibility=authenticated` allows any logged-in user to read
- `allow_public_object_urls=true` exposes provider-native raw object URLs for artifact fetches, but it does not relax Cordis API write rules
- write operations use stronger access requirements than read operations

Handled backend errors use a top-level app-status payload:

```json
{
  "status_code": 404,
  "app_status_code": 1100,
  "message": "Repository not found",
  "detail": "Repository not found"
}
```

`message` comes from the backend app-status catalog. `detail` carries the context-specific exception detail or validation payload.

For implementation details, read the route dependencies and service layer together with [Architecture](./architecture.md).
