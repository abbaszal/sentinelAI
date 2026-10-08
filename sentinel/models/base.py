from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Literal


MessageRole = Literal[
    "system",
    "user",
    "assistant",
    "tool",
]


@dataclass
class ChatMessage:
    """
    One message in an LLM conversation.

    This representation belongs to SentinelAI,
    not specifically to Ollama.
    """

    role: MessageRole
    content: str

    tool_calls: list[
        dict[str, Any]
    ] = field(
        default_factory=list
    )

    tool_name: str | None = None

    def to_dict(
        self,
    ) -> dict[str, Any]:
        """
        Convert SentinelAI's internal message into
        a dictionary understood by an LLM backend.
        """

        data: dict[str, Any] = {
            "role": self.role,
            "content": self.content,
        }

        if self.tool_calls:
            data["tool_calls"] = (
                self.tool_calls
            )

        if self.tool_name is not None:
            data["tool_name"] = (
                self.tool_name
            )

        return data


@dataclass
class LLMResponse:
    """
    Normalized language-model response.
    """

    content: str

    model: str

    tool_calls: list[
        dict[str, Any]
    ] = field(
        default_factory=list
    )

    done: bool = True

    prompt_tokens: int | None = None

    completion_tokens: int | None = None

    total_duration_ns: int | None = None


class LLMClient(ABC):
    """
    Generic interface for all SentinelAI
    language-model backends.
    """

    @abstractmethod
    def chat(
        self,
        messages: list[ChatMessage],
        tools: list[
            dict[str, Any]
        ] | None = None,
        think: bool | None = None,
    ) -> LLMResponse:
        """
        Generate the next assistant response.
        """

        raise NotImplementedError

    def close(self) -> None:
        """
        Optional cleanup hook.
        """

        return None