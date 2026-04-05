# Testing

Cordis uses Pytest for automated verification, with separate backend and CLI test areas.

## Test Layout

- `tests/backend/`: backend app, auth, authorization, repository, version, tag, artifact, storage, upload, download, and management-surface coverage
- `tests/cli/`: CLI command and SDK-facing workflow coverage

## Main Commands

Run the full suite:

```bash
make test
```

Run the full quality gate:

```bash
make lint
make test
```

## Targeted Test Runs

Examples:

```bash
PYTHONPATH=src python3 -m poetry run pytest tests/backend/test_auth.py -q
PYTHONPATH=src python3 -m poetry run pytest tests/backend/test_repository_domain.py -q
PYTHONPATH=src python3 -m poetry run pytest tests/cli/test_main.py -q
```

## What the Tests Cover

Backend tests focus on:

- API behavior and composition
- auth and authorization rules
- repository, version, tag, and artifact workflows
- upload and download behavior
- storage boundary behavior
- admin and management routes

CLI tests focus on:

- command wiring
- config-driven defaults
- repository registration behavior
- tag/version/repository workflows
- resource upload and download command behavior

## When Adding Features

- add behavior-focused tests close to the affected area
- prefer one test file per domain area or command surface
- keep test names descriptive and user-behavior oriented
- verify both happy paths and access/control failures when behavior changes at the backend boundary
