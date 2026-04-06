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
- `GET /versions/{version_id}/artifacts`
- `GET /versions/{version_id}/artifacts/by-path?path=<path>`

Resource existence checks are exposed through:

- `POST /resources/check`

This allows the backend to answer whether a proposed file already matches content registered in a version.

Artifact creation requires `storage_version_id`. Cordis treats that as the durable reference to the exact stored object version behind the artifact metadata.

## Upload Sessions

Cordis uses session-based upload flows for resource ingestion.

Core routes:

- `POST /uploads/sessions`
- `GET /uploads/sessions/{session_id}`
- `POST /uploads/sessions/{session_id}/parts`
- `POST /uploads/sessions/{session_id}/complete`
- `POST /uploads/sessions/{session_id}/abort`

Upload sessions track the target version, path, checksum, size, upload state, and uploaded parts. Finalization creates or resolves artifact metadata and associates it to the target version. Completion also requires the storage backend to return a real object version ID; if that metadata is missing, finalization fails and the session is marked failed.

## Download and Retrieval

Download workflows are version-oriented.

Core routes:

- `GET /versions/{version_id}/artifacts`
- `GET /versions/{version_id}/artifacts/by-path?path=<path>`
- `POST /versions/{version_id}/artifacts/{artifact_id}/download`

The backend returns a mediated download URL plus expiry metadata, so the client does not need direct knowledge of storage-provider internals.

## Users and Roles

Current user and admin surfaces include:

- `/users`
- `/admin/users`
- `/roles`
- `/admin/roles`

These routes support self-service inspection plus admin-facing user and role management workflows.

## Error and Access Behavior

In broad terms:

- unauthenticated requests fail on protected routes
- unauthorized requests fail when the current user lacks the required repository or admin access
- repository visibility and membership determine viewer/developer/owner behavior
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
