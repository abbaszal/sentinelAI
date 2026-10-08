from typing import Any

from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError

from sentinel.retrieval.embedding_retriever import (
    build_embedding_retriever,
)


mcp = MCPServer(
    "SentinelAI Knowledge"
)


# Build embedding model + FAISS index once
# when this MCP server starts.
retriever = build_embedding_retriever()


@mcp.tool(structured_output=True)
def search_policy(
    query: str,
    top_k: int = 3,
) -> dict[str, Any]:
    """
    Search NovaShop policy documents using semantic
    embedding retrieval.

    Returns relevant policy sections together with
    source metadata and similarity scores.
    """

    query = query.strip()

    if not query:
        raise ToolError(
            "Policy search query cannot be empty."
        )

    if top_k < 1 or top_k > 5:
        raise ToolError(
            "top_k must be between 1 and 5."
        )

    results = retriever.search(
        query=query,
        top_k=top_k,
    )

    return {
        "query": query,
        "results": [
            {
                "rank": rank,
                "score": round(
                    result.score,
                    4,
                ),
                "document_id": (
                    result.chunk.document_id
                ),
                "title": (
                    result.chunk.title
                ),
                "section": (
                    result.chunk.section
                ),
                "content": (
                    result.chunk.content
                ),
                "source": (
                    result.chunk.source
                ),
            }
            for rank, result in enumerate(
                results,
                start=1,
            )
        ],
    }


if __name__ == "__main__":
    mcp.run()