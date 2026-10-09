import asyncio

from sentinel.agent.controlled_agent import (
    AgentConfig,
    ControlledAgent,
)

from sentinel.agent.mcp_registry import (
    MCPToolRegistry,
)

from sentinel.models.ollama_client import (
    OllamaClient,
    OllamaConnectionError,
)


async def main() -> None:

    user_request = (
        "Customer 2 says they were charged twice. "
        "Investigate what happened and explain what "
        "NovaShop policy says should happen next."
    )

    print()
    print("=" * 70)
    print("SentinelAI Controlled Agent")
    print("=" * 70)

    print()
    print("USER:")
    print(user_request)

    print()

    try:

        with OllamaClient() as llm:

            async with MCPToolRegistry() as tools:

                print(
                    "Available MCP tools:"
                )

                for tool_name in sorted(
                    tools.tool_names()
                ):
                    print(
                        f"  - {tool_name}"
                    )

                agent = ControlledAgent(
                    llm=llm,
                    tools=tools,
                    config=AgentConfig(
                        max_steps=8,
                        max_tool_calls=12,
                        max_identical_tool_calls=2,
                        think=False,
                    ),
                )

                result = await agent.run(
                    user_request
                )

                print()
                print("=" * 70)

                print("FINAL ANSWER:")
                print(result.answer)

                print()

                print(
                    "Finish reason:",
                    result.finish_reason,
                )

                print(
                    "Model calls:",
                    result.model_calls,
                )

                print(
                    "Tool calls:",
                    len(
                        result.tool_calls
                    ),
                )

                print(
                    "Verification rejections:",
                    len(
                        result.verification_failures
                    ),
                )

                print(
                    "Prompt tokens:",
                    result.prompt_tokens,
                )

                print(
                    "Completion tokens:",
                    result.completion_tokens,
                )





                if (
                    result.verification_failures
                ):

                    print()
                    print(
                        "VERIFICATION HISTORY:"
                    )

                    for (
                        index,
                        failure,
                    ) in enumerate(
                        result.verification_failures,
                        start=1,
                    ):

                        print()
                        print(
                            f"  Rejection #{index}"
                        )

                        for line in (
                            failure.splitlines()
                        ):
                            print(
                                f"  {line}"
                            )





                print()
                print("TOOL TRACE:")

                if not result.tool_calls:

                    print(
                        "  No tools used."
                    )

                for (
                    index,
                    trace,
                ) in enumerate(
                    result.tool_calls,
                    start=1,
                ):

                    print()

                    print(
                        f"  Tool #{index}"
                    )

                    print(
                        "  Step:",
                        trace.step,
                    )

                    print(
                        "  Source:",
                        trace.source,
                    )

                    print(
                        "  Name:",
                        trace.tool_name,
                    )

                    print(
                        "  Arguments:",
                        trace.arguments,
                    )

                    print(
                        "  Error:",
                        trace.is_error,
                    )

                    print(
                        "  Result:",
                        trace.result,
                    )

                print()
                print("=" * 70)

    except OllamaConnectionError as exc:

        print()
        print(
            "Could not connect to Ollama."
        )

        print(exc)


if __name__ == "__main__":

    asyncio.run(
        main()
    )