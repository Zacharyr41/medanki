.PHONY: install install-dev sync test test-unit test-integration lint format typecheck clean dev dev-api dev-web docker-up docker-down docker-build docker-push docker-run-prod setup-hooks help

# Installation
install:
	uv sync
	cd web && npm ci

install-dev:
	uv sync --all-extras
	cd web && npm ci

sync:
	uv sync --all-extras

# Testing
test:
	uv run pytest tests/ -v
	cd web && npm test -- --run

test-unit:
	uv run pytest tests/unit -v --tb=short

test-integration:
	uv run pytest tests/integration -v --tb=short

test-cov:
	uv run pytest tests/ --cov=medanki --cov-report=html --cov-report=term

# Code quality
lint:
	uv run ruff check .
	uv run mypy packages/
	cd web && npm run lint

lint-fix:
	uv run ruff check --fix .

format:
	uv run ruff format .

typecheck:
	uv run mypy packages/

check: lint typecheck test-unit

# Development servers
dev:
	@echo "Starting development servers..."
	uv run uvicorn medanki_api.main:app --reload &
	cd web && npm run dev

dev-api:
	uv run uvicorn medanki_api.main:app --reload --port 8000

dev-web:
	cd web && npm run dev

# Docker
docker-up:
	docker-compose -f docker/docker-compose.yml up -d

docker-down:
	docker-compose -f docker/docker-compose.yml down

docker-logs:
	docker-compose -f docker/docker-compose.yml logs -f

docker-build:
	docker build -f docker/Dockerfile.api -t medanki-api:latest .
	docker build -f docker/Dockerfile.web -t medanki-web:latest .

docker-push:
	docker push medanki-api:latest
	docker push medanki-web:latest

docker-run-prod:
	docker compose -f docker/docker-compose.prod.yml up -d

# Cleanup
clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .ruff_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name htmlcov -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	rm -rf .coverage coverage.xml

# Setup
setup-hooks:
	chmod +x .claude/hooks/*.sh

setup-scispacy:
	uv run pip install https://s3-us-west-2.amazonaws.com/ai2-s2-scispacy/releases/v0.5.4/en_core_sci_lg-0.5.4.tar.gz

# Help
help:
	@echo "Available targets:"
	@echo "  install        - Install dependencies"
	@echo "  install-dev    - Install with dev dependencies"
	@echo "  test           - Run all tests"
	@echo "  test-unit      - Run unit tests only"
	@echo "  test-integration - Run integration tests"
	@echo "  lint           - Run linter"
	@echo "  format         - Format code"
	@echo "  typecheck      - Run type checker"
	@echo "  dev            - Start all dev servers"
	@echo "  dev-api        - Start FastAPI dev server"
	@echo "  dev-web        - Start React dev server"
	@echo "  docker-up      - Start Docker services"
	@echo "  docker-down    - Stop Docker services"
	@echo "  docker-build   - Build all Docker images"
	@echo "  docker-push    - Push images to registry"
	@echo "  docker-run-prod - Run production compose"
	@echo "  clean          - Clean build artifacts"
