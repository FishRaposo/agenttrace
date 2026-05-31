PYTHON	:= python
PIP		:= pip
NPM		:= npm

.PHONY: help demo install test lint format clean setup sdk-test server-test dashboard-test dev

help:
	@echo "AgentTrace - Available targets:"
	@echo ""
	@echo "  demo            Quick demo: start services, run sample trace"
	@echo "  install         Install all dependencies (SDK + Server + Dashboard)"
	@echo "  test            Run all tests"
	@echo "  sdk-test        Run SDK tests"
	@echo "  server-test     Run server tests"
	@echo "  dashboard-test  Run dashboard Playwright tests"
	@echo "  lint            Run ruff + mypy on Python code"
	@echo "  format          Run ruff format"
	@echo "  clean           Remove build artifacts and caches"
	@echo "  setup           First-time setup"
	@echo "  dev             Start docker compose"

install:
	cd sdk && $(PIP) install -e ".[dev]"
	cd server && $(PIP) install -e ".[dev]"
	cd dashboard && $(NPM) install

test: sdk-test server-test

sdk-test:
	cd sdk && $(PYTHON) -m pytest tests/ -v

server-test:
	cd server && $(PYTHON) -m pytest tests/ -v

dashboard-test:
	cd dashboard && npx playwright test --project=chromium

lint:
	cd sdk && ruff check . && mypy agenttrace
	cd server && ruff check . && mypy app

format:
	cd sdk && ruff format .
	cd server && ruff format .

clean:
	$(PYTHON) -c "import shutil, glob; dirs = glob.glob('**/__pycache__', recursive=True) + glob.glob('**/.pytest_cache', recursive=True) + glob.glob('**/*.egg-info', recursive=True); [shutil.rmtree(d) for d in dirs if __import__('pathlib').Path(d).exists()]"
	rm -rf dashboard/.next dashboard/node_modules/.cache

setup: install
	cd server && alembic upgrade head

demo:
	@echo "🚀 Starting AgentTrace demo..."
	docker compose up -d
	@echo "⏳ Waiting for services..."
	@sleep 3
	@echo "📊 Running sample trace..."
	cd examples && $(PYTHON) research_agent.py || true
	@echo "✅ Demo ready!"
	@echo "   Dashboard: http://localhost:3000"
	@echo "   API:       http://localhost:8000"
	@echo ""
	@echo "To stop: docker compose down"

dev:
	docker compose up -d
