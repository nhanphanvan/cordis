# Configuration

Cordis has two different configuration surfaces:

- backend runtime settings, provided through environment variables
- CLI local state, persisted in JSON files

## Backend Settings

The backend settings live in `cordis.shared.settings.Settings` and use the `CORDIS_` prefix.

Current settings:

- `CORDIS_APP_NAME`
- `CORDIS_ENVIRONMENT`
- `CORDIS_API_V1_PREFIX`
- `CORDIS_DB_URL`
- `CORDIS_DB_ECHO`
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
- default database URL: `sqlite+aiosqlite:///./.cordis/cordis.db`
- default storage provider: `s3`
- default storage bucket: `cordis-artifacts`

The settings object also exposes a derived synchronous database URL for tooling that requires a sync-style database connection string.

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
