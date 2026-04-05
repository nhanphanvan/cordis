# Repository Guidelines

## Project Structure & Module Organization

Application code lives under `cordis/`. Use `cordis/backend/` for the FastAPI service and backend-owned runtime concerns such as config, exception handling, and storage integration, and `cordis/cli/` for the Typer CLI and SDK. Keep modules focused and colocate related behavior. Tests live under `tests/`, split into `tests/backend/` and `tests/cli/`. Root files such as `pyproject.toml`, `Makefile`, and `README.md` define tooling and local workflow.

## Build, Test, and Development Commands

- `make install`: install Poetry-managed dependencies for development and tests.
- `make lint`: run `poetry check`, Ruff, Pylint, and MyPy.
- `make fix`: run Ruff autofixes, then Black on `tests/` and `cordis/`.
- `make format`: format the repository with Ruff.
- `make typecheck`: run MyPy only.
- `make test`: run the full pytest suite.
- `make run-backend`: start the backend with `python -m cordis.backend`.
- `make run-cli-help`: inspect the CLI entrypoint and available commands.

## Coding Style & Naming Conventions

Target Python 3.10+ and use 4-space indentation. Prefer explicit type hints on public functions and module boundaries. Follow existing naming patterns: `snake_case` for functions and modules, `PascalCase` for classes, and short, descriptive package names under `cordis`. Before finishing Python edits, also run `black --line-length=120 --target-version=py310 tests` and `black --line-length=120 --target-version=py310 cordis`. Formatting and static checks are enforced with Ruff, Pylint, and MyPy; run `make lint` before opening a change.

## Preferred Backend Style

When working on a backend project in this repository, follow these structural preferences:

- keep a hard separation between `cordis/backend/` and `cordis/cli/`; do not reintroduce a shared package
- use `cordis/backend/config.py` for typed backend configuration and keep `cordis/backend/settings.py` as the thin setup/bootstrap layer
- keep engine and session wiring in `cordis/backend/database.py`, not in a nested `db/` package
- use `cordis/backend/models/base.py` with `DatabaseModel` as the canonical model base
- keep backend exceptions under `cordis/backend/exceptions/` with `app_status.py`, `exceptions.py`, and `exception_handlers.py`
- use `cordis/backend/policies/` for authorization decisions and make route modules call policies explicitly
- move request and domain checks into `cordis/backend/validators/`, not services
- use `cordis/backend/schemas/requests/` for request models and `cordis/backend/schemas/responses/` for response models
- prefer the flow `api -> policy -> validator -> service -> repository -> model -> database`
- keep FastAPI routes thin, keep services focused on orchestration and transactions, and keep persistence access in repositories
- backend utilities should stay backend-runtime-specific; CLI-specific helpers belong under `cordis/cli/`
- prefer hard-cut refactors over temporary compatibility wrappers unless compatibility is explicitly required

## Testing Guidelines

Pytest is the test framework. Add tests next to the relevant area using `test_*.py` filenames and behavior-focused names such as `test_version_command_prints_project_version`. Run `make test` for the full suite, or scope locally with `python3 -m poetry run pytest tests/backend/test_app.py -q`.

## Commit & Pull Request Guidelines

Use short, imperative commit messages. The current history favors Conventional Commit-style prefixes when useful, for example `feat: initialize cordis project scaffold`. Pull requests should include a brief summary, linked issue or context when relevant, and the verification commands you ran.

## Environment Notes

Local commands intentionally use module-based execution from the repo root. Keep that pattern unless the Poetry environment setup changes, because this repository may be used from an already-active virtual environment. When documenting commands or examples, prefer the Make targets first and fall back to the module-based form only when extra detail matters.
