# gRPC PoC — Prime Factorization (Go server ↔ Python client)

A minimal but complete cross-language gRPC proof of concept. One `.proto`
contract drives a **Go server** and a **Python client**, demonstrating the
three RPC patterns you'll reuse in an ETL engine.

```
grpc_poc/
├── proto/factorize.proto        # the contract (single source of truth)
├── gen/go/factorizepb/          # generated Go stubs  (do not edit)
├── gen/python/                  # generated Python stubs (do not edit)
├── server-go/main.go            # Go implementation of the service
├── client-python/client.py      # Python caller
├── scripts/gen.sh               # regenerate stubs from the proto
├── go.mod                       # Go module definition
└── Makefile                     # gen / tidy / server / client
```

## Mental model

gRPC = **Protocol Buffers (the data + contract)** + **HTTP/2 (the transport)**.
You describe a *service* and its *messages* once in a `.proto` file; a code
generator (`protoc`) emits typed client/server code in every language. The
client calls a remote method as if it were local; gRPC handles serialization,
framing, and the HTTP/2 streams underneath.

Why it fits an optimized ETL engine: binary Protobuf is far smaller/faster than
JSON, the contract is strongly typed and versionable, and **streaming** lets you
push records through a pipeline with built-in backpressure instead of polling.

---

## Step 1 — The contract (`proto/factorize.proto`)

Defines one service with three methods and the messages they exchange. The
method *shapes* are the whole point:

| RPC               | Shape                       | ETL analogy                         |
|-------------------|-----------------------------|-------------------------------------|
| `Factorize`       | unary (1 req → 1 resp)      | transform a single record           |
| `FactorizeBatch`  | server-streaming (1 → many) | one trigger fans out many results   |
| `FactorizeStream` | bidirectional (many ↔ many) | continuous in/out pipeline          |

`option go_package` controls the Go import path — change `example.com/grpc_poc`
to your real module path if you publish it.

## Step 2 — Install the toolchain

```bash
# protoc compiler
#   macOS:  brew install protobuf
#   Ubuntu: apt-get install -y protobuf-compiler

# Go plugins (go installs them into $GOBIN / $(go env GOPATH)/bin — add to PATH)
go install google.golang.org/protobuf/cmd/protoc-gen-go@latest
go install google.golang.org/grpc/cmd/protoc-gen-go-grpc@latest
export PATH="$PATH:$(go env GOPATH)/bin"

# Python tooling
pip install -r client-python/requirements.txt
```

## Step 3 — Generate the stubs

```bash
bash scripts/gen.sh        # or: make gen
```

This produces `gen/go/factorizepb/*.pb.go` (messages + client/server interfaces)
and `gen/python/factorize_pb2*.py`. You never hand-write these; regenerate them
whenever the proto changes. The Go server only has to implement the generated
`FactorizerServer` interface; the Python client gets a ready-made `FactorizerStub`.

## Step 4 — Resolve Go dependencies

```bash
go mod tidy                # or: make tidy  — fills go.sum from go.mod
```

## Step 5 — Run it

Terminal 1 (server):
```bash
go run ./server-go         # or: make server
# -> Factorizer gRPC server listening on :50051
```

Terminal 2 (client):
```bash
python3 client-python/client.py     # or: make client
```

Expected output:
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

---

## How a call flows (unary example)

1. Client calls `stub.Factorize(FactorizeRequest(value=360))`.
2. gRPC serializes the message to Protobuf bytes, opens an HTTP/2 stream to
   `/factorize.v1.Factorizer/Factorize`, and sends them.
3. Server's generated handler deserializes into a `*FactorizeRequest`, calls your
   `Factorize` method, gets a `*FactorizeResponse` back.
4. Response is serialized and streamed back; the client deserializes and returns
   a typed object. To your code it looked like a normal function call.

Streaming RPCs work the same way but keep the HTTP/2 stream open: the server
calls `stream.Send(...)` repeatedly (server-streaming), or both sides loop on
`Send`/`Recv` independently (bidirectional) until one closes its half.

## Notes for the ETL engine on Azure Functions

- **Transport security:** this PoC uses `insecure_channel` (plaintext). In prod
  use TLS (`grpc.secure_channel` + credentials).
- **Azure Functions caveat:** the Functions HTTP trigger does not expose raw
  HTTP/2, so you typically *won't* host a long-lived gRPC server inside a
  Function. Common patterns instead: (a) Function acts as a gRPC **client** to a
  backend gRPC service (e.g. on Container Apps / AKS, which support HTTP/2), or
  (b) use gRPC only for internal service-to-service hops and keep the Function
  trigger HTTP/queue-based. Validate the hosting model before committing.
- **Streaming = backpressure:** prefer server-/bidi-streaming for record
  pipelines so memory stays bounded vs. materializing whole batches.

