# Cordis

Cordis is a service for managing files, folders, and artifacts with first-class support for large objects. This repository starts with two components:

- a FastAPI backend core
- a Typer-based CLI/SDK

## Requirements

- Python 3.10 or newer
- Poetry

## Getting Started

```bash
make install
make lint
make test
```

If Poetry is running inside an already-active virtual environment, keep local commands module-based from `src/` rather than relying on editable-root installation.

## Local Development

Start the backend:

```bash
make run-backend
```

Inspect the CLI:

```bash
make run-cli-help
```
