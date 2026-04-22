# Configuration

Cordis has two different configuration surfaces:

- backend runtime settings, provided through environment variables
- CLI local state, persisted in JSON files

## Backend Settings

The backend configuration lives in `cordis.backend.config` and uses the `CORDIS_` environment variable names.

Current settings:

- `CORDIS_APP_NAME`
- `CORDIS_ENVIRONMENT`
- `CORDIS_API_V1_PREFIX`
- `CORDIS_DB_URL`
- `CORDIS_DB_ECHO`
- `CORDIS_DB_POOL_SIZE`
- `CORDIS_DB_MAX_OVERFLOW`
- `CORDIS_DB_POOL_TIMEOUT`
- `CORDIS_DB_POOL_RECYCLE`
- `CORDIS_LOG_LEVEL`
- `CORDIS_HOST`
- `CORDIS_PORT`
- `CORDIS_SECRET_KEY`
- `CORDIS_JWT_ALGORITHM`
- `CORDIS_ACCESS_TOKEN_EXPIRE_MINUTES`
- `CORDIS_STORAGE_PROVIDER`
- `CORDIS_STORAGE_BUCKET`
- `CORDIS_STORAGE_PREFIX`
- `CORDIS_STORAGE_ENDPOINT`
- `CORDIS_STORAGE_ACCESS_KEY`
- `CORDIS_STORAGE_SECRET_KEY`
- `CORDIS_STORAGE_REGION`
- `CORDIS_STORAGE_SECURE`
- `CORDIS_STORAGE_PRESIGN_EXPIRY_SECONDS`

Important defaults:

- API prefix: `/api/v1`
- default host: `127.0.0.1`
- default port: `8000`
- default log level: `INFO`
- default database URL: `sqlite+aiosqlite:///./.cordis/cordis.db`
- default JWT algorithm: `HS256`
- default access token expiry: `60` minutes
- default storage provider: `minio`
- default storage bucket: `cordis-artifacts`

The settings object also exposes a derived synchronous database URL for tooling that requires a sync-style database connection string.

The database configuration also exposes a computed `database_engine_args` property used when creating the SQLAlchemy async engine:

- PostgreSQL-style URLs use the full pool tuning surface
- SQLite URLs use a reduced SQLite-safe subset

Backend process logging is configured during startup from `CORDIS_LOG_LEVEL`. The backend uses the logging helper under `cordis.backend.utils.logging` for console output and key application workflow logs.

Security settings are loaded from the same backend config layer. `cordis.backend.settings.setup()` initializes logging and the security core before the server starts accepting requests, and access tokens are signed JWTs configured by:

- `CORDIS_SECRET_KEY`
- `CORDIS_JWT_ALGORITHM`
- `CORDIS_ACCESS_TOKEN_EXPIRE_MINUTES`

Cordis also supports first-run admin bootstrap during backend startup. This bootstrap runs from the FastAPI application lifespan in `cordis.backend.app`, so it shares the same async event loop as request handling:

- `CORDIS_BOOTSTRAP_ADMIN_EMAIL`
- `CORDIS_BOOTSTRAP_ADMIN_PASSWORD`
- `CORDIS_BOOTSTRAP_ADMIN_NAME`

Bootstrap behavior:

- default repository roles `owner`, `developer`, and `viewer` are ensured on every startup
- if the database has zero users, backend startup requires `CORDIS_BOOTSTRAP_ADMIN_EMAIL` and `CORDIS_BOOTSTRAP_ADMIN_PASSWORD`
- if the database has zero users and those env vars are missing or invalid, backend startup fails
- if the database already has at least one user, bootstrap admin env values are ignored and existing users are not modified
- `CORDIS_BOOTSTRAP_ADMIN_NAME` is optional and defaults to `Admin`

There is no separate backend storage-policy environment variable for public object exposure. Raw provider-native object exposure is controlled per repository through the repository-level `allow_public_object_urls` flag.

For Docker and Compose workflows, Cordis keeps the same `CORDIS_*` contract instead of introducing a second container-specific config layer. The repository now includes `.env.docker.example` as the baseline local stack environment.

## MinIO Storage Behavior

The backend storage layer supports two providers:

- `minio`
- `s3`

For `CORDIS_STORAGE_PROVIDER=minio`, the backend expects:

- `CORDIS_STORAGE_ENDPOINT`
- `CORDIS_STORAGE_ACCESS_KEY`
- `CORDIS_STORAGE_SECRET_KEY`
- `CORDIS_STORAGE_BUCKET`

MinIO endpoint format matters here:

- set `CORDIS_STORAGE_ENDPOINT` to `host:port`, for example `127.0.0.1:9000`
- do not include a scheme such as `http://` or `https://`
- use `CORDIS_STORAGE_SECURE=true|false` to control TLS instead of encoding that in the endpoint string

At adapter initialization time, the backend:

- connects to MinIO using the configured endpoint, credentials, region, and secure flag
- creates the configured bucket if it does not already exist

When a repository enables `allow_public_object_urls`, Cordis updates the bucket policy for only that repository's storage prefix inside the shared bucket. For MinIO, this is a prefix-scoped public-read policy for object fetches, not a bucket-wide public/private toggle. If the bucket does not have any policy yet, Cordis initializes an empty policy document and then adds the repository-scoped allow statement; operators do not need to pre-create a bucket policy just to enable the first public repository prefix.

For `CORDIS_STORAGE_PROVIDER=s3`, the backend uses `boto3` and expects a pre-provisioned AWS S3 bucket.

Operational expectations for `s3`:

- the configured bucket must already exist
- the backend validates bucket accessibility during storage adapter initialization
- the backend does not create AWS buckets automatically

If the S3 bucket is missing or inaccessible, adapter initialization fails.

When a repository enables `allow_public_object_urls`, Cordis applies the same prefix-scoped policy model for S3. The repository flag updates public read access only for that repository's object prefix in the shared bucket. Disabling the flag removes the Cordis-managed allow statement for that prefix; it does not write a blanket deny policy.

## CLI Configuration

The CLI stores state in JSON files.

### Global config

Default location:

```text
~/.cordis/config.json
```

Override the root with:

```text
CORDIS_HOME=/path/to/custom-home
```

The global config stores values such as:

- `endpoint`
- `token`
- `email`

### Cache directory

Default location:

```text
~/.cordis/cache
```

The CLI cache is used by resource transfer helpers to reuse downloaded or uploaded file content when possible. For downloads, Cordis first checks whether the destination file already exists and matches the artifact checksum, then falls back to cache reuse, and only then streams remotely when needed. When cached content is missing, remote artifact downloads stream through the shared SDK HTTP transport and then populate the cache after success.

### Workspace registration

Project-local registration lives at:

```text
<current-working-directory>/.cordis/config.json
```

This file stores:

- `repo_id`
- `version`

Commands such as `cordis resource upload`, `cordis resource download`, and several repository/tag/version commands can use these registered values implicitly.

## Docker Notes

The current Docker/Compose workflow is backend-focused:

- the backend runs in a container
- PostgreSQL and MinIO run in containers
- Alembic is available as an explicit one-off migration command
- the CLI stays host-native for now

The Compose example standardizes on PostgreSQL plus MinIO even though Cordis still supports SQLite and real AWS S3 outside Docker.
The repository includes a `migrate` Compose service, but schema migration execution should currently be treated as a manual operator step rather than an assumed automatic bootstrap phase.

## Operational Notes

- Backend settings are environment-driven and should not be stored in CLI config files.
- CLI state is local to the developer or operator machine and is safe to treat as user-specific state.
- Resource transfer behavior depends on both the configured backend endpoint and the local cache directory.
- Remote download behavior also depends on the shared SDK HTTP transport, which now owns retry, resume, and progress handling.
- `resource download --force` deletes the destination root before downloading, while `resource upload --force` clears the target version contents before upload.
- Repository `visibility` and storage public access are separate controls.
- `visibility` governs Cordis API read authorization.
- `allow_public_object_urls` governs whether artifact responses include provider-native `public_url` values and whether the backend syncs prefix-scoped storage read access for that repository.
- On MinIO, the first enablement can create the bucket policy lazily if none exists yet.
