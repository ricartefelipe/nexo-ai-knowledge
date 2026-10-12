"""Embedding client."""

import json
import threading
from collections.abc import Sequence
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from nexo_ai.domain.documents import EmbeddingFailed, EmbeddingNotConfigured
from nexo_ai.infrastructure.embeddings.openai import (
    OpenAIEmbeddingClient,
    UnconfiguredEmbeddingClient,
    build_embedding_client,
)
from tests.conftest import build_settings

_API_KEY = "local-test-key"


class _Server(ThreadingHTTPServer):
    def __init__(self, response_status: int, response_body: bytes) -> None:
        super().__init__(("127.0.0.1", 0), _Handler)
        self.response_status = response_status
        self.response_body = response_body
        self.authorizations: list[str] = []
        self.payloads: list[bytes] = []


class _Handler(BaseHTTPRequestHandler):
    server: _Server

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", "0"))
        self.server.authorizations.append(self.headers.get("Authorization", ""))
        self.server.payloads.append(self.rfile.read(length))
        body = self.server.response_body
        self.send_response(self.server.response_status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        return


def _serve(status: int, body: bytes) -> _Server:
    server = _Server(status, body)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


def _client(server: _Server, *, dimensions: int = 2) -> OpenAIEmbeddingClient:
    address = server.server_address
    host = address[0]
    port = address[1]
    if isinstance(host, bytes):
        host = host.decode("ascii")
    return OpenAIEmbeddingClient(
        api_key=_API_KEY,
        base_url=f"http://{host}:{port}",
        model="text-embedding-3-small",
        timeout=2,
        dimensions=dimensions,
    )


def _vectors(items: Sequence[tuple[int, list[float]]]) -> bytes:
    return json.dumps(
        {"data": [{"index": index, "embedding": vector} for index, vector in items]}
    ).encode()


def test_client_posts_the_model_and_orders_vectors_without_logging_the_key(
    capsys: pytest.CaptureFixture[str],
) -> None:
    server = _serve(200, _vectors([(1, [0.2, 0.3]), (0, [0.1, 0.4])]))
    try:
        vectors = _client(server).embed(["primeiro", "segundo"])
    finally:
        server.shutdown()
    assert vectors == [[0.1, 0.4], [0.2, 0.3]]
    assert server.authorizations == [f"Bearer {_API_KEY}"]
    payload = json.loads(server.payloads[0])
    assert payload["model"] == "text-embedding-3-small"
    assert payload["input"] == ["primeiro", "segundo"]
    captured = capsys.readouterr()
    assert _API_KEY not in captured.out + captured.err


def test_client_hides_provider_failures(capsys: pytest.CaptureFixture[str]) -> None:
    echoed = json.dumps({"error": _API_KEY}).encode()
    server = _serve(401, echoed)
    try:
        with pytest.raises(EmbeddingFailed, match="falhou") as caught:
            _client(server).embed(["texto"])
    finally:
        server.shutdown()
    assert _API_KEY not in str(caught.value)
    assert caught.value.__cause__ is None
    captured = capsys.readouterr()
    assert _API_KEY not in captured.out + captured.err


def test_client_rejects_invalid_or_mismatched_vectors() -> None:
    invalid = _serve(200, b"{")
    try:
        with pytest.raises(EmbeddingFailed, match="inválida"):
            _client(invalid).embed(["texto"])
    finally:
        invalid.shutdown()

    mismatch = _serve(200, _vectors([(0, [0.1])]))
    try:
        with pytest.raises(EmbeddingFailed, match="dimensão"):
            _client(mismatch, dimensions=2).embed(["texto"])
    finally:
        mismatch.shutdown()

    infinite = _serve(200, _vectors([(0, [float("nan"), 0.2])]))
    try:
        with pytest.raises(EmbeddingFailed, match="inválido"):
            _client(infinite).embed(["texto"])
    finally:
        infinite.shutdown()


def test_empty_input_does_not_call_the_provider() -> None:
    client = OpenAIEmbeddingClient(
        api_key=_API_KEY,
        base_url="http://127.0.0.1:9",
        model="text-embedding-3-small",
        timeout=1,
        dimensions=2,
    )
    assert client.embed(()) == []


def test_client_rejects_a_bad_url_and_an_unreachable_provider() -> None:
    with pytest.raises(EmbeddingFailed, match="URL"):
        OpenAIEmbeddingClient(
            api_key=_API_KEY,
            base_url="ftp://example.test/v1",
            model="text-embedding-3-small",
            timeout=1,
            dimensions=2,
        )
    client = OpenAIEmbeddingClient(
        api_key=_API_KEY,
        base_url="http://127.0.0.1:1",
        model="text-embedding-3-small",
        timeout=0.2,
        dimensions=2,
    )
    with pytest.raises(EmbeddingFailed, match="falhou") as caught:
        client.embed(["texto"])
    assert _API_KEY not in str(caught.value)
    assert caught.value.__cause__ is None


def test_missing_key_builds_an_unconfigured_client() -> None:
    client = build_embedding_client(build_settings())
    assert isinstance(client, UnconfiguredEmbeddingClient)
    with pytest.raises(EmbeddingNotConfigured, match="não está configurado"):
        client.embed(())
    configured = build_embedding_client(build_settings(embedding_api_key=_API_KEY))
    assert isinstance(configured, OpenAIEmbeddingClient)
