# Makefile for AI Inference Project

.PHONY: help build up down restart logs clean test health

help: ## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

build: ## Build all Docker images
	@echo "Building Docker images..."
	docker-compose build

up: ## Start all services
	@echo "Starting services..."
	docker-compose up -d

down: ## Stop all services
	@echo "Stopping services..."
	docker-compose down

restart: down up ## Restart all services

logs: ## Show logs from all services
	docker-compose logs -f

logs-coordinator: ## Show coordinator logs
	docker-compose logs -f coordinator

logs-workers: ## Show worker logs
	docker-compose logs -f worker-bert worker-mobilenet worker-clip

clean: ## Clean up containers and images
	@echo "Cleaning up..."
	docker-compose down -v --remove-orphans
	docker system prune -f

test: ## Run tests
	@echo "Running tests..."
	docker-compose --profile testing up --build tester

health: ## Check service health
	@echo "Checking service health..."
	@curl -s http://localhost:8000/health | python -m json.tool || echo "Coordinator not responding"

scale-workers: ## Scale workers (usage: make scale-workers WORKERS=3)
	@echo "Scaling workers to $(WORKERS) instances..."
	docker-compose up -d --scale worker-bert=$(WORKERS) --scale worker-mobilenet=$(WORKERS) --scale worker-clip=$(WORKERS)

dev: ## Development mode - build and start with logs
	docker-compose up --build

prod: ## Production mode - build and start in background
	docker-compose up --build -d
	@echo "Services started in production mode"
	@echo "Check status: make health"
	@echo "View logs: make logs"