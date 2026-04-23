# Cordis

Cordis is a file and artifact management service built for large-scale objects. It provides a FastAPI backend for repository, version, tag, and artifact workflows, plus a Typer-based CLI for authentication, repository management, and resource transfer operations with structured Rich-rendered output.

Full project documentation lives under [`docs/`](./docs/index.md).

## What It Includes

- A FastAPI backend with versioned API routes under `/api/v1`
- Shared `/users` and `/roles` API resources with per-endpoint admin gating for management operations
- A Typer CLI for login, repository, version, tag, user, and resource workflows
- Rich-rendered CLI tables, detail views, success panels, typed error output, streamed remote download progress, and compact download completion summaries
- Artifact metadata, upload-session, and download flows for large object handling
- `.cordisignore` support for Gitignore-style upload exclusions
- Atomic upload preflight for `resource upload`, so same-version path conflicts abort the whole folder before any mutation
- `--force` support for upload and download workflows: clear version contents before folder upload, replace one target path for `resource upload-item`, or wipe the destination before download
- Pre-upload artifact reuse for unchanged files at the same repository path across versions
- Single-file `resource upload-item` support with explicit repository target paths
- Destination-file checksum reuse for downloads, so an exact local file match can skip both cache copy and remote transfer
- Sequential resumable multipart uploads with a shared `8 MiB` transfer chunk size
- Backend-owned configuration, JWT security, app-status exceptions, and S3-compatible storage integration
- Immutable artifact object keys in shared S3-compatible storage
- Repository `visibility` for Cordis API reads and `allow_public_object_urls` for prefix-scoped raw provider-native asset and package URLs inside the shared storage bucket

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
make build
```

Start the backend locally:

```bash
make run-backend
```

Inspect the CLI entrypoint and available commands:

```bash
make run-cli-help
```

Build the CLI/SDK distribution artifacts:

```bash
make build
```

This staged build excludes `cordis/backend`. If you need a full repository build including backend code, run `python3 -m poetry build` directly.

## Docker

Cordis now includes a backend-focused Docker workflow for local stacks and deployment packaging.

The container stack standardizes on:

- PostgreSQL for the application database
- MinIO for S3-compatible object storage
- the FastAPI backend service
- an explicit Alembic workflow that is still operator-managed

Start the stack:

```bash
cp .env.docker.example .env
docker compose up --build postgres minio backend
```

The backend is then available on `http://127.0.0.1:8000`, MinIO on `http://127.0.0.1:9000`, and the MinIO console on `http://127.0.0.1:9001`.

If you want to run Alembic in the Docker workflow, do it as an explicit operator step:

```bash
docker compose run --rm migrate
```

That migration flow is still being finalized. Treat it as manual infrastructure work for now rather than assuming the stack will bootstrap a fresh database automatically.

The CLI remains host-native in this first pass. Point it at the containerized backend with:

```bash
cordis login --endpoint http://127.0.0.1:8000 --email <email> --password <password>
```

You can also run `cordis login` without `--email` or `--password` and enter those values interactively at the prompt.

## Project Layout

- `cordis/backend/`: FastAPI application, API routers, policies, validators, services, repositories, security, exception handling, and storage integration
- `cordis/cli/`: Typer CLI, command wiring, error handling, and CLI-local helpers under `cordis/cli/utils/`
- `cordis/sdk/`: public Python SDK, API client modules, transfer orchestration, and shared HTTP transport
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

Email-based commands also accept `-e` as the short form of `--email`.

The backend and CLI are designed to work together: the backend owns repository and artifact state, while the CLI handles operator-facing workflows such as authentication, workspace registration, uploads, downloads, and local cache management. The CLI now preflights the full upload folder before mutating anything, so if the target version already contains a conflicting path with different content the whole upload is rejected and no later files are attached or transferred. Exact same-content paths already present in the target version are reported as `Unchanged`, while repository-scoped reuse across versions still skips storage upload when possible. `resource upload --force` first clears the target version's `version_artifact` associations without deleting shared artifact metadata. `resource upload-item` uses the same reuse and resumable multipart flow for one local file and one explicit repository target path; `resource upload-item --force` replaces only that target version path rather than clearing the whole version. On download, Cordis first checks whether the destination file already exists and exactly matches the artifact checksum; if so, it logs `Already present: <path>` and skips both cache copy and remote transfer. Cache hits are logged as `Copied from cache: <path>`, and remote transfers stream through the shared SDK HTTP transport with retry, resume, and Rich progress. `resource download --force` wipes the destination root before materializing the version into a clean directory, and successful full-version downloads finish with one compact summary panel instead of per-file result tables. The `resource download-item` command still only resolves and prints the mediated URL; it does not yet stream the file itself. The backend storage layer supports MinIO and real AWS S3, stores each artifact under its own immutable object key, and can expose provider-native raw object URLs when a repository enables `allow_public_object_urls` by synchronizing public read access for that repository's storage prefix. On MinIO, Cordis initializes an empty bucket policy automatically when the bucket does not already have one, so the first repository that enables public object URLs does not require manual bucket-policy setup.

## Quality Checks

The repository uses Ruff, Pylint, MyPy, and Pytest.

```bash
make lint
make typecheck
make test
```
