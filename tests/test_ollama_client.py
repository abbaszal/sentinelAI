import json

import httpx
import pytest

from sentinel.models.base import (
    ChatMessage,
)

from sentinel.models.ollama_client import (
    OllamaClient,
    OllamaResponseError,
)


def test_ollama_chat_parses_response():

    def handler(
        request: httpx.Request,
    ) -> httpx.Response:

        assert (
            request.url.path
            == "/api/chat"
        )

        payload = json.loads(
            request.content
        )

        assert (
            payload["model"]
            == "test-model"
        )

        assert (
            payload["messages"][0]["role"]
            == "user"
        )

        assert (
            payload["messages"][0]["content"]
            == "Hello"
        )

        assert payload["stream"] is False

        return httpx.Response(
            200,
            json={
                "model": "test-model",
                "message": {
                    "role": "assistant",
                    "content": "Hello from model",
                },
                "done": True,
                "prompt_eval_count": 5,
                "eval_count": 4,
                "total_duration": 1000,
            },
        )

    transport = httpx.MockTransport(
        handler
    )

    http_client = httpx.Client(
        base_url="http://test",
        transport=transport,
    )

    client = OllamaClient(
        model="test-model",
        base_url="http://test",
        http_client=http_client,
    )

    response = client.chat(
        [
            ChatMessage(
                role="user",
                content="Hello",
            )
        ]
    )

    assert (
        response.content
        == "Hello from model"
    )

    assert (
        response.model
        == "test-model"
    )

    assert response.done is True

    assert response.prompt_tokens == 5

    assert (
        response.completion_tokens
        == 4
    )

    http_client.close()


def test_ollama_tool_call_parsing():

    def handler(
        request: httpx.Request,
    ) -> httpx.Response:

        return httpx.Response(
            200,
            json={
                "model": "test-model",
                "message": {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [
                        {
                            "function": {
                                "name": (
                                    "get_order"
                                ),
                                "arguments": {
                                    "order_id": 100
                                },
                            }
                        }
                    ],
                },
                "done": True,
            },
        )

    transport = httpx.MockTransport(
        handler
    )

    http_client = httpx.Client(
        base_url="http://test",
        transport=transport,
    )

    client = OllamaClient(
        model="test-model",
        base_url="http://test",
        http_client=http_client,
    )

    response = client.chat(
        [
            ChatMessage(
                role="user",
                content="Find order 100",
            )
        ]
    )

    assert len(
        response.tool_calls
    ) == 1

    tool_call = (
        response.tool_calls[0]
    )

    assert (
        tool_call["function"]["name"]
        == "get_order"
    )

    assert (
        tool_call["function"][
            "arguments"
        ]["order_id"]
        == 100
    )

    http_client.close()


def test_empty_messages_are_rejected():

    client = OllamaClient(
        model="test-model",
    )

    with pytest.raises(
        ValueError
    ):
        client.chat([])

    client.close()


def test_invalid_ollama_response():

    def handler(
        request: httpx.Request,
    ) -> httpx.Response:

        return httpx.Response(
            200,
            json={
                "unexpected": "response"
            },
        )

    transport = httpx.MockTransport(
        handler
    )

    http_client = httpx.Client(
        base_url="http://test",
        transport=transport,
    )

    client = OllamaClient(
        model="test-model",
        base_url="http://test",
        http_client=http_client,
    )

    with pytest.raises(
        OllamaResponseError
    ):
        client.chat(
            [
                ChatMessage(
                    role="user",
                    content="Hello",
                )
            ]
        )

    http_client.close()