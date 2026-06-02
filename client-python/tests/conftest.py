"""Shared pytest fixtures.

`fmt` and the generated `factorize_pb2` are pure-Python and need no server. The
RPC tests need a running Factorizer: the `grpc_stub` fixture builds the Go server,
launches it on :50051, and yields a connected stub. If the Go toolchain is missing
or the build fails, those tests skip rather than fail.
"""
import contextlib
import os
import socket
import subprocess
import sys
from shutil import which

import pytest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
GEN_PY = os.path.join(REPO_ROOT, "gen", "python")
SERVER_HOST = "localhost"
SERVER_PORT = 50051
SERVER_ADDR = f"{SERVER_HOST}:{SERVER_PORT}"

# The generated *_pb2_grpc.py uses a flat `import factorize_pb2`, so the generated
# package dir must be importable before any test imports the stubs.
sys.path.insert(0, GEN_PY)


def _wait_for_port(host: str, port: int, timeout: float = 10.0) -> bool:
    """Poll until a TCP connection to host:port succeeds, or timeout elapses."""
    import time

    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        with contextlib.closing(socket.socket()) as sock:
            sock.settimeout(0.5)
            try:
                sock.connect((host, port))
                return True
            except OSError:
                time.sleep(0.1)
    return False


@pytest.fixture(scope="session")
def grpc_stub():
    """Build + launch the Go server once per session and yield a connected stub."""
    import grpc

    if which("go") is None:
        pytest.skip("go toolchain not on PATH; skipping server integration tests")

    binary = os.path.join(REPO_ROOT, "bin", "factorize-server-test")
    build = subprocess.run(
        ["go", "build", "-o", binary, "./server-go"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    if build.returncode != 0:
        pytest.skip(f"go build failed (run `make gen` first?):\n{build.stderr}")

    proc = subprocess.Popen(
        [binary],
        cwd=REPO_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    try:
        if not _wait_for_port(SERVER_HOST, SERVER_PORT):
            proc.terminate()
            _, stderr = proc.communicate(timeout=5)
            pytest.skip(f"server never opened :{SERVER_PORT}: {stderr.decode()}")

        import factorize_pb2_grpc as pb_grpc

        with grpc.insecure_channel(SERVER_ADDR) as channel:
            grpc.channel_ready_future(channel).result(timeout=5)
            yield pb_grpc.FactorizerStub(channel)
    finally:
        proc.terminate()
        with contextlib.suppress(subprocess.TimeoutExpired):
            proc.wait(timeout=5)
