# Release Process

Cordis `1.0.0` uses a manual but repeatable release flow.

## Release Artifacts

- Python wheel and sdist for the CLI/SDK distribution
- Docker image built from `dockers/Dockerfile` for the backend runtime
- release notes in `CHANGELOG.md`
- deployment and operator guidance in `docs/production.md`

## Release Checklist

1. Update the version in `pyproject.toml` and `cordis/__init__.py`.
2. Update release notes in `CHANGELOG.md`.
3. Run repository verification:

```bash
make lint
make test
make build
python3 -m poetry build
CORDIS_ENV_FILE=./.env.production.example docker compose -f dockers/compose.yml --env-file dockers/.env.production.example config
CORDIS_ENV_FILE=./.env.production.example docker compose -f dockers/compose.yml --env-file dockers/.env.production.example build backend
```

4. Validate the production deployment path with the steps in `docs/production.md`.
5. Create the release commit and tag, for example `v1.0.0`.
6. Publish the CLI/SDK artifacts through the chosen Python package channel.
7. Deploy the backend image with the Compose baseline and run smoke checks.

## Scope Notes

- `make build` produces the staged CLI/SDK distribution.
- `python3 -m poetry build` produces the full repository build when you need the backend package included.
- Docker Compose is the official production deployment baseline for `1.0.0`.
