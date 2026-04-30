"""Verify that streaming HTTP calls do not inherit the global request timeout.

The non-streaming `timeout` is meant to bound short JSON requests. SSE streams
can run for many minutes (the agent run itself drives the response duration);
the stream client must therefore use a no-read-timeout configuration so a
slow-streaming endpoint does not raise `ReadTimeout` mid-stream.
"""

from __future__ import annotations

import http.server
import socket
import threading
import time
from collections.abc import Iterator

import httpx
import pytest

from ai_sdk._http import AsyncHTTPClient, HTTPClient
from ai_sdk.auth import TokenAuth


def _free_port() -> int:
    """Return an OS-assigned free TCP port on localhost."""
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


class _SlowSSEHandler(http.server.BaseHTTPRequestHandler):
    """HTTP handler that emits SSE events spread over ~2 seconds."""

    # Configurable on the server instance to keep the test fast but slower than `timeout`.
    pre_event_delay: float = 1.5
    inter_event_delay: float = 0.3

    def do_POST(self) -> None:
        # Build the payload up-front so we can advertise a Content-Length,
        # which lets httpx detect a clean end-of-stream regardless of how
        # the underlying socket is torn down at test teardown.
        payload = (
            b'event: message\ndata: {"content": "first"}\n\n'
            b'event: message\ndata: {"content": "second"}\n\n'
        )
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Connection", "close")
        self.end_headers()
        # Wait long enough that a 1s read timeout would fire BEFORE the first
        # byte of the body arrives. Swallow connection errors when the client
        # has already moved on (test teardown closes the connection).
        try:
            time.sleep(self.pre_event_delay)
            self.wfile.write(payload[: len(payload) // 2])
            self.wfile.flush()
            time.sleep(self.inter_event_delay)
            self.wfile.write(payload[len(payload) // 2 :])
            self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            return

    def log_message(self, *args: object) -> None:  # type: ignore[override]
        # Silence default logging during tests.
        return


@pytest.fixture
def slow_sse_server() -> Iterator[str]:
    """Spawn a localhost HTTP server that emits SSE events slowly."""
    port = _free_port()
    server = http.server.ThreadingHTTPServer(("127.0.0.1", port), _SlowSSEHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{port}"
    finally:
        server.shutdown()
        server.server_close()


def _collect_content(chunks: Iterator[bytes]) -> bytes:
    """Concatenate streamed chunks into one bytes object."""
    return b"".join(chunks)


class TestSyncStreamTimeout:
    """Sync streaming should ignore the configured (short) request timeout."""

    def test_post_stream_completes_despite_short_timeout(self, slow_sse_server: str) -> None:
        client = HTTPClient(
            base_url=slow_sse_server,
            auth=TokenAuth("test-token"),
            timeout=1.0,
            max_retries=0,
        )
        try:
            body = _collect_content(client.post_stream("/", json={}))
        finally:
            client.close()

        assert b'"first"' in body
        assert b'"second"' in body

    def test_non_stream_post_does_use_short_timeout(self, slow_sse_server: str) -> None:
        """Sanity check: non-streaming POST against the same slow endpoint
        DOES time out — confirming the streaming path is the special case,
        not the server."""
        client = HTTPClient(
            base_url=slow_sse_server,
            auth=TokenAuth("test-token"),
            timeout=1.0,
            max_retries=0,
        )
        try:
            with pytest.raises(httpx.ReadTimeout):
                client.post("/", json={})
        finally:
            client.close()


class TestAsyncStreamTimeout:
    """Async streaming should also ignore the configured (short) request timeout."""

    @pytest.mark.asyncio
    async def test_post_stream_completes_despite_short_timeout(self, slow_sse_server: str) -> None:
        client = AsyncHTTPClient(
            base_url=slow_sse_server,
            auth=TokenAuth("test-token"),
            timeout=1.0,
            max_retries=0,
        )
        try:
            chunks: list[bytes] = []
            async for chunk in client.post_stream("/", json={}):
                chunks.append(chunk)
        finally:
            await client.close()

        body = b"".join(chunks)
        assert b'"first"' in body
        assert b'"second"' in body
