from typing import Any

import httpx

from config import settings
from sentinel.models.base import (
    ChatMessage,
    LLMClient,
    LLMResponse,
)


class OllamaError(Exception):
    """
    Base exception for Ollama-related failures.
    """


class OllamaConnectionError(
    OllamaError
):
    """
    Raised when SentinelAI cannot reach Ollama.
    """


class OllamaResponseError(
    OllamaError
):
    """
    Raised when Ollama returns an invalid or
    unsuccessful response.
    """


class OllamaClient(LLMClient):
    """
    LLM client for a local Ollama server.

    The rest of SentinelAI should depend on
    LLMClient rather than directly on this class.
    """

    def __init__(
        self,
        model: str | None = None,
        base_url: str | None = None,
        timeout_seconds: float | None = None,
        http_client: httpx.Client | None = None,
    ) -> None:

        self.model = (
            model
            or settings.ollama_model
        )

        self.base_url = (
            base_url
            or settings.ollama_base_url
        ).rstrip("/")

        self.timeout_seconds = (
            timeout_seconds
            or settings.ollama_timeout_seconds
        )



        self._owns_http_client = (
            http_client is None
        )

        if http_client is None:
            self.http_client = httpx.Client(
                base_url=self.base_url,
                timeout=self.timeout_seconds,
            )
        else:
            self.http_client = http_client





    def chat(
        self,
        messages: list[ChatMessage],
        tools: list[
            dict[str, Any]
        ] | None = None,
        think: bool | None = None,
    ) -> LLMResponse:

        if not messages:
            raise ValueError(
                "At least one message is required."
            )

        if think is None:
            think = settings.ollama_think

        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [
                message.to_dict()
                for message in messages
            ],
            "stream": False,
            "think": think,
        }

        if tools:
            payload["tools"] = tools

        try:
            response = self.http_client.post(
                "/api/chat",
                json=payload,
            )

            response.raise_for_status()

        except (
            httpx.ConnectError,
            httpx.TimeoutException,
        ) as exc:

            raise OllamaConnectionError(
                "Could not connect to Ollama at "
                f"{self.base_url}. "
                "Make sure Ollama is running."
            ) from exc

        except httpx.HTTPStatusError as exc:

            raise OllamaResponseError(
                "Ollama returned HTTP "
                f"{exc.response.status_code}: "
                f"{exc.response.text}"
            ) from exc

        try:
            data = response.json()

        except ValueError as exc:
            raise OllamaResponseError(
                "Ollama returned invalid JSON."
            ) from exc

        message = data.get("message")

        if not isinstance(
            message,
            dict,
        ):
            raise OllamaResponseError(
                "Ollama response did not contain "
                "a valid message object."
            )

        content = message.get(
            "content",
            "",
        )

        tool_calls = message.get(
            "tool_calls",
            [],
        )

        if tool_calls is None:
            tool_calls = []

        return LLMResponse(
            content=content,
            model=data.get(
                "model",
                self.model,
            ),
            tool_calls=tool_calls,
            done=bool(
                data.get(
                    "done",
                    True,
                )
            ),
            prompt_tokens=data.get(
                "prompt_eval_count"
            ),
            completion_tokens=data.get(
                "eval_count"
            ),
            total_duration_ns=data.get(
                "total_duration"
            ),
        )





    def close(self) -> None:

        if self._owns_http_client:
            self.http_client.close()





    def __enter__(
        self,
    ) -> "OllamaClient":

        return self

    def __exit__(
        self,
        exc_type,
        exc_value,
        traceback,
    ) -> None:

        self.close()