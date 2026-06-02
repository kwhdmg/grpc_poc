"""gRPC client for the Factorizer service.

Demonstrates the client side of all three RPC patterns. Run the Go server
first (see README), then: python client.py
"""
import os
import sys
import time

import grpc

# The generated *_pb2_grpc.py uses a flat `import factorize_pb2`, so the
# generated package dir must be importable. Add it to sys.path.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "gen", "python"))

import factorize_pb2 as pb          # messages
import factorize_pb2_grpc as pb_grpc  # service stub

SERVER_ADDR = "localhost:50051"


def fmt(resp: "pb.FactorizeResponse") -> str:
    """Render 360 -> '2^3 * 3^2 * 5' for readable output."""
    parts = [
        f"{f.prime}^{f.exponent}" if f.exponent > 1 else f"{f.prime}"
        for f in resp.factors
    ]
    return f"{resp.value} = {' * '.join(parts)}  ({resp.elapsed_micros}us)"


def call_unary(stub: "pb_grpc.FactorizerStub") -> None:
    # Unary: build one request, get one response back.
    resp = stub.Factorize(pb.FactorizeRequest(value=360))
    print("[unary]        ", fmt(resp))


def call_server_stream(stub: "pb_grpc.FactorizerStub") -> None:
    # Server streaming: one request, iterate over the response stream.
    req = pb.FactorizeBatchRequest(values=[12, 97, 1_000_000, 9_999_991])
    for resp in stub.FactorizeBatch(req):  # blocks per item until server Sends
        print("[server-stream]", fmt(resp))


def call_bidi_stream(stub: "pb_grpc.FactorizerStub") -> None:
    # Bidirectional: we feed a generator of requests; gRPC sends them as we
    # yield, and we read responses concurrently from the returned iterator.
    def request_iter():
        for v in (84, 17, 2_310, 600_851_475_143):
            yield pb.FactorizeRequest(value=v)
            time.sleep(0.05)  # simulate records trickling in

    for resp in stub.FactorizeStream(request_iter()):
        print("[bidi-stream]  ", fmt(resp))


def main() -> None:
    # insecure_channel = plaintext HTTP/2 (fine for local PoC; use TLS in prod).
    with grpc.insecure_channel(SERVER_ADDR) as channel:
        stub = pb_grpc.FactorizerStub(channel)
        call_unary(stub)
        call_server_stream(stub)
        call_bidi_stream(stub)


if __name__ == "__main__":
    main()

