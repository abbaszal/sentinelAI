import json

import pytest

from sentinel.agent.controlled_agent import (
    AgentConfig,
    ControlledAgent,
)

from sentinel.agent.mcp_registry import (
    ToolExecutionResult,
)

from sentinel.models.base import (
    ChatMessage,
    LLMClient,
    LLMResponse,
)






class FakeLLMClient(
    LLMClient
):

    def __init__(
        self,
        responses: list[
            LLMResponse
        ],
    ) -> None:

        self.responses = responses

        self.index = 0

    def chat(
        self,
        messages: list[ChatMessage],
        tools=None,
        think=None,
    ) -> LLMResponse:

        response = (
            self.responses[
                self.index
            ]
        )

        self.index += 1

        return response






class FakeToolRegistry:

    def __init__(
        self,
    ) -> None:

        self.calls = []

    def ollama_tools(
        self,
    ):

        return [
            {
                "type": "function",
                "function": {
                    "name": "get_order",
                    "description": (
                        "Get an order"
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "order_id": {
                                "type": "integer"
                            }
                        },
                        "required": [
                            "order_id"
                        ],
                    },
                },
            }
        ]

    def has_tool(
        self,
        tool_name: str,
    ) -> bool:

        return (
            tool_name
            == "get_order"
        )

    async def call_tool(
        self,
        tool_name,
        arguments,
    ):

        self.calls.append(
            (
                tool_name,
                arguments,
            )
        )

        data = {
            "order_id": (
                arguments[
                    "order_id"
                ]
            ),
            "status": "shipped",
            "total_amount": 59.99,
        }

        return ToolExecutionResult(
            tool_name=tool_name,
            is_error=False,
            structured_content=data,
            model_content=json.dumps(
                {
                    "is_error": False,
                    "result": data,
                }
            ),
        )






@pytest.mark.anyio
async def test_agent_calls_tool_then_answers():

    fake_llm = FakeLLMClient(
        responses=[
            LLMResponse(
                content="",
                model="fake",
                tool_calls=[
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
            ),

            LLMResponse(
                content=(
                    "Order 100 has shipped."
                ),
                model="fake",
            ),
        ]
    )

    tools = FakeToolRegistry()

    agent = ControlledAgent(
        llm=fake_llm,
        tools=tools,
    )

    result = await agent.run(
        "Where is order 100?"
    )

    assert (
        result.finish_reason
        == "completed"
    )

    assert (
        result.answer
        == "Order 100 has shipped."
    )

    assert (
        result.model_calls
        == 2
    )

    assert len(
        result.tool_calls
    ) == 1

    assert tools.calls == [
        (
            "get_order",
            {
                "order_id": 100
            },
        )
    ]


@pytest.mark.anyio
async def test_agent_can_answer_without_tool():

    fake_llm = FakeLLMClient(
        responses=[
            LLMResponse(
                content=(
                    "Hello! How can I help?"
                ),
                model="fake",
            )
        ]
    )

    tools = FakeToolRegistry()

    agent = ControlledAgent(
        llm=fake_llm,
        tools=tools,
    )

    result = await agent.run(
        "Hello"
    )

    assert (
        result.finish_reason
        == "completed"
    )

    assert len(
        result.tool_calls
    ) == 0


@pytest.mark.anyio
async def test_agent_rejects_unknown_tool():

    fake_llm = FakeLLMClient(
        responses=[
            LLMResponse(
                content="",
                model="fake",
                tool_calls=[
                    {
                        "function": {
                            "name": (
                                "delete_database"
                            ),
                            "arguments": {},
                        }
                    }
                ],
            ),
            LLMResponse(
                content=(
                    "I cannot perform "
                    "that operation."
                ),
                model="fake",
            ),
        ]
    )

    tools = FakeToolRegistry()

    agent = ControlledAgent(
        llm=fake_llm,
        tools=tools,
    )

    result = await agent.run(
        "Delete everything."
    )

    assert (
        result.finish_reason
        == "completed"
    )

    assert tools.calls == []


@pytest.mark.anyio
async def test_agent_detects_tool_loop():

    repeated_call = {
        "function": {
            "name": "get_order",
            "arguments": {
                "order_id": 100
            },
        }
    }

    fake_llm = FakeLLMClient(
        responses=[
            LLMResponse(
                content="",
                model="fake",
                tool_calls=[
                    repeated_call
                ],
            ),
            LLMResponse(
                content="",
                model="fake",
                tool_calls=[
                    repeated_call
                ],
            ),
            LLMResponse(
                content="",
                model="fake",
                tool_calls=[
                    repeated_call
                ],
            ),
        ]
    )

    tools = FakeToolRegistry()

    agent = ControlledAgent(
        llm=fake_llm,
        tools=tools,
        config=AgentConfig(
            max_steps=6,
            max_identical_tool_calls=2,
        ),
    )

    result = await agent.run(
        "Find order 100."
    )

    assert (
        result.finish_reason
        == "loop_detected"
    )