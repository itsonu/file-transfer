# Developer shortcuts. Run `make help` to list them.
PY ?= .venv/bin/python
BIN := .venv/bin

.DEFAULT_GOAL := help
.PHONY: help setup run dev test e2e cov lint fmt typecheck audit check docker build binary clean

help: ## Show this help
	@awk 'BEGIN {FS = ":.*##"} /^[a-zA-Z_-]+:.*##/ {printf "  \033[36m%-10s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

.venv/.dev-installed: pyproject.toml
	@command -v uv >/dev/null 2>&1 && { [ -x $(PY) ] || uv venv -q .venv; uv pip install -q -p $(PY) -e ".[dev,e2e]"; } \
		|| { [ -x $(PY) ] || python3 -m venv .venv; $(PY) -m pip install -q -e ".[dev,e2e]"; }
	@$(BIN)/pre-commit install >/dev/null 2>&1 || true
	@touch $@

setup: .venv/.dev-installed ## Install the project with dev tools and git hooks
	@$(PY) -m playwright install chromium >/dev/null 2>&1 || echo "  (Playwright browser not installed — e2e tests will be skipped)"

run: .venv/.dev-installed ## Run the app (pass options with ARGS="--pin")
	$(BIN)/open-transfer $(ARGS)

dev: .venv/.dev-installed ## Run with verbose logging on a scratch folder
	$(BIN)/open-transfer .dev-share --verbose $(ARGS)

test: .venv/.dev-installed ## Unit + API tests
	$(BIN)/pytest -m "not e2e"

e2e: .venv/.dev-installed ## Browser end-to-end tests (Playwright + Chromium)
	$(BIN)/pytest -m e2e

cov: .venv/.dev-installed ## Tests with a coverage report
	$(BIN)/pytest -m "not e2e" --cov --cov-report=term-missing

lint: .venv/.dev-installed ## Lint Python and check JavaScript syntax
	$(BIN)/ruff check .
	$(BIN)/ruff format --check .
	node --check src/open_transfer/static/app.js

fmt: .venv/.dev-installed ## Auto-format and auto-fix
	$(BIN)/ruff format .
	$(BIN)/ruff check --fix .

typecheck: .venv/.dev-installed ## Static type checking
	$(BIN)/mypy

audit: .venv/.dev-installed ## Scan dependencies for known vulnerabilities
	$(BIN)/pip-audit --strict .

check: lint typecheck test e2e ## Everything CI runs

docker: ## Build and run the Docker image
	docker build -t open-transfer .
	docker run --rm -it -p 5000:5000 -v "$$PWD/uploads:/data" open-transfer

build: .venv/.dev-installed ## Build wheel and sdist into dist/
	$(PY) -m pip install -q build && $(PY) -m build

binary: .venv/.dev-installed ## Build a standalone executable with PyInstaller
	$(PY) -m pip install -q pyinstaller && $(BIN)/pyinstaller --noconfirm packaging/open-transfer.spec

clean: ## Remove build artefacts and caches
	rm -rf build dist .pytest_cache .mypy_cache .ruff_cache .coverage htmlcov .dev-share
	find . -name __pycache__ -type d -prune -exec rm -rf {} +
