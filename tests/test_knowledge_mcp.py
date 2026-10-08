import pytest

from mcp import Client

from mcp_servers.knowledge.server import (
    mcp,
)


@pytest.mark.anyio
async def test_policy_search_tool():

    async with Client(
        mcp,
        raise_exceptions=True,
    ) as client:

        result = await client.call_tool(
            "search_policy",
            {
                "query": (
                    "customer was charged twice"
                ),
                "top_k": 3,
            },
        )

        assert result.is_error is False

        data = result.structured_content

        assert data["query"]

        assert len(
            data["results"]
        ) == 3

        top_result = data["results"][0]

        assert (
            top_result["document_id"]
            == "payment_policy"
        )