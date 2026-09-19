"""OpenRouter boundary. Request bodies and secrets are intentionally never logged."""

import json
import time
from dataclasses import dataclass
from typing import Any, Protocol

import httpx


class ProviderError(RuntimeError):
    def __init__(self, code: str, safe_message: str, *, retryable: bool = False) -> None:
        super().__init__(safe_message)
        self.code = code
        self.safe_message = safe_message
        self.retryable = retryable


@dataclass(frozen=True)
class StructuredGenerationRequest:
    system_prompt: str
    user_payload: dict[str, Any]
    schema_name: str
    json_schema: dict[str, Any]


class LLMProvider(Protocol):
    def generate_structured(self, request: StructuredGenerationRequest) -> dict[str, Any]: ...

    def embed(self, inputs: list[str]) -> list[list[float]]: ...


class OpenRouterProvider:
    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        llm_model: str,
        embedding_model: str,
        embedding_dimensions: int,
        timeout_seconds: int,
    ) -> None:
        self.llm_model = llm_model
        self.embedding_model = embedding_model
        self.embedding_dimensions = embedding_dimensions
        self._client = httpx.Client(
            base_url=base_url.rstrip("/"),
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=timeout_seconds,
        )

    def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        for attempt in range(2):
            error: Exception
            try:
                response = self._client.post(path, json=payload)
                response.raise_for_status()
                body = response.json()
                if not isinstance(body, dict):
                    raise ValueError("Provider response was not an object")
                return body
            except (httpx.TimeoutException, httpx.TransportError) as exc:
                retryable = True
                error = exc
            except httpx.HTTPStatusError as exc:
                retryable = exc.response.status_code == 429 or exc.response.status_code >= 500
                error = exc
            except (ValueError, json.JSONDecodeError) as exc:
                raise ProviderError(
                    "provider_invalid_response", "Provider returned invalid data"
                ) from exc
            if not retryable or attempt == 1:
                raise ProviderError(
                    "provider_unavailable", "Semantic provider is unavailable", retryable=retryable
                ) from error
            time.sleep(0.2)
        raise AssertionError("unreachable")

    def generate_structured(self, request: StructuredGenerationRequest) -> dict[str, Any]:
        body = self._post(
            "/chat/completions",
            {
                "model": self.llm_model,
                "messages": [
                    {"role": "system", "content": request.system_prompt},
                    {"role": "user", "content": json.dumps(request.user_payload)},
                ],
                "response_format": {
                    "type": "json_schema",
                    "json_schema": {
                        "name": request.schema_name,
                        "strict": True,
                        "schema": request.json_schema,
                    },
                },
                "provider": {"require_parameters": True},
                "temperature": 0,
            },
        )
        try:
            content = body["choices"][0]["message"]["content"]
            parsed = json.loads(content) if isinstance(content, str) else content
        except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
            raise ProviderError(
                "provider_invalid_response", "Provider returned invalid data"
            ) from exc
        if not isinstance(parsed, dict):
            raise ProviderError("provider_invalid_response", "Provider returned invalid data")
        return parsed

    def embed(self, inputs: list[str]) -> list[list[float]]:
        if not inputs:
            return []
        body = self._post(
            "/embeddings",
            {
                "model": self.embedding_model,
                "input": inputs,
                "dimensions": self.embedding_dimensions,
            },
        )
        try:
            ordered = sorted(body["data"], key=lambda item: int(item["index"]))
            vectors = [[float(value) for value in item["embedding"]] for item in ordered]
        except (KeyError, TypeError, ValueError) as exc:
            raise ProviderError(
                "provider_invalid_response", "Provider returned invalid embeddings"
            ) from exc
        if len(vectors) != len(inputs) or any(
            len(vector) != self.embedding_dimensions for vector in vectors
        ):
            raise ProviderError("provider_invalid_response", "Provider returned invalid embeddings")
        return vectors

    def close(self) -> None:
        self._client.close()
