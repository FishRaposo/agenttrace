PYTHON := python
NPM    := npm

.PHONY: install dev test sdk-test server-test dashboard-test lint format typecheck \
        docker-up docker-down demo clean help

install: ## Install shared-core, the SDK (standalone), server, and dashboard deps
	pip install -e ../shared-core
	pip install -e sdk
	pip install -e "server[dev]"
	cd dashboard && $(NPM) install

dev: ## Run the collector server locally (uvicorn on :8000)
	cd server && uvicorn app.main:app --reload --port 8000

test: sdk-test server-test ## Run SDK + server test suites

sdk-test: ## Run SDK tests (standalone — no shared-core)
	cd sdk && $(PYTHON) -m pytest -q

server-test: ## Run server tests
	cd server && $(PYTHON) -m pytest -q

dashboard-test: ## Run dashboard Playwright tests
	cd dashboard && npx playwright test --project=chromium

lint: ## Lint server + SDK + examples with ruff
	ruff check server/app sdk/agenttrace examples server/tests sdk/tests

format: ## Format Python code with ruff
	ruff format server/app sdk/agenttrace examples server/tests sdk/tests

typecheck: ## Type-check server + SDK with pyright
	pyright server/app sdk/agenttrace

docker-up: ## Start Postgres + Redis + server + dashboard
	docker compose up -d

docker-down: ## Stop all containers
	docker compose down

demo: ## Run the offline SDK tracing demo (JSONL export)
	$(PYTHON) examples/run_demo.py

clean: ## Remove caches
	$(PYTHON) -c "import shutil, pathlib; [shutil.rmtree(p, ignore_errors=True) for p in pathlib.Path('.').rglob('__pycache__')]; [shutil.rmtree(p, ignore_errors=True) for p in pathlib.Path('.').rglob('.pytest_cache')]; shutil.rmtree('.ruff_cache', ignore_errors=True)"

help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-16s\033[0m %s\n", $$1, $$2}'
