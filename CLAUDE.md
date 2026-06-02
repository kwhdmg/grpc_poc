# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A cross-language gRPC proof of concept: a single `.proto` contract (`proto/factorize.proto`) drives a **Go server** (`server-go/`) and a **Python client** (`client-python/`). The domain (prime factorization) is incidental — the point is to demonstrate the three gRPC interaction patterns (unary, server-streaming, bidirectional) intended for reuse in an ETL engine. See `README.md` for the conceptual walkthrough.

## Architecture

The `.proto` is the single source of truth. Everything else is generated from it or implements its interfaces:

- `proto/factorize.proto` — service + message definitions. Edit this, then regenerate.
- `gen/go/factorizepb/` and `gen/python/` — **generated stubs, do not hand-edit.** Regenerate after any proto change.
- `server-go/main.go` — implements `pb.FactorizerServer`. Domain logic (`factorize`/`compute`) is separate from the three RPC handlers (`Factorize`, `FactorizeBatch`, `FactorizeStream`). Embeds `UnimplementedFactorizerServer` for forward compatibility. Listens on `:50051`.
- `client-python/client.py` — `FactorizerStub` caller exercising all three patterns. It prepends `../gen/python` to `sys.path` because the generated `*_pb2_grpc.py` uses a flat `import factorize_pb2`.

The three RPC shapes are the reusable lesson: unary (1→1, single-record transform), server-streaming (1→many, fan-out), bidirectional (many↔many, continuous pipeline with backpressure).

## Common commands

```bash
make gen      # regenerate Go + Python stubs from the proto (bash scripts/gen.sh)
make tidy     # go mod tidy — resolve Go deps / fill go.sum
make server   # go run ./server-go  (listens on :50051)
make client   # python3 client-python/client.py  (server must be running first)
```

Run the server and client in two separate terminals. There is no test suite.

### Python environment

The Python client uses **uv** (`uv.lock`, `pyproject.toml`, `.venv/`), not pip/requirements.txt. Use `uv sync` to install deps and `uv run python client.py` (from `client-python/`) if not relying on the Makefile. Note: `scripts/gen.sh` and `README.md` still reference a non-existent `client-python/requirements.txt` — ignore those; the real dependency source is `pyproject.toml`.

## Regenerating stubs

`make gen` runs both generators. The Python half (`grpc_tools.protoc`) works out of the box. The Go half requires `protoc`, `protoc-gen-go`, and `protoc-gen-go-grpc` on `PATH` (see README Step 2 for install).

**Known gotcha:** the proto's `option go_package` reads `example.com/gprc_poc/...` (typo: `gprc`), while the Go module and `gen.sh`'s `--go_opt=module=` use `example.com/grpc_poc` (`grpc`). The mismatched module prefix makes `protoc-gen-go` fail to emit Go stubs — which is why `gen/go/` is currently empty. Fix the typo in `proto/factorize.proto` to match the module path before regenerating Go code.
