# Architecture

Cordis is split into a backend service and a CLI surface.

## High-Level Shape

- `cordis.backend`: FastAPI application, domain services, persistence, security, exception handling, storage integration, and API schemas
- `cordis.cli`: Typer command surface, SDK client, config helpers, and transfer utilities
The backend owns repository, version, tag, artifact, upload-session, runtime settings, and app-status exception contracts. The CLI turns those capabilities into local operator workflows such as login, workspace registration, uploads, downloads, and cache-aware retrieval.

## Backend Layers

### API layer

`cordis.backend.api` contains:

- route composition
- dependency wiring
- transport-level authentication entrypoints

Versioned routes are mounted under `/api/v1`.
The backend registers centralized exception handling from `cordis.backend.exceptions`, which also owns the app-status response contract and exception logging.

### Policy layer

`cordis.backend.policies` contains authorization decisions. Routes call policies explicitly so repository and admin access rules are visible at the API boundary.

### Validator layer

`cordis.backend.validators` contains request and domain validation. Validators are responsible for:

- existence checks
- uniqueness checks
- cross-entity consistency
- request normalization and lookup helpers

### Service layer

`cordis.backend.services` contains orchestration and transaction flow. Services are responsible for:

- coordinating repositories and storage operations
- mutating validated domain state
- committing, refreshing, and sequencing multi-step workflows

### Repository and unit-of-work layer

`cordis.backend.repositories` holds persistence access. The unit-of-work object provides a single boundary for transaction-scoped repository usage.

### Security

`cordis.backend.security` owns password hashing, JWT creation and verification, bearer-token authentication backends, and the authenticated `UserInfo` principal type. Backend startup initializes this package through `cordis.backend.settings.setup()`.

### Models and schemas

- `cordis.backend.models`: persistence models
- `cordis.backend.schemas.requests`: request contracts
- `cordis.backend.schemas.responses`: response contracts

This keeps storage concerns separate from HTTP payload concerns.
Model relationships follow an explicit reference-style convention: typed `Mapped[...]` relationships, explicit `back_populates`, database-aligned `passive_deletes`, and ownership cascades only on parent-owned child collections.

### Storage boundary

`cordis.backend.storage` defines the storage protocol, transfer-related types, and provider error mapping. The current implementation is S3-compatible, but the rest of the backend works against the adapter boundary rather than provider-specific calls.

### Exceptions

`cordis.backend.exceptions` defines the app-status catalog, backend exception classes, and FastAPI exception handlers. It normalizes domain errors, request validation errors, and uncaught exceptions into the same response contract.

### Utilities

`cordis.backend.utils` currently holds backend logging helpers. Logging is part of the active runtime path and is initialized during backend startup.

## CLI Layers

### Commands

`cordis.cli.commands` defines the Typer entrypoint and command groups.

### SDK

`cordis.cli.sdk` contains the backend-facing client wrapper used by the CLI. It centralizes HTTP request construction and higher-level transfer workflows.

### CLI utilities

`cordis.cli.utils` contains CLI-owned support code such as the shared HTTP transport used by the SDK.

### Config

`cordis.cli.config` owns global config, workspace registration, and cache path helpers.

### Transfer helpers

`cordis.cli.transfer` handles local file iteration, checksums, cache reuse, and download-to-disk helpers.

## Request Flow

Typical backend flow:

1. A route handler receives a request under `/api/v1`.
2. Dependencies resolve the current user and unit of work.
3. The route calls a policy for authorization.
4. The route calls validator helpers to resolve and validate domain state.
5. A service coordinates repositories or storage and performs the mutation.
6. Repository calls load or persist state through the unit of work.
7. The route returns a response schema.

## Resource Transfer Flow

Typical upload flow:

1. A CLI resource command calls the SDK client.
2. The SDK resolves repository and version context.
3. The backend creates or resumes an upload session.
4. Upload parts are recorded and finalized through the storage adapter.
5. Artifact metadata with a required storage object version ID is attached to the target version.
6. The CLI stores reusable file content in the local cache.

Typical download flow:

1. The CLI lists version artifacts.
2. Cached content is reused when possible.
3. Missing content is resolved through a backend download endpoint.
4. The backend returns a mediated download URL.
5. The CLI writes the file locally and stores it in cache.
