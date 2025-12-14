.PHONY: help install test lint dev docker-build docker-push docker-run-prod

help:
	@echo "Available targets:"
	@echo "  install        - Install dependencies"
	@echo "  test           - Run all tests"
	@echo "  lint           - Run linters"
	@echo "  dev            - Start development servers"
	@echo "  docker-build   - Build all Docker images"
	@echo "  docker-push    - Push images to registry"
	@echo "  docker-run-prod - Run production compose"

install:
	uv sync --all-extras
	cd web && npm ci

test:
	uv run pytest tests/ -v
	cd web && npm test -- --run

lint:
	uv run ruff check .
	uv run mypy packages/
	cd web && npm run lint

dev:
	@echo "Starting development servers..."
	uv run uvicorn medanki_api.main:app --reload &
	cd web && npm run dev

docker-build:
	docker build -f docker/Dockerfile.api -t medanki-api:latest .
	docker build -f docker/Dockerfile.web -t medanki-web:latest .

docker-push:
	docker push medanki-api:latest
	docker push medanki-web:latest

docker-run-prod:
	docker compose -f docker/docker-compose.prod.yml up -d
