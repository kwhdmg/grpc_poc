#!/usr/bin/env bash
# Regenerates Go + Python stubs from proto/factorize.proto.
# Run from the project root: bash scripts/gen.sh
set -euo pipefail
cd "$(dirname "$0")/.."

# Python (uses grpcio-tools; pip install -r client-python/requirements.txt)
python3 -m grpc_tools.protoc -I proto \
  --python_out=gen/python \
  --grpc_python_out=gen/python \
  proto/factorize.proto

# Go (needs protoc + protoc-gen-go + protoc-gen-go-grpc on PATH; see README)
protoc -I proto \
  --go_out=. --go_opt=module=example.com/grpc_poc \
  --go-grpc_out=. --go-grpc_opt=module=example.com/grpc_poc \
  proto/factorize.proto

echo "Stubs regenerated."
