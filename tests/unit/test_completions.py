"""Language-model client."""

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from uuid import uuid4

import pytest

from nexo_ai.domain.retrieval import CompletionFailed, CompletionNotConfigured, SourceReference
from nexo_ai.infrastructure.completions.openai import (
    OpenAICompletionClient,
    UnconfiguredCompletionClient,
    build_completion_client,
)
from tests.conftest import build_settings

_API_KEY = "local-completion-key"


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
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


def _client(server: _Server) -> OpenAICompletionClient:
    address = server.server_address
    host = address[0]
    port = address[1]
    if isinstance(host, bytes):
        host = host.decode("ascii")
    return OpenAICompletionClient(
        api_key=_API_KEY,
        base_url=f"http://{host}:{port}",
        model="gpt-4o-mini",
        timeout=2,
        max_tokens=80,
    )


def _source() -> SourceReference:
    return SourceReference(
        document_id=uuid4(),
        filename="contrato.md",
        position=1,
        content="O prazo é de 30 dias.",
        distance=0.1,
    )


def _body(content: str) -> bytes:
    return json.dumps({"choices": [{"message": {"content": content}}]}).encode()


def test_client_sends_sources_and_hides_the_key(capsys: pytest.CaptureFixture[str]) -> None:
    server = _serve(200, _body("  Resposta com fonte.  "))
    source = _source()
    try:
        text = _client(server).complete(question="qual o prazo?", references=[source])
    finally:
        server.shutdown()
    assert text == "Resposta com fonte."
    assert server.authorizations == [f"Bearer {_API_KEY}"]
    payload = json.loads(server.payloads[0])
    assert payload["model"] == "gpt-4o-mini"
    assert payload["temperature"] == 0
    user = payload["messages"][1]["content"]
    assert "contrato.md" in user
    assert "O prazo é de 30 dias." in user
    assert "qual o prazo?" in user
    assert _API_KEY not in capsys.readouterr().out + capsys.readouterr().err


def test_client_hides_provider_failures() -> None:
    server = _serve(500, json.dumps({"error": _API_KEY}).encode())
    try:
        with pytest.raises(CompletionFailed, match="falhou") as caught:
            _client(server).complete(question="prazo", references=[_source()])
    finally:
        server.shutdown()
    assert _API_KEY not in str(caught.value)
    assert caught.value.__cause__ is None

    empty = _serve(200, _body("  "))
    try:
        with pytest.raises(CompletionFailed, match="vazia"):
            _client(empty).complete(question="prazo", references=[_source()])
    finally:
        empty.shutdown()

    invalid = _serve(200, b"{}")
    try:
        with pytest.raises(CompletionFailed, match="inválida"):
            _client(invalid).complete(question="prazo", references=[_source()])
    finally:
        invalid.shutdown()


def test_unreachable_provider_and_missing_key() -> None:
    client = OpenAICompletionClient(
        api_key=_API_KEY,
        base_url="http://127.0.0.1:1",
        model="gpt-4o-mini",
        timeout=0.2,
        max_tokens=80,
    )
    with pytest.raises(CompletionFailed, match="falhou") as caught:
        client.complete(question="prazo", references=[_source()])
    assert caught.value.__cause__ is None
    assert client.complete(question="", references=()) == ""
    with pytest.raises(CompletionFailed, match="URL"):
        OpenAICompletionClient(
            api_key=_API_KEY,
            base_url="ftp://example.test",
            model="gpt-4o-mini",
            timeout=1,
            max_tokens=10,
        )
    missing = build_completion_client(build_settings())
    assert isinstance(missing, UnconfiguredCompletionClient)
    with pytest.raises(CompletionNotConfigured, match="não está configurado"):
        missing.complete(question="", references=())
    configured = build_completion_client(build_settings(completion_api_key=_API_KEY))
    assert isinstance(configured, OpenAICompletionClient)
