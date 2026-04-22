# Architecture

Cordis is split into a backend service and a CLI surface.

## High-Level Shape

- `cordis.backend`: FastAPI application, domain services, persistence, security, exception handling, storage integration, and API schemas
- `cordis.cli`: Typer command surface, config helpers, and transfer utilities
- `cordis.sdk`: public Python SDK client, transport, API modules, and reusable transfer orchestration
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

`cordis.backend.app` owns the FastAPI application lifespan. Runtime bootstrap, including default role seeding and optional first-admin creation, now runs there so database access stays on the same async event loop as request handling.

### Models and schemas

- `cordis.backend.models`: persistence models
- `cordis.backend.schemas.requests`: request contracts
- `cordis.backend.schemas.responses`: response contracts

This keeps storage concerns separate from HTTP payload concerns.
Model relationships follow an explicit reference-style convention: typed `Mapped[...]` relationships, explicit `back_populates`, database-aligned `passive_deletes`, and ownership cascades only on parent-owned child collections.

### Storage boundary

`cordis.backend.storage` defines the storage protocol, transfer-related types, provider bootstrapping, provider error mapping, and repository-scoped public-object access helpers. The current concrete implementations are MinIO and real AWS S3, with the rest of the backend still working against the shared adapter boundary rather than provider-specific calls.
Cordis uses a shared storage bucket and structured object keys. When a repository enables `allow_public_object_urls`, the repository service asks the storage adapter to sync public read access only for that repository's key prefix rather than switching the whole bucket between public and private modes.

### Exceptions

`cordis.backend.exceptions` defines the app-status catalog, backend exception classes, and FastAPI exception handlers. It normalizes domain errors, request validation errors, and uncaught exceptions into the same response contract.

### Utilities

`cordis.backend.utils` currently holds backend logging helpers. Logging is part of the active runtime path and is initialized during backend startup.

## CLI Layers

### Commands

`cordis.cli.commands` defines the Typer entrypoint and command groups. Commands collect user input, call the SDK, and route expected failures through the shared CLI error handler.

### Presentation and errors

`cordis.cli.utils.presentation` owns Rich-rendered tables, detail views, success panels, and error panels. `cordis.cli.errors` defines the typed CLI exception surface used to normalize config, transport, and backend API failures before they reach the terminal.

### SDK

`cordis.sdk` contains the backend-facing client used both by Python consumers and by the CLI. It centralizes HTTP request construction, backend error normalization, and higher-level transfer workflows.

### Config

`cordis.cli.utils.files` owns global config, workspace registration, cache path helpers, and CLI-local file helpers. CLI-specific client construction from local config also stays on the CLI side rather than in the public SDK package.

### Transfer helpers

`cordis.cli.utils.files` handles local file iteration, multipart upload chunking, checksums, cache reuse, and other local transfer helpers. Remote HTTP download streaming lives in the shared SDK HTTP transport layer rather than here.

## Request Flow

Typical backend flow:

1. A route handler receives a request under `/api/v1`.
2. Dependencies resolve the current user and unit of work.
3. The route calls a policy for authorization.
4. The route calls validator helpers to resolve and validate domain state.
5. A service coordinates repositories or storage and performs the mutation.
6. Repository calls load or persist state through the unit of work.
7. The route returns a response schema.

For repository create and update mutations, the service layer also synchronizes prefix-scoped storage public access when `allow_public_object_urls` changes.

## Resource Transfer Flow

Typical upload flow:

1. A CLI resource command calls the SDK client.
2. The SDK resolves repository and version context.
3. The CLI preflights the full folder against the target version before any mutation.
4. Same-version exact matches are classified as unchanged, same-version path conflicts abort the whole upload, and reusable repository artifacts from other versions are staged for attach.
5. If preflight succeeds, reusable artifacts are attached directly to the target version and only the remaining files enter upload-session handling.
6. The CLI uploads missing file parts sequentially and can resume by skipping already-recorded parts.
7. Upload parts are recorded and finalized through the storage adapter.
8. Artifact metadata backed by one immutable storage object is attached to the target version.
9. The CLI stores reusable file content in the local cache.

Read [Transfer Workflows](./transfer-workflows.md) for the full upload sequence, including validation and upload-session lifecycle details.

Typical download flow:

1. The CLI lists version artifacts.
2. If `--force` is set, the CLI wipes the destination root first.
3. Existing destination files that already match the artifact checksum are treated as satisfied and skipped.
4. Cached content is reused when possible for the remaining artifacts.
5. Missing content is resolved through a backend download endpoint.
6. The backend returns a mediated download URL.
7. The CLI streams the file locally through the shared HTTP transport with retry, resume, and progress support.
8. The CLI stores the completed file in cache.

Read [Transfer Workflows](./transfer-workflows.md) for the full download sequence and the distinction between cache hits, mediated download URLs, and streamed remote transfers.
