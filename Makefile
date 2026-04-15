.PHONY: install
install:
	python3 -m poetry install --with dev,test --no-root

.PHONY: lint
fix:
	python3 -m poetry run ruff check --fix .
	python3 -m poetry run black --line-length=120 --target-version=py310 tests
	python3 -m poetry run black --line-length=120 --target-version=py310 cordis

.PHONY: lint
lint:
	python3 -m poetry check
	python3 -m poetry run ruff check .
	python3 -m poetry run pylint cordis
	python3 -m poetry run mypy cordis

.PHONY: format
format:
	python3 -m poetry run ruff format .

.PHONY: typecheck
typecheck:
	python3 -m poetry run mypy cordis

.PHONY: test
test:
	python3 -m poetry run pytest

.PHONY: build
build:
	python3 scripts/build_cli_sdk_dist.py

.PHONY: run-backend
run-backend:
	python3 -m poetry run python -m cordis.backend

.PHONY: run-cli-help
run-cli-help:
	python3 -m poetry run python -m cordis.cli --help

.PHONY: clean
clean:
	find . -type d -name "__pycache__" -prune -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -prune -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -prune -exec rm -rf {} +
	find . -type d -name ".ruff_cache" -prune -exec rm -rf {} +
	find . -type f -name ".coverage*" -delete
