# Development

This guide is for contributors working inside the Cordis repository.

## Code Layout

- `cordis/backend/api`: route definitions, dependencies, and API composition
- `cordis/backend/policies`: authorization rules and route-level access decisions
- `cordis/backend/validators`: request and domain validation helpers
- `cordis/backend/services`: business logic and orchestration
- `cordis/backend/repositories`: persistence access and unit-of-work boundary
- `cordis/backend/models`: persistence models
- `cordis/backend/security`: password hashing, JWT handling, bearer authentication, and authenticated principal types
- `cordis/backend/schemas/requests`: request contracts
- `cordis/backend/schemas/responses`: response contracts
- `cordis/backend/storage`: storage abstraction and provider adapter
- `cordis/backend/utils`: backend logging and utility helpers
- `cordis/cli/commands`: Typer command definitions
- `cordis/cli/errors.py`: typed CLI exception surface for config, API, and transport failures
- `cordis/cli/presentation.py`: Rich-based output helpers for tables, detail views, and status panels
- `cordis/cli/sdk`: backend-facing client wrapper
- `cordis/cli/utils/httpx_service.py`: shared CLI HTTP transport, including streamed artifact downloads with retry and resume
- `cordis/cli/config`: config and workspace-registration helpers
- `cordis/cli/transfer`: local file and cache helpers
- `cordis/cli/transfer/files.py`: upload file discovery, `.cordisignore` matching, multipart chunk iteration, checksums, and cache file paths
- `cordis/cli/transfer/constants.py`: shared transfer constants such as the canonical `8 MiB` chunk size
- `cordis/backend/settings.py`: backend startup wiring for logging and security
- `cordis/backend/exceptions/`: app status catalog, backend exception types, and centralized exception handlers

## Quality Gates

Use the standard Make targets:

```bash
make lint
make test
```

Additional useful targets:

```bash
make format
make typecheck
```

## Backend Extension Pattern

When adding backend functionality:

1. add or update schemas under `cordis/backend/schemas/requests` and `cordis/backend/schemas/responses`
2. add or update policies for authorization
3. add or update validators for request and domain checks
4. add service logic for orchestration and transaction flow
5. add repository methods if persistence access changes
6. add or update route handlers and dependencies
7. add tests in `tests/backend`

Keep route modules explicit about policy and validator calls.
Keep business validation out of services.
Use module-level loggers for key mutation and auth workflows rather than scattering ad-hoc print-style diagnostics.

## CLI Extension Pattern

When adding CLI functionality:

1. add or update the SDK client behavior in `cordis.cli.sdk`
2. add or update typed CLI errors if the feature introduces a new expected failure mode
3. wire the user-facing command in `cordis.cli.commands`
4. render human-facing output through the shared presentation helpers
5. use config helpers for persisted endpoint, token, or workspace state
6. use transfer helpers for local file and cache behavior when relevant
7. add tests in `tests/cli`

Keep HTTP details inside the SDK layer, not directly inside command handlers.
Keep expected failure rendering centralized through the shared CLI error path rather than duplicating command-local `try/except` formatting.
Keep upload ignore semantics in the transfer layer and treat `.cordisignore` as the only upload ignore file in the current design.
Keep pre-upload artifact reuse checks in the SDK/transfer workflow rather than duplicating repository/path reuse logic in command handlers.
Keep CLI uploads sequential and resumable against backend upload sessions rather than collapsing files into one synthetic part.
Keep remote artifact download streaming in `cordis.cli.utils.httpx_service` rather than reintroducing raw network helpers under `cordis.cli.transfer`.

## Configuration and State

- backend runtime config comes from `CORDIS_` environment variables
- CLI global state lives under `~/.cordis` by default
- workspace registration lives under `<cwd>/.cordis`
- Docker/Compose runtime uses the same `CORDIS_*` env surface through `.env.docker.example`
- Alembic is present in the repository, but migration execution should currently be treated as manual/operator-managed in the container workflow

Read [Configuration](./configuration.md) before changing any of these boundaries.

## Documentation Expectations

When major behavior changes:

- update the relevant guide under `docs/`
- keep `README.md` concise and link into the deeper guides
- keep the primary product documentation in the top-level `docs/` guides
