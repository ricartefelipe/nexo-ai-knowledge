"""OpenAI-compatible embedding client."""

import json
import math
import urllib.error
import urllib.request
from collections.abc import Sequence
from urllib.parse import urlsplit

from nexo_ai.config.settings import Settings
from nexo_ai.domain.documents import EmbeddingFailed, EmbeddingNotConfigured

EMBEDDING_DIMENSIONS = 1536
_BATCH_SIZE = 64


class UnconfiguredEmbeddingClient:
    """Reject embedding calls when no provider key was configured."""

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        raise EmbeddingNotConfigured("O provedor de embeddings não está configurado.")


class OpenAIEmbeddingClient:
    """Call an OpenAI-compatible `/embeddings` endpoint."""

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        model: str,
        timeout: float,
        dimensions: int,
    ) -> None:
        parsed = urlsplit(base_url)
        if parsed.scheme not in {"http", "https"} or parsed.netloc == "":
            raise EmbeddingFailed("A URL do provedor de embeddings é inválida.")
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._timeout = timeout
        self._dimensions = dimensions

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        if not texts:
            return []
        vectors: list[list[float]] = []
        for start in range(0, len(texts), _BATCH_SIZE):
            vectors.extend(self._embed_batch(list(texts[start : start + _BATCH_SIZE])))
        return vectors

    def _embed_batch(self, texts: list[str]) -> list[list[float]]:
        payload = json.dumps({"model": self._model, "input": texts}).encode("utf-8")
        request = urllib.request.Request(  # noqa: S310
            f"{self._base_url}/embeddings",
            data=payload,
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self._timeout) as response:  # noqa: S310
                raw = response.read()
        except urllib.error.HTTPError as exc:
            exc.read()
            raise EmbeddingFailed("O provedor de embeddings falhou.") from None
        except urllib.error.URLError:
            raise EmbeddingFailed("O provedor de embeddings falhou.") from None
        return _parse_embeddings(raw, expected_count=len(texts), dimensions=self._dimensions)


def build_embedding_client(
    settings: Settings,
) -> OpenAIEmbeddingClient | UnconfiguredEmbeddingClient:
    """Use the configured provider, or a client that fails only when ingestion asks for it."""

    if settings.embedding_api_key == "":
        return UnconfiguredEmbeddingClient()
    return OpenAIEmbeddingClient(
        api_key=settings.embedding_api_key,
        base_url=settings.embedding_base_url,
        model=settings.embedding_model,
        timeout=settings.embedding_timeout,
        dimensions=EMBEDDING_DIMENSIONS,
    )


def _parse_embeddings(raw: bytes, *, expected_count: int, dimensions: int) -> list[list[float]]:
    try:
        body = json.loads(raw)
        data = body["data"]
        ordered = sorted(data, key=lambda item: int(item["index"]))
        vectors = [[float(value) for value in item["embedding"]] for item in ordered]
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        raise EmbeddingFailed("O provedor de embeddings devolveu uma resposta inválida.") from None
    if len(vectors) != expected_count or any(len(vector) != dimensions for vector in vectors):
        raise EmbeddingFailed("O provedor de embeddings devolveu um vetor com dimensão inesperada.")
    if any(not math.isfinite(value) for vector in vectors for value in vector):
        raise EmbeddingFailed("O provedor de embeddings devolveu um vetor inválido.")
    return vectors
