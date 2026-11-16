.PHONY: help install run run-api collect init-db test lint format clean

VENV = .venv
PYTHON = $(VENV)/bin/python
PIP = $(VENV)/bin/pip
PYTEST = $(VENV)/bin/pytest
RUFF = $(VENV)/bin/ruff

help:
	@echo "STEM RADAR - Developer Commands"
	@echo "  make install   Install dependencies into virtual environment"
	@echo "  make run       Start the Telegram Bot"
	@echo "  make run-api   Start the FastAPI REST server"
	@echo "  make collect   Run a one-shot multi-source intelligence collection"
	@echo "  make init-db   Initialize database schema and seed STEM categories"
	@echo "  make test      Execute pytest automated test suite"
	@echo "  make lint      Run Ruff static analysis and lint checks"
	@echo "  make format    Auto-format codebase with Ruff"
	@echo "  make clean     Remove cache and temporary build files"

install:
	$(PIP) install -r requirements.txt

run:
	$(PYTHON) bot.py

run-api:
	$(PYTHON) api.py

collect:
	$(PYTHON) bot.py --collect

init-db:
	$(PYTHON) bot.py --init-db

test:
	$(PYTEST) -v

lint:
	$(RUFF) check .

format:
	$(RUFF) check --fix .
	$(RUFF) format .

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".ruff_cache" -exec rm -rf {} +

