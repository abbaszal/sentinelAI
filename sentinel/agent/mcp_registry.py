import json

from contextlib import AsyncExitStack
from dataclasses import dataclass
from typing import Any

from mcp import Client

from mcp_servers.knowledge.server import (
    mcp as knowledge_mcp,
)

from mcp_servers.operations.server import (
    mcp as operations_mcp,
)

from mcp_servers.support_db.server import (
    mcp as support_db_mcp,
)






@dataclass
class ToolExecutionResult:
    """
    Normalized result from an MCP tool invocation.
    """

    tool_name: str

    is_error: bool

    structured_content: Any | None

    model_content: str






@dataclass
class RegisteredTool:
    """
    Internal record connecting an MCP tool definition
    with the MCP client that owns it.
    """

    name: str

    description: str

    input_schema: dict[str, Any]

    client: Client






class MCPToolRegistry:
    """
    Collect all SentinelAI MCP tools behind one interface.

    The future agent does not need to know which MCP
    server owns a specific tool.

    Example:

        get_orders
            -> Support DB MCP

        search_policy
            -> Knowledge MCP

        detect_duplicate_payment
            -> Operations MCP
    """

    def __init__(
        self,
    ) -> None:

        self._exit_stack: (
            AsyncExitStack | None
        ) = None

        self._tools: dict[
            str,
            RegisteredTool,
        ] = {}





    async def __aenter__(
        self,
    ) -> "MCPToolRegistry":

        self._exit_stack = (
            AsyncExitStack()
        )

        await self._exit_stack.__aenter__()

        servers = [
            (
                "support_db",
                support_db_mcp,
            ),
            (
                "knowledge",
                knowledge_mcp,
            ),
            (
                "operations",
                operations_mcp,
            ),
        ]

        for server_name, server in servers:

            client = await (
                self._exit_stack.enter_async_context(
                    Client(server)
                )
            )

            tools_result = (
                await client.list_tools()
            )

            for tool in tools_result.tools:

                if tool.name in self._tools:

                    raise RuntimeError(
                        "Duplicate MCP tool name "
                        f"detected: {tool.name}"
                    )

                self._tools[
                    tool.name
                ] = RegisteredTool(
                    name=tool.name,
                    description=(
                        tool.description
                        or tool.name
                    ),
                    input_schema=(
                        tool.input_schema
                    ),
                    client=client,
                )

        return self

    async def __aexit__(
        self,
        exc_type,
        exc_value,
        traceback,
    ) -> None:

        if self._exit_stack is not None:

            await self._exit_stack.__aexit__(
                exc_type,
                exc_value,
                traceback,
            )





    def tool_names(
        self,
    ) -> set[str]:

        return set(
            self._tools.keys()
        )

    def has_tool(
        self,
        tool_name: str,
    ) -> bool:

        return (
            tool_name
            in self._tools
        )





    def ollama_tools(
        self,
    ) -> list[dict[str, Any]]:
        """
        Convert MCP tool definitions into the function
        schema expected by Ollama.

        MCP already provides JSON Schema for each tool's
        parameters, so we reuse that schema rather than
        manually redefining the tool.
        """

        tools: list[
            dict[str, Any]
        ] = []

        for registered in (
            self._tools.values()
        ):

            tools.append(
                {
                    "type": "function",
                    "function": {
                        "name": (
                            registered.name
                        ),
                        "description": (
                            registered.description
                        ),
                        "parameters": (
                            registered.input_schema
                        ),
                    },
                }
            )

        return tools





    async def call_tool(
        self,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> ToolExecutionResult:
        """
        Execute one allowed MCP tool.

        Unknown tools are rejected rather than being
        dynamically resolved or executed.
        """

        registered = self._tools.get(
            tool_name
        )

        if registered is None:

            return ToolExecutionResult(
                tool_name=tool_name,
                is_error=True,
                structured_content=None,
                model_content=json.dumps(
                    {
                        "error": (
                            "Unknown or unauthorized "
                            f"tool: {tool_name}"
                        )
                    }
                ),
            )

        result = await (
            registered.client.call_tool(
                tool_name,
                arguments,
            )
        )






        if (
            result.structured_content
            is not None
        ):

            payload = {
                "is_error": (
                    result.is_error
                ),
                "result": (
                    result.structured_content
                ),
            }

            model_content = json.dumps(
                payload,
                ensure_ascii=False,
                default=str,
            )

            return ToolExecutionResult(
                tool_name=tool_name,
                is_error=bool(
                    result.is_error
                ),
                structured_content=(
                    result.structured_content
                ),
                model_content=(
                    model_content
                ),
            )






        text_parts: list[str] = []

        for block in result.content:

            text = getattr(
                block,
                "text",
                None,
            )

            if text:
                text_parts.append(
                    text
                )

        fallback_content = "\n".join(
            text_parts
        )

        payload = {
            "is_error": (
                result.is_error
            ),
            "result": (
                fallback_content
            ),
        }

        return ToolExecutionResult(
            tool_name=tool_name,
            is_error=bool(
                result.is_error
            ),
            structured_content=None,
            model_content=json.dumps(
                payload,
                ensure_ascii=False,
                default=str,
            ),
        )