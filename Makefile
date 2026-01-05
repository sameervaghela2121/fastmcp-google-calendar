# Chime Labs MCP Servers Makefile

.PHONY: help install install-dev sync test lint format check clean run-google-calendar

help: ## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install production dependencies
	uv sync --no-dev

install-dev: ## Install all dependencies including development tools
	uv sync --all-extras

sync: ## Sync dependencies (equivalent to install-dev)
	uv sync --all-extras

test: ## Run tests
	uv run pytest

test-cov: ## Run tests with coverage
	uv run pytest --cov=shared_utils --cov=google_calendar --cov-report=html --cov-report=term

lint: ## Run linting (ruff + mypy)
	uv run ruff check .
	uv run mypy .

format: ## Format code with black and ruff
	uv run black .
	uv run ruff check --fix .

check: ## Run all checks (lint + test)
	$(MAKE) lint
	$(MAKE) test

clean: ## Clean build artifacts and cache
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf .ruff_cache/
	rm -rf htmlcov/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

run-google-calendar: ## Run the Google Calendar MCP server
	cd servers/google-calendar && python run.py

run-server: ## Run a specific server (usage: make run-server SERVER=google-calendar)
	python run.py $(SERVER)

docker-build-google-calendar: ## Build Docker image for Google Calendar server
	cd servers/google-calendar && docker build -t google-calendar-server .

docker-run-google-calendar: ## Run Google Calendar server in Docker
	docker run -p 8000:8000 google-calendar-server

# Development helpers
dev-setup: install-dev ## Set up development environment
	@echo "Development environment ready!"
	@echo "Run 'make help' to see available commands"

pre-commit: format lint test ## Run pre-commit checks
	@echo "Pre-commit checks completed successfully!"
