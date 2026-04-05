.PHONY: install
install:
	python3 -m poetry install --with dev,test --no-root

.PHONY: lint
fix:
	PYTHONPATH=src python3 -m poetry run ruff check --fix ${path}

.PHONY: lint
lint:
	python3 -m poetry check
	PYTHONPATH=src python3 -m poetry run ruff check .
	PYTHONPATH=src python3 -m poetry run pylint src
	PYTHONPATH=src python3 -m poetry run mypy src

.PHONY: format
format:
	PYTHONPATH=src python3 -m poetry run ruff format .

.PHONY: typecheck
typecheck:
	PYTHONPATH=src python3 -m poetry run mypy src

.PHONY: test
test:
	PYTHONPATH=src python3 -m poetry run pytest

.PHONY: run-backend
run-backend:
	PYTHONPATH=src python3 -m poetry run python -m cordis.backend

.PHONY: run-cli-help
run-cli-help:
	PYTHONPATH=src python3 -m poetry run python -m cordis.cli --help

.PHONY: clean
clean:
	find . -type d -name "__pycache__" -prune -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -prune -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -prune -exec rm -rf {} +
	find . -type d -name ".ruff_cache" -prune -exec rm -rf {} +
	find . -type f -name ".coverage*" -delete
