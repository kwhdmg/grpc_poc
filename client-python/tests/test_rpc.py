"""Contract tests against a live Go server, exercising all three RPC patterns.

These validate both the gRPC wiring and the server's factorization correctness.
They rely on the `grpc_stub` fixture (see conftest.py) and skip if Go is absent.
"""
import factorize_pb2 as pb


def _factors(resp) -> dict:
    """Collapse a response's factor list into a {prime: exponent} dict."""
    return {f.prime: f.exponent for f in resp.factors}


def test_unary_factorize(grpc_stub):
    resp = grpc_stub.Factorize(pb.FactorizeRequest(value=360))
    assert resp.value == 360
    assert _factors(resp) == {2: 3, 3: 2, 5: 1}


def test_server_streaming_batch(grpc_stub):
    req = pb.FactorizeBatchRequest(values=[12, 97, 1_000_000, 9_999_991])
    out = {r.value: _factors(r) for r in grpc_stub.FactorizeBatch(req)}
    assert out == {
        12: {2: 2, 3: 1},
        97: {97: 1},               # prime
        1_000_000: {2: 6, 5: 6},
        9_999_991: {9_999_991: 1},  # prime
    }


def test_bidirectional_stream(grpc_stub):
    values = [84, 17, 2_310, 600_851_475_143]

    def request_iter():
        for v in values:
            yield pb.FactorizeRequest(value=v)

    out = {r.value: _factors(r) for r in grpc_stub.FactorizeStream(request_iter())}
    assert out == {
        84: {2: 2, 3: 1, 7: 1},
        17: {17: 1},
        2_310: {2: 1, 3: 1, 5: 1, 7: 1, 11: 1},
        600_851_475_143: {71: 1, 839: 1, 1_471: 1, 6_857: 1},
    }


def test_one_has_no_prime_factors(grpc_stub):
    # 1 is the empty product: trial division emits nothing.
    resp = grpc_stub.Factorize(pb.FactorizeRequest(value=1))
    assert resp.factors == []


def test_elapsed_micros_is_populated(grpc_stub):
    # A large composite should take measurable (non-negative) compute time.
    resp = grpc_stub.Factorize(pb.FactorizeRequest(value=600_851_475_143))
    assert resp.elapsed_micros >= 0
