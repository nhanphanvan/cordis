# Development

This guide is for contributors working inside the Cordis repository.

## Code Layout

- `cordis/backend/api`: route definitions, dependencies, and API composition
- `cordis/backend/services`: business logic and orchestration
- `cordis/backend/repositories`: persistence access and unit-of-work boundary
- `cordis/backend/models`: persistence models
- `cordis/backend/schemas`: request and response contracts
- `cordis/backend/storage`: storage abstraction and provider adapter
- `cordis/backend/utils`: backend logging and utility helpers
- `cordis/cli/commands`: Typer command definitions
- `cordis/cli/sdk`: backend-facing client wrapper
- `cordis/cli/config`: config and workspace-registration helpers
- `cordis/cli/transfer`: local file and cache helpers
- `cordis/backend/settings.py`: backend runtime settings
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

1. add or update schemas for request and response contracts
2. add service logic for workflow and domain rules
3. add repository methods if persistence access changes
4. add or update route handlers and dependencies
5. add tests in `tests/backend`

Keep business rules in services instead of route handlers.
Use module-level loggers for key mutation and auth workflows rather than scattering ad-hoc print-style diagnostics.

## CLI Extension Pattern

When adding CLI functionality:

1. add or update the SDK client behavior in `cordis.cli.sdk`
2. wire the user-facing command in `cordis.cli.commands`
3. use config helpers for persisted endpoint, token, or workspace state
4. use transfer helpers for local file and cache behavior when relevant
5. add tests in `tests/cli`

Keep HTTP details inside the SDK layer, not directly inside command handlers.

## Configuration and State

- backend runtime config comes from `CORDIS_` environment variables
- CLI global state lives under `~/.cordis` by default
- workspace registration lives under `<cwd>/.cordis`

Read [Configuration](./configuration.md) before changing any of these boundaries.

## Documentation Expectations

When major behavior changes:

- update the relevant guide under `docs/`
- keep `README.md` concise and link into the deeper guides
- keep the primary product documentation in the top-level `docs/` guides
