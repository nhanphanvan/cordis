# Architecture

Cordis is split into a backend service and a CLI surface.

## High-Level Shape

- `cordis.backend`: FastAPI application, domain services, persistence, storage integration, and API schemas
- `cordis.cli`: Typer command surface, SDK client, config helpers, and transfer utilities
- `cordis.shared`: cross-cutting settings and small shared contracts

The backend owns repository, version, tag, artifact, and upload-session state. The CLI turns those capabilities into local operator workflows such as login, workspace registration, uploads, downloads, and cache-aware retrieval.

## Backend Layers

### API layer

`cordis.backend.api` contains:

- route composition
- dependency wiring
- authentication and authorization entrypoints
- exception mapping

Versioned routes are mounted under `/api/v1`.

### Service layer

`cordis.backend.services` contains business logic and orchestration. Services are responsible for:

- validating workflow-level behavior
- enforcing domain rules
- coordinating repositories and storage operations

### Repository and unit-of-work layer

`cordis.backend.repositories` holds persistence access. The unit-of-work object provides a single boundary for transaction-scoped repository usage.

### Models and schemas

- `cordis.backend.models`: persistence models
- `cordis.backend.schemas`: request and response contracts

This keeps storage concerns separate from HTTP payload concerns.

### Storage boundary

`cordis.backend.storage` defines the storage protocol, transfer-related types, and provider error mapping. The current implementation is S3-compatible, but the rest of the backend works against the adapter boundary rather than provider-specific calls.

## CLI Layers

### Commands

`cordis.cli.commands` defines the Typer entrypoint and command groups.

### SDK

`cordis.cli.sdk` contains the backend-facing client wrapper used by the CLI. It centralizes HTTP request construction and higher-level transfer workflows.

### Config

`cordis.cli.config` owns global config, workspace registration, and cache path helpers.

### Transfer helpers

`cordis.cli.transfer` handles local file iteration, checksums, cache reuse, and download-to-disk helpers.

## Request Flow

Typical backend flow:

1. A route handler receives a request under `/api/v1`.
2. Dependencies resolve the current user, authorization context, and unit of work.
3. A service applies business rules and coordinates repositories or storage.
4. Repository calls load or persist state through the unit of work.
5. The route returns a response schema.

## Resource Transfer Flow

Typical upload flow:

1. A CLI resource command calls the SDK client.
2. The SDK resolves repository and version context.
3. The backend creates or resumes an upload session.
4. Upload parts are recorded and finalized through the storage adapter.
5. Artifact metadata is attached to the target version.
6. The CLI stores reusable file content in the local cache.

Typical download flow:

1. The CLI lists version artifacts.
2. Cached content is reused when possible.
3. Missing content is resolved through a backend download endpoint.
4. The backend returns a mediated download URL.
5. The CLI writes the file locally and stores it in cache.
