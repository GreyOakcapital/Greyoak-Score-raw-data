.PHONY: setup run run-bg stop clean test lint fmt logs shell-api shell-db help validate-config

setup: ## Install dependencies and pre-commit hooks
	@echo "📦 Installing dependencies..."
	pip install --upgrade pip
	pip install -r requirements.txt -r requirements-dev.txt
	@echo "🔗 Installing pre-commit hooks..."
	pre-commit install
	@echo "✅ Setup complete! Run 'make help' to see available commands."

run: ## Start docker-compose services
	@echo "🚀 Starting GreyOak Score Engine..."
	docker-compose up --build

run-bg: ## Start services in background
	@echo "🚀 Starting services in background..."
	docker-compose up -d --build
	@echo "✅ Services running. View logs: make logs"

stop: ## Stop docker-compose services
	@echo "🛑 Stopping services..."
	docker-compose down

clean: ## Stop services and remove volumes
	@echo "🧹 Cleaning up (removing volumes)..."
	docker-compose down -v

test: ## Run tests with coverage
	@echo "🧪 Running tests..."
	pytest

lint: ## Run linters (black, ruff, mypy)
	@echo "🔍 Running linters..."
	@echo "Checking code formatting (black)..."
	black --check .
	@echo "Checking code quality (ruff)..."
	ruff check .
	@echo "Checking types (mypy)..."
	mypy .

fmt: ## Format code (black + ruff auto-fix)
	@echo "✨ Formatting code..."
	black .
	ruff check --fix .
	@echo "✅ Code formatted!"

validate-config: ## Validate YAML configuration files
	@echo "✅ Validating configuration files..."
	python scripts/validate_config.py

logs: ## Tail API logs
	docker-compose logs -f api

shell-api: ## Shell into API container
	docker exec -it greyoak-api bash

shell-db: ## Shell into DB container
	docker exec -it greyoak-db psql -U greyoak -d greyoak_scores

help: ## Show this help
	@echo "GreyOak Score Engine - Available Commands:"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

.DEFAULT_GOAL := help
