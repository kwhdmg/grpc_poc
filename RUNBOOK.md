# RUNBOOK

Operational guide for the Factorizer gRPC PoC: how to set it up, run it, regenerate
stubs, and recover from the failure modes you're likely to hit. For the conceptual
walkthrough see `README.md`; for repo architecture see `CLAUDE.md`.

## Prerequisites

| Tool | Why | Install (macOS) |
|------|-----|-----------------|
| Go (≥ 1.26) | builds/runs the server | `brew install go` |
| `protoc` | compiles the proto | `brew install protobuf` |
| `protoc-gen-go`, `protoc-gen-go-grpc` | Go stub generation | `go install google.golang.org/protobuf/cmd/protoc-gen-go@latest` and `go install google.golang.org/grpc/cmd/protoc-gen-go-grpc@latest` |
| `uv` | Python deps + runner | `brew install uv` |

The two Go plugins install into `$(go env GOPATH)/bin`. That directory must be on
`PATH` before generating stubs:

```bash
export PATH="$PATH:$(go env GOPATH)/bin"
```

(Add it to your shell profile to make it permanent.)

## First-time setup

From the repo root:

```bash
make gen      # generate Go + Python stubs from proto/factorize.proto
make tidy     # go mod tidy — resolves Go deps, fills go.sum
cd client-python && uv sync && cd ..   # install Python deps into .venv
```

`make gen` must succeed and populate **both** `gen/go/factorizepb/*.pb.go` and
`gen/python/factorize_pb2*.py`. If `gen/go/` is empty afterward, see Troubleshooting.

## Running it

Two terminals, server first.

**Terminal 1 — server:**
```bash
make server          # go run ./server-go
# -> Factorizer gRPC server listening on :50051
```

**Terminal 2 — client:**
```bash
make client          # python3 client-python/client.py
# or: cd client-python && uv run python client.py
```

Expected client output (exercises all three RPC patterns):

```
[unary]         360 = 2^3 * 3^2 * 5  (0us)
[server-stream] 12 = 2^2 * 3
[server-stream] 97 = 97
[server-stream] 1000000 = 2^6 * 5^6
[server-stream] 9999991 = 9999991
[bidi-stream]   84 = 2^2 * 3 * 7
[bidi-stream]   17 = 17
[bidi-stream]   2310 = 2 * 3 * 5 * 7 * 11
[bidi-stream]   600851475143 = 71 * 839 * 1471 * 6857
```

Stop the server with `Ctrl-C`.

## Changing the contract

Any edit to `proto/factorize.proto` requires regeneration and a rebuild:

```bash
make gen        # regenerate both languages
make tidy       # only if new imports were pulled in
```

Then restart the server and re-run the client. The generated stubs in `gen/` are
**not** hand-edited — always regenerate.

When adding an RPC, mind the shape keywords in the proto: a missing `stream` on the
request or response silently changes the RPC type (e.g. server-streaming → unary),
which then fails to match the server handler signature at compile time.

## Building the server binary

`go run ./server-go` and `make server` work as-is. If you want a standalone binary,
do **not** run `go build ./server-go` from the root — it tries to write an output
file named `server-go`, which collides with the directory. Use an explicit output:

```bash
go build -o bin/factorize-server ./server-go
./bin/factorize-server
```

## Troubleshooting

**`scripts/gen.sh`: `protoc-gen-go: program not found`**
The Go plugins aren't on `PATH`. Run `export PATH="$PATH:$(go env GOPATH)/bin"` and
retry. Confirm they're installed with `ls $(go env GOPATH)/bin`.

**`gen/go/` is empty after `make gen`, no error**
The proto's `option go_package` prefix doesn't match `--go_opt=module=` in
`scripts/gen.sh`. Both must be `example.com/grpc_poc`. `protoc-gen-go` silently
skips files whose package falls outside the module prefix.

**Server: `undefined: pb.Factorizer_FactorizeBatchServer` (or similar) at build**
The generated stubs are stale or the RPC's streaming shape in the proto doesn't match
the handler. Re-run `make gen`, then `go build`. `FactorizeBatch` must be declared
`returns (stream FactorizeResponse)` for the streaming server signature to exist.

**Client: `failed to connect to all addresses` / `Connection refused`**
The server isn't running, or isn't on `:50051`. Start Terminal 1 first and confirm it
logged `listening on :50051`. Check nothing else holds the port: `lsof -i :50051`.

**Client: `ModuleNotFoundError: No module named 'factorize_pb2'`**
Python stubs are missing or `gen/python` isn't importable. Run `make gen`; the client
prepends `../gen/python` to `sys.path`, so the files must exist there.

**Client: `ModuleNotFoundError: No module named 'grpc'`**
Python deps aren't installed. Run `uv sync` in `client-python/`, and invoke the client
via `uv run python client.py` (or `make client`) so it uses the project `.venv`.

## Reference

| Item | Value |
|------|-------|
| Server listen address | `:50051` |
| Client target | `localhost:50051` |
| Transport | plaintext HTTP/2 (`insecure_channel`) — use TLS in prod |
| Go module | `example.com/grpc_poc` |
| Proto package | `factorize.v1` |
