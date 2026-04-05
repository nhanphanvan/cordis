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
- default storage provider: `s3`
- default storage bucket: `cordis-artifacts`

The settings object also exposes a derived synchronous database URL for tooling that requires a sync-style database connection string.

The database configuration also exposes a computed `database_engine_args` property used when creating the SQLAlchemy async engine:

- PostgreSQL-style URLs use the full pool tuning surface
- SQLite URLs use a reduced SQLite-safe subset

Backend process logging is configured during startup from `CORDIS_LOG_LEVEL`. The backend uses the logging helper under `cordis.backend.utils.logging` for console output and key application workflow logs.

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

The CLI cache is used by resource transfer helpers to reuse downloaded or uploaded file content when possible.

### Workspace registration

Project-local registration lives at:

```text
<current-working-directory>/.cordis/config.json
```

This file stores:

- `repo_id`
- `version`

Commands such as `cordis resource upload`, `cordis resource download`, and several repository/tag/version commands can use these registered values implicitly.

## Operational Notes

- Backend settings are environment-driven and should not be stored in CLI config files.
- CLI state is local to the developer or operator machine and is safe to treat as user-specific state.
- Resource transfer behavior depends on both the configured backend endpoint and the local cache directory.
