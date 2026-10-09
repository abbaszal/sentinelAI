import argparse
import asyncio

from pathlib import Path

from sentinel.agent.controlled_agent import (
    AgentConfig,
    ControlledAgent,
)

from sentinel.agent.mcp_registry import (
    MCPToolRegistry,
)

from sentinel.evaluation.agent_eval import (
    calculate_agent_summary,
    evaluate_agent_case,
    load_agent_benchmark,
    print_case_result,
    print_summary,
    save_results,
)

from sentinel.models.ollama_client import (
    OllamaClient,
)


async def run_benchmark(
    limit: int | None = None,
    case_id: str | None = None,
    output_path: Path = Path(
        "artifacts/evaluations/"
        "agent_benchmark_latest.json"
    ),
) -> None:

    cases = load_agent_benchmark()





    if case_id is not None:

        cases = [
            case
            for case in cases
            if case.case_id
            == case_id
        ]

        if not cases:

            raise ValueError(
                f"Unknown benchmark case: "
                f"{case_id}"
            )





    elif (
        limit is not None
    ):

        cases = cases[
            :limit
        ]

    print()
    print("=" * 72)
    print("SentinelAI Agent Benchmark")
    print("=" * 72)

    print()
    print(
        "Cases selected:",
        len(cases),
    )

    results = []





    with OllamaClient() as llm:

        async with MCPToolRegistry() as tools:

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

            for index, case in enumerate(
                cases,
                start=1,
            ):

                print()
                print(
                    f"[{index}/{len(cases)}] "
                    f"{case.case_id}"
                )

                print(
                    case.user_request
                )

                result = (
                    await evaluate_agent_case(
                        case=case,
                        agent=agent,
                    )
                )

                results.append(
                    result
                )

                print_case_result(
                    result
                )

    summary = (
        calculate_agent_summary(
            results
        )
    )

    print_summary(
        summary
    )

    save_results(
        output_path=(
            output_path
        ),
        summary=summary,
        results=results,
    )

    print()
    print(
        "Saved detailed results to:"
    )

    print(
        output_path
    )


def parse_args():

    parser = argparse.ArgumentParser(
        description=(
            "Run the SentinelAI "
            "controlled-agent benchmark."
        )
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help=(
            "Run only the first N cases."
        ),
    )

    parser.add_argument(
        "--case",
        type=str,
        default=None,
        help=(
            "Run a single benchmark case ID."
        ),
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=Path(
            "artifacts/evaluations/"
            "agent_benchmark_latest.json"
        ),
        help=(
            "JSON output path."
        ),
    )

    return parser.parse_args()


def main():

    args = parse_args()

    asyncio.run(
        run_benchmark(
            limit=args.limit,
            case_id=args.case,
            output_path=(
                args.output
            ),
        )
    )


if __name__ == "__main__":
    main()