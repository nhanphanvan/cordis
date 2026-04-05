# Cordis

Cordis is a file and artifact management service built for large-scale objects. It provides a FastAPI backend for repository, version, tag, and artifact workflows, plus a Typer-based CLI for authentication, repository management, and resource transfer operations.

Full project documentation lives under [`docs/`](./docs/index.md).

## What It Includes

- A FastAPI backend with versioned API routes under `/api/v1`
- A Typer CLI for login, repository, version, tag, user, and resource workflows
- Artifact metadata, upload-session, and download flows for large object handling
- Backend-owned configuration, app-status exceptions, and storage integration

## Requirements

- Python 3.10 or newer
- Poetry

## Installation

Install development and test dependencies with:

```bash
make install
```

If Poetry is running inside an already-active virtual environment, keep local commands module-based from the repo root instead of relying on editable-root installation.

## Documentation

- [Documentation Index](./docs/index.md)
- [Getting Started](./docs/getting-started.md)
- [Configuration](./docs/configuration.md)
- [CLI Guide](./docs/cli.md)
- [Backend API](./docs/backend-api.md)
- [Architecture](./docs/architecture.md)
- [Development](./docs/development.md)

## Local Development

Run the main verification commands:

```bash
make lint
make test
```

Start the backend locally:

```bash
make run-backend
```

Inspect the CLI entrypoint and available commands:

```bash
make run-cli-help
```

## Project Layout

- `cordis/backend/`: FastAPI application, API routers, domain services, repositories, models, exception handling, and storage integration
- `cordis/cli/`: Typer CLI, SDK client, config handling, and transfer helpers
- `tests/backend/`: backend-focused tests
- `tests/cli/`: CLI-focused tests

## Using Cordis

Cordis exposes two main entrypoints:

- `cordis-server` for running the backend service
- `cordis` for CLI workflows

Common CLI areas include:

- `cordis login`
- `cordis user ...`
- `cordis repository ...`
- `cordis version ...`
- `cordis tag ...`
- `cordis resource ...`

The backend and CLI are designed to work together: the backend owns repository and artifact state, while the CLI handles operator-facing workflows such as authentication, workspace registration, uploads, downloads, and local cache management.

## Quality Checks

The repository uses Ruff, Pylint, MyPy, and Pytest.

```bash
make lint
make typecheck
make test
```
