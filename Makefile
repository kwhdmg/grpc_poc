# Convenience targets. Run from the project root.
.PHONY: gen tidy server client test

gen: ## Regenerate Go + Python stubs from the proto
	bash scripts/gen.sh

tidy: ## Resolve Go module dependencies (fills go.sum)
	go mod tidy

server: ## Build & run the Go gRPC server (listen on :50051)
	go run ./server-go

client: ## Run the Python client (server must already be running)
	python3 client-python/client.py

test: ## Run the pytest suite (builds & launches the Go server itself)
	cd client-python && uv run pytest
