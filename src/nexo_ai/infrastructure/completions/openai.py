"""OpenAI-compatible chat completion client."""

import json
import urllib.error
import urllib.request
from collections.abc import Sequence
from urllib.parse import urlsplit

from nexo_ai.config.settings import Settings
from nexo_ai.domain.retrieval import CompletionFailed, CompletionNotConfigured, SourceReference

_SYSTEM_PROMPT = (
    "Responda em português usando somente as fontes numeradas. "
    "Se as fontes não contiverem a resposta, diga que as fontes não respondem. "
    "Não invente fatos. Cite cada fonte usada com o número entre colchetes, como [1]; "
    "uma resposta sem citação será tratada como não sustentada."
)


class UnconfiguredCompletionClient:
    """Reject completion calls when no language-model key was configured."""

    def complete(self, *, question: str, references: Sequence[SourceReference]) -> str:
        raise CompletionNotConfigured("O provedor de linguagem não está configurado.")


class OpenAICompletionClient:
    """Call an OpenAI-compatible `/chat/completions` endpoint."""

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        model: str,
        timeout: float,
        max_tokens: int,
    ) -> None:
        parsed = urlsplit(base_url)
        if parsed.scheme not in {"http", "https"} or parsed.netloc == "":
            raise CompletionFailed("A URL do provedor de linguagem é inválida.")
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._timeout = timeout
        self._max_tokens = max_tokens

    def complete(self, *, question: str, references: Sequence[SourceReference]) -> str:
        if question == "" and not references:
            return ""
        payload = json.dumps(
            {
                "model": self._model,
                "temperature": 0,
                "max_tokens": self._max_tokens,
                "messages": [
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": _user_prompt(question, references)},
                ],
            }
        ).encode("utf-8")
        request = urllib.request.Request(  # noqa: S310
            f"{self._base_url}/chat/completions",
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
            raise CompletionFailed("O provedor de linguagem falhou.") from None
        except urllib.error.URLError:
            raise CompletionFailed("O provedor de linguagem falhou.") from None
        return _parse_completion(raw)


def build_completion_client(
    settings: Settings,
) -> OpenAICompletionClient | UnconfiguredCompletionClient:
    """Use the configured language model, or a client that fails only when a query asks for it."""

    if settings.completion_api_key == "":
        return UnconfiguredCompletionClient()
    return OpenAICompletionClient(
        api_key=settings.completion_api_key,
        base_url=settings.embedding_base_url,
        model=settings.completion_model,
        timeout=settings.completion_timeout,
        max_tokens=settings.completion_max_tokens,
    )


def _user_prompt(question: str, references: Sequence[SourceReference]) -> str:
    blocks = [
        f"[{index}] arquivo={source.filename} posição={source.position}\n{source.content}"
        for index, source in enumerate(references, start=1)
    ]
    blocks.append(f"Pergunta: {question}")
    return "\n\n".join(blocks)


def _parse_completion(raw: bytes) -> str:
    try:
        body = json.loads(raw)
        content = body["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError, json.JSONDecodeError):
        raise CompletionFailed("O provedor de linguagem devolveu uma resposta inválida.") from None
    if not isinstance(content, str) or content.strip() == "":
        raise CompletionFailed("O provedor de linguagem devolveu uma resposta vazia.")
    return content.strip()
