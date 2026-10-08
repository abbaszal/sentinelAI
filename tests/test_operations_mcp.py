import pytest

from mcp import Client

from mcp_servers.operations.server import (
    mcp,
)


@pytest.mark.anyio
async def test_operations_tools_exist():

    async with Client(
        mcp,
        raise_exceptions=True,
    ) as client:

        result = await client.list_tools()

        tool_names = {
            tool.name
            for tool in result.tools
        }

        assert (
            "detect_duplicate_payment"
            in tool_names
        )

        assert (
            "check_cancellation_eligibility"
            in tool_names
        )

        assert (
            "get_payment_summary"
            in tool_names
        )