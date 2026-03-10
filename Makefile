.PHONY: help infra-up infra-down infra-reset logs \
        query ingestion worker \
        ingest-sample token \
        eval-golden eval-ragas eval-latency \
        test lint fmt setup

help:
	@echo ""
	@echo "Infrastructure:"
	@echo "  make infra-up        Start all infrastructure containers"
	@echo "  make infra-down      Stop infrastructure"
	@echo "  make infra-reset     Stop and delete all volumes (full wipe)"
	@echo "  make logs svc=NAME   Tail logs for a container (e.g. svc=rag-qdrant)"
	@echo ""
	@echo "Services:"
	@echo "  make query           Start query service (port 8001)"
	@echo "  make ingestion       Start ingestion service (port 8002)"
	@echo "  make worker          Start worker service"
	@echo ""
	@echo "Dev helpers:"
	@echo "  make token           Print a JWT token for dev-key-1"
	@echo "  make ingest-sample   Ingest sample Wikipedia categories"
	@echo ""
	@echo "Evaluation:"
	@echo "  make eval-golden     Generate golden Q&A dataset"
	@echo "  make eval-ragas      Run RAGAS evaluation"
	@echo "  make eval-latency    Run latency benchmark"
	@echo ""
	@echo "Code quality:"
	@echo "  make lint            Run ruff linter"
	@echo "  make fmt             Run ruff formatter"
	@echo "  make test            Run all tests"
	@echo ""

# --- Infrastructure ---

infra-up:
	docker compose -f infrastructure/docker/docker-compose.infra.yml up -d
	@echo "Waiting for services to be healthy..."
	@sleep 5
	@chmod +x infrastructure/scripts/init_topics.sh
	@./infrastructure/scripts/init_topics.sh
	@chmod +x infrastructure/scripts/init_qdrant.sh
	@./infrastructure/scripts/init_qdrant.sh
	@docker compose -f infrastructure/docker/docker-compose.infra.yml ps

infra-down:
	docker compose -f infrastructure/docker/docker-compose.infra.yml down

infra-reset:
	docker compose -f infrastructure/docker/docker-compose.infra.yml down -v

logs:
	docker compose -f infrastructure/docker/docker-compose.infra.yml logs -f $(svc)

# --- Services ---

query:
	cd services/query && uv run uvicorn src.main:app --port 8001 --reload

ingestion:
	cd services/ingestion && uv run uvicorn src.main:app --port 8002 --reload

worker:
	cd services/worker && uv run python -m src.main

# --- Dev helpers ---

token:
	@curl -s -X POST http://localhost/v1/auth/token \
		-H "Content-Type: application/json" \
		-d '{"api_key": "dev-key-1"}' | python3 -c \
		"import sys,json; print(json.load(sys.stdin)['access_token'])"

ingest-sample:
	curl -s -X POST http://localhost/v1/ingest/category \
		-H "Content-Type: application/json" \
		-d '{"category": "Distributed computing", "limit": 20}'
	curl -s -X POST http://localhost/v1/ingest/category \
		-H "Content-Type: application/json" \
		-d '{"category": "Consensus algorithms", "limit": 10}'
	curl -s -X POST http://localhost/v1/ingest/category \
		-H "Content-Type: application/json" \
		-d '{"category": "Database management systems", "limit": 10}'

# --- Evaluation ---

eval-golden:
	cd evals && uv run python datasets/generate_golden_set.py \
		--token "$$(make token 2>/dev/null)" \
		--output datasets/candidates.json

eval-ragas:
	cd evals && uv run python runners/ragas_eval.py \
		--token "$$(make token 2>/dev/null)" \
		--golden datasets/candidates.json \
		--output results/ragas_$$(date +%Y%m%d_%H%M%S).csv

eval-latency:
	cd evals && uv run python runners/latency_bench.py \
		--token "$$(make token 2>/dev/null)" \
		--rounds 3 \
		--output results/latency_$$(date +%Y%m%d_%H%M%S).csv

# --- Code quality ---

test:
	uv run pytest services/ -v

lint:
	uv run ruff check services/ shared/

fmt:
	uv run ruff format services/ shared/

setup:
	./infrastructure/scripts/setup.sh
