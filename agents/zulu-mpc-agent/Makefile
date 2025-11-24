.PHONY: help install init test lint format clean run health

help:
	@echo "ZULU MPC Agent - Make Commands"
	@echo ""
	@echo "Setup:"
	@echo "  make install    - Install dependencies"
	@echo "  make init       - Initialize directories and config"
	@echo ""
	@echo "Development:"
	@echo "  make test       - Run tests"
	@echo "  make lint       - Run linters"
	@echo "  make format     - Format code"
	@echo "  make clean      - Clean temporary files"
	@echo ""
	@echo "Operations:"
	@echo "  make run        - Start Ollama and check health"
	@echo "  make health     - Check system health"
	@echo ""

install:
	@echo "Installing dependencies..."
	pip install -r requirements.txt
	pip install -e .
	@echo "Done!"

init:
	@echo "Initializing ZULU agent..."
	python cli.py init
	@echo "Done!"

test:
	@echo "Running tests..."
	pytest tests/ -v --cov=agent_core --cov-report=html
	@echo "Coverage report: htmlcov/index.html"

lint:
	@echo "Running linters..."
	mypy agent_core/
	ruff check agent_core/ cli.py
	@echo "Lint complete!"

format:
	@echo "Formatting code..."
	black agent_core/ cli.py tests/
	ruff check --fix agent_core/ cli.py
	@echo "Format complete!"

clean:
	@echo "Cleaning temporary files..."
	rm -rf __pycache__ .pytest_cache .mypy_cache .coverage htmlcov
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	@echo "Clean complete!"

run:
	@echo "Starting Ollama..."
	@ollama serve > /dev/null 2>&1 &
	@sleep 2
	@echo "Checking model..."
	@ollama list | grep llama3.1 || ollama pull llama3.1:8b
	@make health

health:
	@echo "Checking system health..."
	python cli.py health

# Database operations
db-backup:
	@echo "Backing up database..."
	@mkdir -p data/backups
	@cp data/zulu_agent.db "data/backups/zulu_agent_$(shell date +%Y%m%d_%H%M%S).db"
	@echo "Backup created!"

db-vacuum:
	@echo "Vacuuming database..."
	python -c "from agent_core.memory import SessionStore; SessionStore('./data/zulu_agent.db').vacuum()"
	@echo "Vacuum complete!"

# Example commands
example-process:
	@echo "Processing example audio..."
	python cli.py process examples/sample_call.wav --title "Example Call"

example-list:
	@echo "Listing sessions..."
	python cli.py list -n 5

# Development server (future web interface)
dev:
	@echo "Starting development server..."
	@echo "Not yet implemented - CLI only for now"

# Documentation
docs:
	@echo "Building documentation..."
	@echo "Not yet implemented"
