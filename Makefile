PYTHON ?= python3
NPM ?= npm

.PHONY: install backend-install frontend-install lint format mypy test typecheck frontend-test frontend-build quality db-upgrade db-seed audit-prune precommit-install precommit-run docker-up export-openapi codegen-contracts

install: backend-install frontend-install

backend-install:
	$(PYTHON) -m pip install -e ".[dev]"

frontend-install:
	$(NPM) --prefix frontend ci

lint:
	$(PYTHON) -m ruff check src tests alembic

format:
	$(PYTHON) -m ruff format src tests alembic

test:
	$(PYTHON) -m pytest -q

mypy:
	$(PYTHON) -m mypy src tests

typecheck:
	$(NPM) --prefix frontend run typecheck

frontend-test:
	$(NPM) --prefix frontend run test:run

frontend-build:
	$(NPM) --prefix frontend run build

quality: lint mypy test codegen-contracts typecheck frontend-test frontend-build

db-upgrade:
	$(PYTHON) -m relational_fraud_intelligence.manage migrate

db-seed:
	$(PYTHON) -m relational_fraud_intelligence.manage seed

audit-prune:
	$(PYTHON) -m relational_fraud_intelligence.manage prune-audit

precommit-install:
	pre-commit install --install-hooks
	pre-commit install --hook-type pre-push --install-hooks

precommit-run:
	pre-commit run --all-files

docker-up:
	docker compose up --build

export-openapi:
	$(PYTHON) scripts/export_openapi.py

codegen-contracts: export-openapi
	$(NPM) --prefix frontend run codegen:contracts

