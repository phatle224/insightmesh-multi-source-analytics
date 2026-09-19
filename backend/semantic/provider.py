"""Provider boundaries for direct Gemini generation and OpenRouter fallback/embeddings."""

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

    def close(self) -> None: ...


def _gemini_schema(
    schema: dict[str, Any], definitions: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Gemini REST uses enum-like uppercase JSON schema type names."""
    definitions = definitions or schema.get("$defs", {})
    reference = schema.get("$ref")
    if isinstance(reference, str) and reference.startswith("#/$defs/"):
        target = definitions.get(reference.rsplit("/", 1)[-1])
        if isinstance(target, dict):
            return _gemini_schema(target, definitions)
    converted: dict[str, Any] = {}
    for key, value in schema.items():
        # The REST Schema protobuf rejects this JSON-Schema keyword even though
        # it is valid in the Pydantic/OpenRouter schema representation.
        if key in {"additionalProperties", "$defs", "$ref"}:
            continue
        if key == "type" and isinstance(value, str):
            converted[key] = value.upper()
        elif isinstance(value, dict):
            converted[key] = _gemini_schema(value, definitions)
        elif isinstance(value, list):
            converted[key] = [
                _gemini_schema(item, definitions) if isinstance(item, dict) else item
                for item in value
            ]
        else:
            converted[key] = value
    return converted


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
                error_code = (
                    "provider_timeout"
                    if isinstance(exc, httpx.TimeoutException)
                    else "provider_unavailable"
                )
            except httpx.HTTPStatusError as exc:
                retryable = exc.response.status_code == 429 or exc.response.status_code >= 500
                error = exc
                error_code = (
                    "provider_rate_limited"
                    if exc.response.status_code == 429
                    else "provider_unavailable"
                )
            except (ValueError, json.JSONDecodeError) as exc:
                raise ProviderError(
                    "provider_invalid_response", "Provider returned invalid data"
                ) from exc
            if not retryable or attempt == 1:
                raise ProviderError(
                    error_code,
                    "Semantic provider is unavailable",
                    retryable=retryable,
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


class GeminiProvider:
    """Direct Google AI Studio Gemini GenerateContent client."""

    def __init__(self, *, api_key: str, base_url: str, model: str, timeout_seconds: int) -> None:
        self.model = model
        self._client = httpx.Client(
            base_url=base_url.rstrip("/"),
            headers={"x-goog-api-key": api_key},
            timeout=timeout_seconds,
        )

    def generate_structured(self, request: StructuredGenerationRequest) -> dict[str, Any]:
        prompt = f"{request.system_prompt}\n\nInput metadata:\n{json.dumps(request.user_payload)}"
        payload = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {
                "responseMimeType": "application/json",
                "responseSchema": _gemini_schema(request.json_schema),
                "temperature": 0,
            },
        }
        for attempt in range(2):
            error: Exception | None = None
            try:
                response = self._client.post(
                    f"/v1beta/models/{self.model}:generateContent", json=payload
                )
                response.raise_for_status()
                body = response.json()
                content = body["candidates"][0]["content"]["parts"][0]["text"]
                parsed = json.loads(content) if isinstance(content, str) else content
                if not isinstance(parsed, dict):
                    raise ValueError("Gemini response was not an object")
                return parsed
            except (httpx.TimeoutException, httpx.TransportError) as exc:
                error = exc
                code = (
                    "provider_timeout"
                    if isinstance(exc, httpx.TimeoutException)
                    else "provider_unavailable"
                )
            except httpx.HTTPStatusError as exc:
                error = exc
                code = (
                    "provider_rate_limited"
                    if exc.response.status_code == 429
                    else "provider_unavailable"
                )
                if exc.response.status_code not in {429, 500, 502, 503, 504}:
                    raise ProviderError(
                        "provider_auth_failed", "Gemini provider rejected the request"
                    ) from exc
            except (KeyError, IndexError, TypeError, ValueError, json.JSONDecodeError) as exc:
                raise ProviderError(
                    "provider_invalid_response", "Gemini returned invalid structured data"
                ) from exc
            if attempt == 1:
                raise ProviderError(
                    code, "Gemini provider is unavailable", retryable=True
                ) from error
            time.sleep(0.2)
        raise AssertionError("unreachable")

    def embed(self, inputs: list[str]) -> list[list[float]]:
        raise ProviderError(
            "embedding_provider_unavailable", "Gemini embeddings are not configured"
        )

    def close(self) -> None:
        self._client.close()


class FallbackProvider:
    """Use Gemini first; fallback only for timeout or rate-limit exhaustion."""

    def __init__(self, primary: LLMProvider, fallback: LLMProvider | None) -> None:
        self.primary = primary
        self.fallback = fallback

    def generate_structured(self, request: StructuredGenerationRequest) -> dict[str, Any]:
        try:
            return self.primary.generate_structured(request)
        except ProviderError as error:
            if self.fallback is None or error.code not in {
                "provider_timeout",
                "provider_rate_limited",
            }:
                raise
            return self.fallback.generate_structured(request)

    def embed(self, inputs: list[str]) -> list[list[float]]:
        if self.fallback is not None:
            return self.fallback.embed(inputs)
        return self.primary.embed(inputs)

    def close(self) -> None:
        self.primary.close()
        if self.fallback is not None:
            self.fallback.close()
