PYTHON ?= python3.11
VENV := .venv/bin
export PYTHONPATH := backend:.
export PATH := $(CURDIR)/.venv/bin:$(PATH)
.PHONY: setup runner sources corpus train types dev demo test lint build check reproduce
setup:
	$(PYTHON) -m venv .venv
	$(VENV)/python -m pip install -r requirements.lock
	cd frontend && npm ci
runner:
	docker build -t samyak-runner:phase1 runner
sources:
	$(VENV)/python scripts/data_sources.py
corpus:
	$(VENV)/python scripts/build_corpus.py
train:
	$(VENV)/python scripts/train.py
types:
	$(VENV)/python scripts/export_openapi.py
	cd frontend && npx openapi-typescript openapi.json -o src/lib/api.d.ts
dev:
	$(VENV)/python scripts/dev.py
demo:
	$(VENV)/python scripts/demo.py
test:
	$(VENV)/pytest -q
	cd frontend && npm test
lint:
	$(VENV)/ruff check backend scripts runner
	$(VENV)/ruff format --check backend scripts runner
	cd frontend && npm run lint && npm run typecheck
build:
	cd frontend && npm run build
check: lint test build
reproduce: sources runner corpus train
