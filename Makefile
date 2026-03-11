PYTHON ?= python3
NPM ?= npm

.PHONY: install backend-install frontend-install test typecheck frontend-build docker-up

install: backend-install frontend-install

backend-install:
	$(PYTHON) -m pip install -e ".[dev]"

frontend-install:
	$(NPM) --prefix frontend install

test:
	$(PYTHON) -m pytest -q

typecheck:
	$(NPM) --prefix frontend run typecheck

frontend-build:
	$(NPM) --prefix frontend run build

docker-up:
	docker compose up --build
