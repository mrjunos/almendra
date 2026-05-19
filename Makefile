# almendra — developer task runner
# `make setup` installs everything; the other targets assume an environment
# created by uv. Run `make help` for the full list.

.DEFAULT_GOAL := help
.PHONY: help setup setup-min lint format test info train eval export bench data clean

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

setup: ## Install the project with all extras (torch, onnx, dvc, dev)
	uv sync --all-extras

setup-min: ## Install only core + dev deps (fast; no torch) — enough for lint/test/info
	uv sync --extra dev

lint: ## Run ruff lint + format checks
	uv run ruff check .
	uv run ruff format --check .

format: ## Auto-format the codebase
	uv run ruff format .
	uv run ruff check --fix .

test: ## Run the test suite
	uv run pytest

info: ## Print the canonical taxonomy and project status
	uv run almendra info

data: ## Download the configured public datasets
	uv run python scripts/download_public_datasets.py

ingest: ## Ingest downloaded datasets into data/processed/manifest.jsonl
	uv run almendra ingest

train: ## Train a model (override config: make train ARGS="model=efficientnet_lite0")
	uv run almendra train $(ARGS)

eval: ## Evaluate a trained checkpoint
	uv run almendra eval $(ARGS)

export: ## Export a checkpoint to ONNX (+ INT8) with a parity check
	uv run almendra export $(ARGS)

bench: ## Benchmark inference latency / throughput
	uv run almendra bench $(ARGS)

clean: ## Remove build artifacts, caches and run outputs
	rm -rf outputs mlruns .pytest_cache .ruff_cache dist build
	find . -type d -name __pycache__ -exec rm -rf {} +
