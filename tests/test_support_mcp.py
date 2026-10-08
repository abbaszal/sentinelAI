import pytest

from mcp import Client

from mcp_servers.support_db.server import (
    mcp,
)


@pytest.mark.anyio
async def test_support_mcp_lists_tools():
    async with Client(
        mcp,
        raise_exceptions=True,
    ) as client:

        result = await client.list_tools()

        tool_names = {
            tool.name
            for tool in result.tools
        }

        assert "get_customer_summary" in tool_names
        assert "get_orders" in tool_names
        assert "get_order" in tool_names
        assert "get_payment_status" in tool_names
        assert "get_shipment_status" in tool_names
        assert "get_refunds" in tool_names
        assert (
            "get_customer_support_cases"
            in tool_names
        )


@pytest.mark.anyio
async def test_support_mcp_has_output_schema():
    async with Client(
        mcp,
        raise_exceptions=True,
    ) as client:

        result = await client.list_tools()

        get_order_tool = next(
            tool
            for tool in result.tools
            if tool.name == "get_order"
        )

        assert (
            get_order_tool.output_schema
            is not None
        )


@pytest.mark.anyio
async def test_support_mcp_get_order():
    async with Client(
        mcp,
        raise_exceptions=True,
    ) as client:

        result = await client.call_tool(
            "get_order",
            {
                "order_id": 1,
            },
        )

        assert result.is_error is False

        assert (
            result.structured_content
            is not None
        )

        data = result.structured_content

        assert data["order_id"] == 1
        assert "customer_id" in data
        assert "status" in data
        assert "total_amount" in data