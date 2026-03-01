.PHONY: help infra-up infra-down dev-up dev-down logs test lint fmt

help:
	@echo "Available targets:"
	@echo "  infra-up    Start infrastructure (Qdrant, Redis, Postgres, Redpanda, Ollama)"
	@echo "  infra-down  Stop infrastructure"
	@echo "  dev-up      Start full dev stack"
	@echo "  dev-down    Stop full dev stack"
	@echo "  logs        Tail logs (usage: make logs svc=qdrant)"
	@echo "  test        Run all tests"
	@echo "  lint        Run ruff linter"
	@echo "  fmt         Run ruff formatter"

infra-up:
	docker compose -f infrastructure/docker/docker-compose.infra.yml up -d
	@echo "Waiting for services to be healthy..."
	@sleep 5
	@docker compose -f infrastructure/docker/docker-compose.infra.yml ps

infra-down:
	docker compose -f infrastructure/docker/docker-compose.infra.yml down

infra-reset:
	docker compose -f infrastructure/docker/docker-compose.infra.yml down -v

logs:
	docker compose -f infrastructure/docker/docker-compose.infra.yml logs -f $(svc)

test:
	uv run pytest services/ -v

lint:
	uv run ruff check services/ shared/

fmt:
	uv run ruff format services/ shared/

setup:
	./infrastructure/scripts/setup.sh