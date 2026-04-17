COMPOSE := docker compose
BACKEND_DIR := backend
BACKEND_VENV := $(CURDIR)/$(BACKEND_DIR)/venv
BACKEND_PYTHON := $(BACKEND_VENV)/bin/python

.PHONY: run down compose-logs backend-setup frontend-setup test dev-backend dev-frontend dev

run:
	$(COMPOSE) up --build

down:
	$(COMPOSE) down

test: backend-setup
	@$(BACKEND_PYTHON) -m pytest -q $(BACKEND_DIR)/test

