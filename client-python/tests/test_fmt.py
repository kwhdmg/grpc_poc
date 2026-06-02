"""Unit tests for client.fmt — the response-rendering helper. No server needed."""
import factorize_pb2 as pb
from client import fmt


def _resp(value, factors, micros=0):
    """Build a FactorizeResponse from (prime, exponent) tuples."""
    return pb.FactorizeResponse(
        value=value,
        factors=[pb.PrimeFactor(prime=p, exponent=e) for p, e in factors],
        elapsed_micros=micros,
    )


def test_single_prime_omits_exponent():
    assert fmt(_resp(97, [(97, 1)])) == "97 = 97  (0us)"


def test_exponents_rendered_with_caret():
    assert fmt(_resp(360, [(2, 3), (3, 2), (5, 1)])) == "360 = 2^3 * 3^2 * 5  (0us)"


def test_all_distinct_primes_have_no_carets():
    out = fmt(_resp(2310, [(2, 1), (3, 1), (5, 1), (7, 1), (11, 1)]))
    assert out == "2310 = 2 * 3 * 5 * 7 * 11  (0us)"


def test_elapsed_micros_included():
    assert fmt(_resp(12, [(2, 2), (3, 1)], micros=7)).endswith("(7us)")


def test_prime_input_factors_to_itself():
    assert fmt(_resp(13, [(13, 1)])) == "13 = 13  (0us)"
