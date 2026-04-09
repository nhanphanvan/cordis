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
6. List version contents with `cordis resource ls`.
7. Download them again with `cordis resource download --path <target-folder>`.

If the upload folder contains files you do not want to send, add a `.cordisignore` file there. Cordis uses Gitignore-style matching rules for upload exclusion.

## Important Local Paths

- Global CLI home: `~/.cordis` by default, or `CORDIS_HOME` when overridden
- Global CLI config: `~/.cordis/config.json`
- Global CLI cache: `~/.cordis/cache`
- Workspace registration file: `<project>/.cordis/config.json`

## Next Reading

- Read [Configuration](./configuration.md) to understand backend settings and CLI persistence.
- Read [CLI Guide](./cli.md) for command workflows.
- Read [Architecture](./architecture.md) for the internal structure.
