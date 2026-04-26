# Production Deployment

Cordis `1.0.0` supports a Docker Compose production baseline built around PostgreSQL, MinIO, the FastAPI backend, and a host-native CLI.

## Supported Baseline

- Docker Compose deployment from `dockers/compose.yml`
- PostgreSQL as the application database
- MinIO as the S3-compatible storage backend
- explicit one-off migration execution through the `migrate` service
- host-native CLI and SDK consumers outside the container stack

This baseline is the supported production target for `1.0.0`. Generic container-platform deployment and cloud-specific infrastructure recipes are not part of the official support contract yet.

## Required Configuration

Start from the production example environment:

```bash
cp dockers/.env.production.example dockers/.env.production.local
```

Set production values before startup:

- `CORDIS_SECRET_KEY` must be a long random secret and must not use the development default
- `CORDIS_DB_URL` must point to PostgreSQL
- `CORDIS_BOOTSTRAP_ADMIN_PASSWORD` must be at least 12 characters and must not use the example default
- MinIO credentials must be replaced with operator-managed values

## Deployment Sequence

Validate the Compose configuration:

```bash
CORDIS_ENV_FILE=./.env.production.local docker compose -f dockers/compose.yml --env-file dockers/.env.production.local config
```

Build the backend image:

```bash
CORDIS_ENV_FILE=./.env.production.local docker compose -f dockers/compose.yml --env-file dockers/.env.production.local build backend
```

Run migrations explicitly:

```bash
CORDIS_ENV_FILE=./.env.production.local docker compose -f dockers/compose.yml --env-file dockers/.env.production.local run --rm migrate
```

Start the production baseline stack:

```bash
CORDIS_ENV_FILE=./.env.production.local docker compose -f dockers/compose.yml --env-file dockers/.env.production.local up -d postgres minio backend
```

## Post-Deploy Smoke Checks

- `curl http://127.0.0.1:8000/healthz`
- `curl http://127.0.0.1:8000/version`
- verify the first admin bootstrap succeeds on an empty database
- verify `cordis login --endpoint http://127.0.0.1:8000`
- verify a basic repository, version, and resource workflow with operator credentials

## Operational Notes

- Keep the MinIO service private unless you intentionally need direct object access.
- Treat `dockers/.env.production.local` as a secret-bearing operator file and keep it out of version control.
- Migrations remain explicit by design so schema changes are never hidden behind normal service startup.
