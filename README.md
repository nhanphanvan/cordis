# Cordis

Cordis is a file and artifact management service built for large-scale objects. It provides a FastAPI backend for repository, version, tag, and artifact workflows, plus a Typer-based CLI for authentication, repository management, and resource transfer operations with structured Rich-rendered output.

Full project documentation lives under [`docs/`](./docs/index.md).

## What It Includes

- A FastAPI backend with versioned API routes under `/api/v1`
- A Typer CLI for login, repository, version, tag, user, and resource workflows
- Rich-rendered CLI tables, detail views, success panels, typed error output, and streamed transfer progress
- Artifact metadata, upload-session, and download flows for large object handling
- `.cordisignore` support for Gitignore-style upload exclusions
- Sequential resumable multipart uploads with a shared `8 MiB` transfer chunk size
- Backend-owned configuration, JWT security, app-status exceptions, and S3-compatible storage integration
- Required storage object-version lineage for persisted artifacts

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
- [Transfer Workflows](./docs/transfer-workflows.md)
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

- `cordis/backend/`: FastAPI application, API routers, policies, validators, services, repositories, security, exception handling, and storage integration
- `cordis/cli/`: Typer CLI, SDK client, presentation/error handling, config handling, and transfer helpers
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

Common shared short flags include `-p` for `--path`, `-id` for `--repo-id`, and `-v` for `--version`.

The backend and CLI are designed to work together: the backend owns repository and artifact state, while the CLI handles operator-facing workflows such as authentication, workspace registration, uploads, downloads, and local cache management. The CLI now renders both success and expected failure states through a shared presentation layer, uses sequential resumable multipart uploads with a shared `8 MiB` transfer chunk size, and streams remote artifact downloads through the shared HTTP transport with retry, resume, and Rich progress. The backend storage layer now supports MinIO and real AWS S3, while preserving required object versioning so persisted artifacts always carry a `storage_version_id` that resolves the exact underlying object version.

## Quality Checks

The repository uses Ruff, Pylint, MyPy, and Pytest.

```bash
make lint
make typecheck
make test
```
