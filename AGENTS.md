# Repository Guidelines

## Project Structure & Module Organization

Application code lives under `src/cordis/`. Use `src/cordis/backend/` for the FastAPI service, `src/cordis/cli/` for the Typer CLI and SDK, and `src/cordis/shared/` for shared settings or cross-cutting utilities. Keep modules focused and colocate related behavior. Tests live under `tests/`, split into `tests/backend/` and `tests/cli/`. Root files such as `pyproject.toml`, `Makefile`, and `README.md` define tooling and local workflow.

## Build, Test, and Development Commands

- `make install`: install Poetry-managed dependencies for development and tests.
- `make lint`: run `poetry check`, Ruff, Pylint, and MyPy.
- `make format`: format the repository with Ruff.
- `make typecheck`: run MyPy only.
- `make test`: run the full pytest suite.
- `make run-backend`: start the backend with `python -m cordis.backend`.
- `make run-cli-help`: inspect the CLI entrypoint and available commands.

## Coding Style & Naming Conventions

Target Python 3.10+ and use 4-space indentation. Prefer explicit type hints on public functions and module boundaries. Follow existing naming patterns: `snake_case` for functions and modules, `PascalCase` for classes, and short, descriptive package names under `cordis`. Formatting and static checks are enforced with Ruff, Pylint, and MyPy; run `make lint` before opening a change.

## Testing Guidelines

Pytest is the test framework. Add tests next to the relevant area using `test_*.py` filenames and behavior-focused names such as `test_version_command_prints_project_version`. Run `make test` for the full suite, or scope locally with `PYTHONPATH=src python3 -m poetry run pytest tests/backend/test_app.py -q`.

## Commit & Pull Request Guidelines

Use short, imperative commit messages. The current history favors Conventional Commit-style prefixes when useful, for example `feat: initialize cordis project scaffold`. Pull requests should include a brief summary, linked issue or context when relevant, and the verification commands you ran.

## Environment Notes

Local commands intentionally use `PYTHONPATH=src` and module-based execution. Keep that pattern unless the Poetry environment setup changes, because this repository may be used from an already-active virtual environment. When documenting commands or examples, prefer the Make targets first and fall back to the module-based form only when extra detail matters.
