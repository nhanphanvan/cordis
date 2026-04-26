# Docker Guide

Cordis ships a backend-focused Docker workflow under `dockers/`.

Use Docker from the repo root and pass the Compose file explicitly:

```bash
CORDIS_ENV_FILE=./.env.docker.example docker compose -f dockers/compose.yml --env-file dockers/.env.docker.example config
```

## Included Services

- `postgres` for the application database
- `minio` for S3-compatible object storage
- `backend` for the FastAPI service
- `migrate` as an explicit one-off Alembic job

The CLI remains host-native in this workflow.

## Quick Start

Start the local stack with the committed development example environment:

```bash
CORDIS_ENV_FILE=./.env.docker.example docker compose -f dockers/compose.yml --env-file dockers/.env.docker.example up --build postgres minio backend
```

The backend is then available on `http://127.0.0.1:8000`, MinIO on `http://127.0.0.1:9000`, and the MinIO console on `http://127.0.0.1:9001`.

The bootstrap admin values come from `dockers/.env.docker.example` by default:

- `CORDIS_BOOTSTRAP_ADMIN_EMAIL`
- `CORDIS_BOOTSTRAP_ADMIN_PASSWORD`
- `CORDIS_BOOTSTRAP_ADMIN_NAME`

On an empty database, backend startup creates the first admin from those values. If the database has no users and the bootstrap env is missing or invalid, backend startup fails.

## Local Overrides

If you want local Docker-only overrides, copy the example to an untracked file and use that file with `--env-file`:

```bash
cp dockers/.env.docker.example dockers/.env.docker.local
CORDIS_ENV_FILE=./.env.docker.local docker compose -f dockers/compose.yml --env-file dockers/.env.docker.local up --build postgres minio backend
```

Keep local override files out of version control.

For production deployment, use the separate guide in [Production Deployment](./production.md) and start from `dockers/.env.production.example` instead of the development example.

## Migrations

Migrations are operator-managed and do not run automatically when you start `backend`.

Run them explicitly when needed:

```bash
CORDIS_ENV_FILE=./.env.docker.example docker compose -f dockers/compose.yml --env-file dockers/.env.docker.example run --rm migrate
```

This keeps schema changes as a deliberate step instead of hiding them behind normal service startup.

## Host-Native CLI

Point the host CLI at the containerized backend:

```bash
cordis login --endpoint http://127.0.0.1:8000 --email <email> --password <password>
```

You can also omit `--email` and `--password` and enter them interactively.
