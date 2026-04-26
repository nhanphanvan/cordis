# Repository Guidelines

## Project Structure & Module Organization

Application code lives under `cordis/`. Use `cordis/backend/` for the FastAPI service and backend-owned runtime concerns such as config, exception handling, storage integration, and migration helpers, `cordis/cli/` for the Typer CLI and CLI-owned local behavior, and `cordis/sdk/` for the public Python SDK and shared transport. Keep modules focused and colocate related behavior. Tests live under `tests/`, split into `tests/backend/` and `tests/cli/`. Root files such as `pyproject.toml`, `Makefile`, `README.md`, and `alembic.ini` define tooling and local workflow, while Docker assets live under `dockers/`.

## Build, Test, and Development Commands

- `make install`: install Poetry-managed dependencies for development and tests.
- `make lint`: run `poetry check`, Ruff, Pylint, and MyPy.
- `make fix`: run Ruff autofixes, then Black on `tests/` and `cordis/`.
- `make format`: format the repository with Ruff.
- `make typecheck`: run MyPy only.
- `make test`: run the full pytest suite.
- `make build`: build the CLI/SDK-focused source distribution and wheel.
- `make run-backend`: start the backend with `python -m cordis.backend`.
- `make run-cli-help`: inspect the CLI entrypoint and available commands.
- `CORDIS_ENV_FILE=./.env.docker.example docker compose -f dockers/compose.yml --env-file dockers/.env.docker.example config`: validate the Docker Compose stack definition.
- `CORDIS_ENV_FILE=./.env.docker.example docker compose -f dockers/compose.yml --env-file dockers/.env.docker.example up --build postgres minio backend`: run the containerized backend stack.

## Coding Style & Naming Conventions

Target Python 3.10+ and use 4-space indentation. Prefer explicit type hints on public functions and module boundaries. Follow existing naming patterns: `snake_case` for functions and modules, `PascalCase` for classes, and short, descriptive package names under `cordis`. Before finishing Python edits, also run `black --line-length=120 --target-version=py310 tests` and `black --line-length=120 --target-version=py310 cordis`. Formatting and static checks are enforced with Ruff, Pylint, and MyPy; run `make lint` before opening a change.

## Preferred Backend Style

When working on a backend project in this repository, follow these structural preferences:

- keep a hard separation between `cordis/backend/` and `cordis/cli/`; do not reintroduce a shared package
- use `cordis/backend/config.py` for typed backend configuration and keep `cordis/backend/settings.py` as the thin setup/bootstrap layer
- keep backend security under `cordis/backend/security/` with `core.py`, `authentication/`, and `userinfo.py`
- initialize logging and security from `cordis/backend/settings.py`
- keep engine and session wiring in `cordis/backend/database.py`, not in a nested `db/` package
- use `cordis/backend/models/base.py` with `DatabaseModel` as the canonical model base
- keep backend models explicit and reference-style: `__tablename__` first, `__table_args__` when needed, typed `Mapped[...]` relationships, explicit `back_populates`, `passive_deletes=True` where FKs already use `ondelete`, and `cascade="all, delete-orphan"` on parent-owned child collections
- keep backend exceptions under `cordis/backend/exceptions/` with `app_status.py`, `exceptions.py`, and `exception_handlers.py`
- use `cordis/backend/policies/` for authorization decisions and make route modules call policies explicitly
- move request and domain checks into `cordis/backend/validators/`, not services
- use `cordis/backend/schemas/requests/` for request models and `cordis/backend/schemas/responses/` for response models
- prefer the flow `api -> policy -> validator -> service -> repository -> model -> database`
- keep FastAPI routes thin, keep services focused on orchestration and transactions, and keep persistence access in repositories
- keep user and role APIs on shared `/users` and `/roles` resource routers; enforce admin-only behavior per endpoint with policies instead of separate `/admin/...` routers
- treat each artifact as one immutable stored object addressed by a stable key; do not reintroduce required provider object-version metadata into the artifact model
- keep repository API visibility separate from raw storage exposure: use repository `visibility` for Cordis read authorization and `allow_public_object_urls` only for world-readable provider-native object URLs
- backend utilities should stay backend-runtime-specific; CLI-specific helpers belong under `cordis/cli/`
- prefer hard-cut refactors over temporary compatibility wrappers unless compatibility is explicitly required

## Preferred CLI Style

When working on the CLI in this repository, follow these structural preferences:

- keep `cordis/cli/commands/` focused on command wiring and input collection, not HTTP or transport details
- keep backend communication inside `cordis/sdk/`; CLI-specific config-driven client construction belongs under `cordis/cli/`
- keep CLI error types in `cordis/cli/errors.py` and prefer typed CLI exceptions over raw `RuntimeError`
- keep command error handling centralized; expected failures should render through the shared CLI error path rather than ad-hoc `try/except` blocks in each command
- keep CLI presentation helpers under `cordis/cli/utils/presentation.py` and prefer Rich tables, detail views, and status panels over manual string concatenation
- surface artifact `public_url` values in CLI output when present, but do not degrade mediated download flows for repositories that keep raw storage private
- keep transfer-, cache-, and CLI config-specific local behavior under `cordis/cli/utils/files.py`
- keep upload file discovery and `.cordisignore` handling in `cordis/cli/utils/files.py`, not in command handlers or SDK API modules
- keep CLI uploads path-aware and repository-aware: pre-check for reusable artifacts at the same repository path before starting upload, and only use session-based multipart transfer when reuse is not possible
- keep CLI uploads session-based and truly multipart when transfer is required: chunk files locally, upload parts sequentially, and resume by skipping persisted session parts rather than sending whole files as one part
- keep the canonical transfer chunk size in `cordis/constants.py`; the current value is `8 * 1024 * 1024`
- keep remote artifact download transport in `cordis/sdk/httpx_service.py`; streamed downloads should use the shared HTTP layer with retry, resume, and Rich progress rather than ad-hoc network helpers in the transfer layer
- `make build` is for the CLI/SDK distribution only; use `python3 -m poetry build` directly when a full repository build including `cordis/backend` is required
- prefer human-friendly default output; if adding machine-readable output later, make it explicit rather than degrading the default presentation
- keep common CLI short flags consistent: prefer `-p` for `--path`, `-id` for `--repo-id`, and `-v` for `--version`

## Testing Guidelines

Pytest is the test framework. Add tests next to the relevant area using `test_*.py` filenames and behavior-focused names such as `test_version_command_prints_project_version`. Run `make test` for the full suite, or scope locally with `python3 -m poetry run pytest tests/backend/test_app.py -q`.

## Commit & Pull Request Guidelines

Use short, imperative commit messages. The current history favors Conventional Commit-style prefixes when useful, for example `feat: initialize cordis project scaffold`. Pull requests should include a brief summary, linked issue or context when relevant, and the verification commands you ran.

## Environment Notes

Local commands intentionally use module-based execution from the repo root. Keep that pattern unless the Poetry environment setup changes, because this repository may be used from an already-active virtual environment. When documenting commands or examples, prefer the Make targets first and fall back to the module-based form only when extra detail matters.
The repository now includes Docker and Compose assets for a backend-focused PostgreSQL + MinIO stack. Keep migration execution explicit in documentation and operator workflows; do not assume the Docker stack should auto-apply schema changes unless that behavior is deliberately implemented and verified.

<!-- gitnexus:start -->
# GitNexus — Code Intelligence

This project is indexed by GitNexus as **cordis** (3145 symbols, 8214 relationships, 268 execution flows). Use the GitNexus MCP tools to understand code, assess impact, and navigate safely.

> If any GitNexus tool warns the index is stale, run `npx gitnexus analyze` in terminal first.

## Always Do

- **MUST run impact analysis before editing any symbol.** Before modifying a function, class, or method, run `gitnexus_impact({target: "symbolName", direction: "upstream"})` and report the blast radius (direct callers, affected processes, risk level) to the user.
- **MUST run `gitnexus_detect_changes()` before committing** to verify your changes only affect expected symbols and execution flows.
- **MUST warn the user** if impact analysis returns HIGH or CRITICAL risk before proceeding with edits.
- When exploring unfamiliar code, use `gitnexus_query({query: "concept"})` to find execution flows instead of grepping. It returns process-grouped results ranked by relevance.
- When you need full context on a specific symbol — callers, callees, which execution flows it participates in — use `gitnexus_context({name: "symbolName"})`.

## Never Do

- NEVER edit a function, class, or method without first running `gitnexus_impact` on it.
- NEVER ignore HIGH or CRITICAL risk warnings from impact analysis.
- NEVER rename symbols with find-and-replace — use `gitnexus_rename` which understands the call graph.
- NEVER commit changes without running `gitnexus_detect_changes()` to check affected scope.

## Resources

| Resource | Use for |
|----------|---------|
| `gitnexus://repo/cordis/context` | Codebase overview, check index freshness |
| `gitnexus://repo/cordis/clusters` | All functional areas |
| `gitnexus://repo/cordis/processes` | All execution flows |
| `gitnexus://repo/cordis/process/{name}` | Step-by-step execution trace |

## CLI

| Task | Read this skill file |
|------|---------------------|
| Understand architecture / "How does X work?" | `.claude/skills/gitnexus/gitnexus-exploring/SKILL.md` |
| Blast radius / "What breaks if I change X?" | `.claude/skills/gitnexus/gitnexus-impact-analysis/SKILL.md` |
| Trace bugs / "Why is X failing?" | `.claude/skills/gitnexus/gitnexus-debugging/SKILL.md` |
| Rename / extract / split / refactor | `.claude/skills/gitnexus/gitnexus-refactoring/SKILL.md` |
| Tools, resources, schema reference | `.claude/skills/gitnexus/gitnexus-guide/SKILL.md` |
| Index, status, clean, wiki CLI commands | `.claude/skills/gitnexus/gitnexus-cli/SKILL.md` |

<!-- gitnexus:end -->
