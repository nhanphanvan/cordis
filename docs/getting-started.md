# Getting Started

This guide gets a local Cordis environment running for development.

## Requirements

- Python 3.10 or newer
- Poetry

## Install Dependencies

```bash
make install
```

Cordis expects local commands to run from the repo root. The `Makefile` already does this, so use the provided targets by default.

## Verify the Environment

```bash
make lint
make test
```

## Run the Backend

```bash
make run-backend
```

By default the backend binds to `127.0.0.1:8000` and exposes the versioned API under `/api/v1`.

Useful quick checks:

```bash
curl http://127.0.0.1:8000/healthz
curl http://127.0.0.1:8000/api/v1/healthz
```

## Inspect the CLI

```bash
make run-cli-help
```

The CLI entrypoint is `cordis`, with command groups for users, repositories, versions, tags, and resource transfers.

## First Local Workflow

1. Start the backend with `make run-backend`.
2. Inspect the CLI with `make run-cli-help`.
3. Log in with `cordis login --email <email> --password <password>`.
4. Register a working directory with `cordis repository register --repo-id <id> --version <name>`.
5. Upload local contents with `cordis resource upload --path <folder>`.
6. Or upload one file to one explicit repository path with `cordis resource upload-item --source-path <local-file> --target-path <artifact-path>`.
7. List version contents with `cordis resource ls`.
8. Download them again with `cordis resource download --path <target-folder>`.

If the upload folder contains files you do not want to send, add a `.cordisignore` file there. Cordis uses Gitignore-style matching rules for upload exclusion.
If you upload a later version where a file is unchanged at the same repository path, Cordis can now reuse the existing artifact and skip the storage upload for that file.
If you upload to the same target version and one path already exists there with different content, Cordis rejects the whole folder before starting any upload or attach operations.
If you use `cordis resource upload --force`, Cordis clears the target version contents first by removing version-to-artifact associations, then uploads the folder as the new version contents.
If you use `cordis resource upload-item --force`, Cordis removes only the existing association for that one target path in the version before replacing it.
If you use `cordis resource download --force`, Cordis wipes the target directory before downloading. Without `--force`, it keeps unrelated files in place and can skip work entirely when a destination file already matches the artifact checksum.

## Important Local Paths

- Global CLI home: `~/.cordis` by default, or `CORDIS_HOME` when overridden
- Global CLI config: `~/.cordis/config.json`
- Global CLI cache: `~/.cordis/cache`
- Workspace registration file: `<project>/.cordis/config.json`

## Next Reading

- Read [Configuration](./configuration.md) to understand backend settings and CLI persistence.
- Read [CLI Guide](./cli.md) for command workflows.
- Read [Architecture](./architecture.md) for the internal structure.

## Dockerized Local Stack

Cordis also supports a backend-focused Docker Compose workflow built around PostgreSQL and MinIO.

Recommended startup flow:

```bash
cp .env.docker.example .env
docker compose up --build postgres minio backend
```

The bootstrap admin env in `.env.docker.example` is now part of first-run startup. On an empty database, the backend creates the first admin user from:

- `CORDIS_BOOTSTRAP_ADMIN_EMAIL`
- `CORDIS_BOOTSTRAP_ADMIN_PASSWORD`
- `CORDIS_BOOTSTRAP_ADMIN_NAME`

If the database has no users and the required bootstrap env is missing or invalid, backend startup fails.

This stack runs:

- `postgres` for the application database
- `minio` for S3-compatible object storage
- `backend` as the FastAPI service

If you want to run Alembic from Docker, do it explicitly:

```bash
docker compose run --rm migrate
```

Treat that migration step as operator-managed for now. The Docker stack should currently be read as backend packaging plus service orchestration, not as guaranteed fresh-database bootstrap automation.

The host-native CLI can target that backend once it is running:

```bash
cordis login --endpoint http://127.0.0.1:8000 --email <email> --password <password>
```
