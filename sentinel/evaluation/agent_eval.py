import json
import re
import time

from dataclasses import (
    asdict,
    dataclass,
    field,
)

from pathlib import Path
from typing import Any

from database.session import (
    SessionLocal,
)

from sentinel.agent.controlled_agent import (
    AgentRunResult,
    AgentToolTrace,
    ControlledAgent,
)

from sentinel.business.order_rules import (
    calculate_overpayment_amount,
    detect_duplicate_payment,
)

from sentinel.repositories.support_repository import (
    get_customer_orders,
)


# ---------------------------------------------------------
# Configuration
# ---------------------------------------------------------

DEFAULT_BENCHMARK_PATH = Path(
    "data/benchmarks/"
    "agent_duplicate_payment_benchmark.json"
)


# ---------------------------------------------------------
# Benchmark models
# ---------------------------------------------------------

@dataclass
class AgentBenchmarkCase:
    case_id: str

    customer_id: int

    expected_duplicate: bool

    requires_policy: bool

    category: str

    user_request: str


@dataclass
class OracleOrderResult:
    order_id: int

    duplicate_payment: bool

    overpayment_amount: float


@dataclass
class AgentCaseEvaluation:
    case_id: str

    category: str

    customer_id: int

    expected_duplicate: bool

    oracle_orders: list[
        OracleOrderResult
    ]

    finish_reason: str

    completed: bool

    duplicate_tool_coverage: bool

    duplicate_tool_accuracy: bool

    policy_coverage: bool

    answer_fact_coverage: bool

    overall_success: bool

    model_calls: int

    tool_calls: int

    verification_rejections: int

    scope_rejections: int

    prompt_tokens: int

    completion_tokens: int

    latency_seconds: float

    answer: str

    failures: list[str] = field(
        default_factory=list
    )


@dataclass
class AgentBenchmarkSummary:
    total_cases: int

    completed_rate: float

    duplicate_tool_coverage_rate: float

    duplicate_tool_accuracy_rate: float

    policy_coverage_rate: float

    answer_fact_coverage_rate: float

    overall_success_rate: float

    average_model_calls: float

    average_tool_calls: float

    average_verification_rejections: float

    average_scope_rejections: float

    average_prompt_tokens: float

    average_completion_tokens: float

    average_latency_seconds: float


# ---------------------------------------------------------
# Benchmark loading
# ---------------------------------------------------------

def load_agent_benchmark(
    path: Path = DEFAULT_BENCHMARK_PATH,
) -> list[AgentBenchmarkCase]:

    raw_data = json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )

    cases: list[
        AgentBenchmarkCase
    ] = []

    for item in raw_data:

        cases.append(
            AgentBenchmarkCase(
                case_id=item["id"],
                customer_id=(
                    item["customer_id"]
                ),
                expected_duplicate=(
                    item[
                        "expected_duplicate"
                    ]
                ),
                requires_policy=(
                    item[
                        "requires_policy"
                    ]
                ),
                category=item[
                    "category"
                ],
                user_request=item[
                    "user_request"
                ],
            )
        )

    return cases


# ---------------------------------------------------------
# Trusted oracle
# ---------------------------------------------------------

def build_oracle(
    customer_id: int,
) -> list[OracleOrderResult]:
    """
    Build ground truth directly from the trusted
    deterministic business layer.

    This does NOT use the agent's conclusions.
    """

    with SessionLocal() as db:

        orders = get_customer_orders(
            db,
            customer_id,
        )

        results: list[
            OracleOrderResult
        ] = []

        for order in orders:

            duplicate = (
                detect_duplicate_payment(
                    db,
                    order.id,
                )
            )

            overpayment = (
                calculate_overpayment_amount(
                    db,
                    order.id,
                )
            )

            results.append(
                OracleOrderResult(
                    order_id=order.id,
                    duplicate_payment=(
                        duplicate
                    ),
                    overpayment_amount=(
                        overpayment
                    ),
                )
            )

        return results


# ---------------------------------------------------------
# Trace helpers
# ---------------------------------------------------------

def successful_duplicate_traces(
    traces: list[
        AgentToolTrace
    ],
) -> dict[
    int,
    AgentToolTrace,
]:
    """
    Return successful duplicate-payment checks keyed
    by order ID.
    """

    results: dict[
        int,
        AgentToolTrace,
    ] = {}

    for trace in traces:

        if trace.is_error:
            continue

        if (
            trace.tool_name
            != "detect_duplicate_payment"
        ):
            continue

        order_id = trace.arguments.get(
            "order_id"
        )

        if not isinstance(
            order_id,
            int,
        ):
            continue

        results[
            order_id
        ] = trace

    return results


def has_successful_policy_search(
    traces: list[
        AgentToolTrace
    ],
) -> bool:

    for trace in traces:

        if trace.is_error:
            continue

        if (
            trace.tool_name
            != "search_policy"
        ):
            continue

        if not isinstance(
            trace.result,
            dict,
        ):
            continue

        results = trace.result.get(
            "results"
        )

        if (
            isinstance(
                results,
                list,
            )
            and len(results) > 0
        ):
            return True

    return False


# ---------------------------------------------------------
# Evidence grading
# ---------------------------------------------------------

def grade_duplicate_tool_coverage(
    oracle: list[
        OracleOrderResult
    ],
    run: AgentRunResult,
) -> bool:

    traces = (
        successful_duplicate_traces(
            run.tool_calls
        )
    )

    expected_order_ids = {
        order.order_id
        for order in oracle
    }

    checked_order_ids = set(
        traces.keys()
    )

    return (
        expected_order_ids
        <= checked_order_ids
    )


def grade_duplicate_tool_accuracy(
    oracle: list[
        OracleOrderResult
    ],
    run: AgentRunResult,
) -> bool:

    traces = (
        successful_duplicate_traces(
            run.tool_calls
        )
    )

    for expected in oracle:

        trace = traces.get(
            expected.order_id
        )

        if trace is None:
            return False

        if not isinstance(
            trace.result,
            dict,
        ):
            return False

        actual_duplicate = (
            trace.result.get(
                "duplicate_payment"
            )
        )

        actual_overpayment = (
            trace.result.get(
                "overpayment_amount"
            )
        )

        if (
            actual_duplicate
            is not expected.duplicate_payment
        ):
            return False

        if not isinstance(
            actual_overpayment,
            (
                int,
                float,
            ),
        ):
            return False

        if abs(
            float(
                actual_overpayment
            )
            - expected.overpayment_amount
        ) > 0.01:
            return False

    return True


# ---------------------------------------------------------
# Final-answer grading
# ---------------------------------------------------------

def answer_mentions_order(
    answer: str,
    order_id: int,
) -> bool:

    pattern = (
        r"\border"
        r"(?:\s+id)?"
        r"\s*[:#]?\s*"
        + re.escape(
            str(order_id)
        )
        + r"\b"
    )

    return (
        re.search(
            pattern,
            answer,
            flags=re.IGNORECASE,
        )
        is not None
    )


def answer_mentions_amount(
    answer: str,
    amount: float,
) -> bool:

    variants = {
        f"{amount:.2f}",
        str(
            round(
                amount,
                2,
            )
        ),
    }

    return any(
        variant in answer
        for variant in variants
    )


def grade_answer_fact_coverage(
    oracle: list[
        OracleOrderResult
    ],
    answer: str,
) -> bool:
    """
    Strictly grade important deterministic facts.

    Positive cases:
        every duplicated order must be mentioned
        and its overpayment amount must be mentioned.

    Negative cases:
        answer must not positively claim a duplicate
        payment was confirmed.
    """

    duplicated_orders = [
        order
        for order in oracle
        if order.duplicate_payment
    ]

    # ---------------------------------------------
    # Positive case
    # ---------------------------------------------

    if duplicated_orders:

        for order in duplicated_orders:

            if not answer_mentions_order(
                answer,
                order.order_id,
            ):
                return False

            if not answer_mentions_amount(
                answer,
                order.overpayment_amount,
            ):
                return False

        return True

    # ---------------------------------------------
    # Negative case
    # ---------------------------------------------

    lower = answer.lower()

    positive_claim_patterns = (
        "duplicate payment was confirmed",
        "duplicate payments were confirmed",
        "duplicate payment is confirmed",
        "duplicate payments are confirmed",
        "duplicate payment was detected",
        "duplicate payments were detected",
        "meets the criteria for a duplicate payment",
    )

    return not any(
        pattern in lower
        for pattern
        in positive_claim_patterns
    )


# ---------------------------------------------------------
# Single-case evaluation
# ---------------------------------------------------------

async def evaluate_agent_case(
    case: AgentBenchmarkCase,
    agent: ControlledAgent,
) -> AgentCaseEvaluation:

    oracle = build_oracle(
        case.customer_id
    )

    oracle_has_duplicate = any(
        order.duplicate_payment
        for order in oracle
    )

    failures: list[str] = []

    # ---------------------------------------------
    # Benchmark integrity
    # ---------------------------------------------

    if (
        oracle_has_duplicate
        != case.expected_duplicate
    ):

        failures.append(
            "BENCHMARK_INTEGRITY: "
            "The benchmark label does not match "
            "the deterministic database oracle."
        )

    started = (
        time.perf_counter()
    )

    run = await agent.run(
        case.user_request
    )

    elapsed = (
        time.perf_counter()
        - started
    )

    completed = (
        run.finish_reason
        == "completed"
    )

    duplicate_tool_coverage = (
        grade_duplicate_tool_coverage(
            oracle=oracle,
            run=run,
        )
    )

    duplicate_tool_accuracy = (
        grade_duplicate_tool_accuracy(
            oracle=oracle,
            run=run,
        )
    )

    if case.requires_policy:

        policy_coverage = (
            has_successful_policy_search(
                run.tool_calls
            )
        )

    else:
        # Policy retrieval is not required for this case.
        policy_coverage = True

    answer_fact_coverage = (
        grade_answer_fact_coverage(
            oracle=oracle,
            answer=run.answer,
        )
    )

    # ---------------------------------------------
    # Failure reasons
    # ---------------------------------------------

    if not completed:
        failures.append(
            "Agent did not finish with "
            "finish_reason='completed'."
        )

    if not duplicate_tool_coverage:
        failures.append(
            "Not every relevant order received a "
            "successful detect_duplicate_payment call."
        )

    if not duplicate_tool_accuracy:
        failures.append(
            "Agent trace does not match the trusted "
            "duplicate-payment oracle."
        )

    if not policy_coverage:
        failures.append(
            "Required policy evidence was not retrieved."
        )

    if not answer_fact_coverage:
        failures.append(
            "Final answer does not cover the required "
            "deterministic facts."
        )

    overall_success = (
        completed
        and duplicate_tool_coverage
        and duplicate_tool_accuracy
        and policy_coverage
        and answer_fact_coverage
        and not any(
            failure.startswith(
                "BENCHMARK_INTEGRITY"
            )
            for failure in failures
        )
    )

    return AgentCaseEvaluation(
        case_id=case.case_id,
        category=case.category,
        customer_id=(
            case.customer_id
        ),
        expected_duplicate=(
            case.expected_duplicate
        ),
        oracle_orders=oracle,
        finish_reason=(
            run.finish_reason
        ),
        completed=completed,
        duplicate_tool_coverage=(
            duplicate_tool_coverage
        ),
        duplicate_tool_accuracy=(
            duplicate_tool_accuracy
        ),
        policy_coverage=(
            policy_coverage
        ),
        answer_fact_coverage=(
            answer_fact_coverage
        ),
        overall_success=(
            overall_success
        ),
        model_calls=(
            run.model_calls
        ),
        tool_calls=len(
            run.tool_calls
        ),
        verification_rejections=len(
            run.verification_failures
        ),
        scope_rejections=len(
            run.scope_rejections
        ),
        prompt_tokens=(
            run.prompt_tokens
        ),
        completion_tokens=(
            run.completion_tokens
        ),
        latency_seconds=(
            elapsed
        ),
        answer=run.answer,
        failures=failures,
    )


# ---------------------------------------------------------
# Summary
# ---------------------------------------------------------

def safe_average(
    values: list[
        int | float
    ],
) -> float:

    if not values:
        return 0.0

    return (
        sum(values)
        / len(values)
    )


def calculate_agent_summary(
    results: list[
        AgentCaseEvaluation
    ],
) -> AgentBenchmarkSummary:

    total = len(results)

    if total == 0:

        return AgentBenchmarkSummary(
            total_cases=0,
            completed_rate=0.0,
            duplicate_tool_coverage_rate=0.0,
            duplicate_tool_accuracy_rate=0.0,
            policy_coverage_rate=0.0,
            answer_fact_coverage_rate=0.0,
            overall_success_rate=0.0,
            average_model_calls=0.0,
            average_tool_calls=0.0,
            average_verification_rejections=0.0,
            average_scope_rejections=0.0,
            average_prompt_tokens=0.0,
            average_completion_tokens=0.0,
            average_latency_seconds=0.0,
        )

    def rate(
        attribute: str,
    ) -> float:

        successful = sum(
            1
            for result in results
            if getattr(
                result,
                attribute,
            )
        )

        return successful / total

    return AgentBenchmarkSummary(
        total_cases=total,

        completed_rate=rate(
            "completed"
        ),

        duplicate_tool_coverage_rate=rate(
            "duplicate_tool_coverage"
        ),

        duplicate_tool_accuracy_rate=rate(
            "duplicate_tool_accuracy"
        ),

        policy_coverage_rate=rate(
            "policy_coverage"
        ),

        answer_fact_coverage_rate=rate(
            "answer_fact_coverage"
        ),

        overall_success_rate=rate(
            "overall_success"
        ),

        average_model_calls=safe_average(
            [
                result.model_calls
                for result in results
            ]
        ),

        average_tool_calls=safe_average(
            [
                result.tool_calls
                for result in results
            ]
        ),

        average_verification_rejections=safe_average(
            [
                result.verification_rejections
                for result in results
            ]
        ),

        average_scope_rejections=safe_average(
            [
                result.scope_rejections
                for result in results
            ]
        ),

        average_prompt_tokens=safe_average(
            [
                result.prompt_tokens
                for result in results
            ]
        ),

        average_completion_tokens=safe_average(
            [
                result.completion_tokens
                for result in results
            ]
        ),

        average_latency_seconds=safe_average(
            [
                result.latency_seconds
                for result in results
            ]
        ),
    )


# ---------------------------------------------------------
# Reporting
# ---------------------------------------------------------

def print_case_result(
    result: AgentCaseEvaluation,
) -> None:

    status = (
        "PASS"
        if result.overall_success
        else "FAIL"
    )

    print()
    print("-" * 72)

    print(
        f"{result.case_id} "
        f"[{result.category}] "
        f"→ {status}"
    )

    print(
        "Customer:",
        result.customer_id,
    )

    print(
        "Finish:",
        result.finish_reason,
    )

    print(
        "Duplicate coverage:",
        result.duplicate_tool_coverage,
    )

    print(
        "Duplicate accuracy:",
        result.duplicate_tool_accuracy,
    )

    print(
        "Policy coverage:",
        result.policy_coverage,
    )

    print(
        "Answer fact coverage:",
        result.answer_fact_coverage,
    )

    print(
        "Model calls:",
        result.model_calls,
    )

    print(
        "Tool calls:",
        result.tool_calls,
    )

    print(
        "Verification rejections:",
        result.verification_rejections,
    )

    print(
        "Scope rejections:",
        result.scope_rejections,
    )

    print(
        "Prompt tokens:",
        result.prompt_tokens,
    )

    print(
        "Completion tokens:",
        result.completion_tokens,
    )

    print(
        "Latency:",
        f"{result.latency_seconds:.2f}s",
    )

    if result.failures:

        print("Failures:")

        for failure in (
            result.failures
        ):

            print(
                f"  - {failure}"
            )


def print_summary(
    summary: AgentBenchmarkSummary,
) -> None:

    print()
    print("=" * 72)
    print("SentinelAI Agent Benchmark Summary")
    print("=" * 72)

    print()
    print(
        f"Cases: "
        f"{summary.total_cases}"
    )

    print(
        "Completed:              "
        f"{summary.completed_rate:.3f}"
    )

    print(
        "Duplicate coverage:     "
        f"{summary.duplicate_tool_coverage_rate:.3f}"
    )

    print(
        "Duplicate accuracy:     "
        f"{summary.duplicate_tool_accuracy_rate:.3f}"
    )

    print(
        "Policy coverage:        "
        f"{summary.policy_coverage_rate:.3f}"
    )

    print(
        "Answer fact coverage:   "
        f"{summary.answer_fact_coverage_rate:.3f}"
    )

    print(
        "Overall success:        "
        f"{summary.overall_success_rate:.3f}"
    )

    print()
    print(
        "Average model calls:    "
        f"{summary.average_model_calls:.2f}"
    )

    print(
        "Average tool calls:     "
        f"{summary.average_tool_calls:.2f}"
    )

    print(
        "Avg verification rejects: "
        f"{summary.average_verification_rejections:.2f}"
    )

    print(
        "Avg scope rejects:        "
        f"{summary.average_scope_rejections:.2f}"
    )

    print(
        "Average prompt tokens:  "
        f"{summary.average_prompt_tokens:.1f}"
    )

    print(
        "Average output tokens:  "
        f"{summary.average_completion_tokens:.1f}"
    )

    print(
        "Average latency:        "
        f"{summary.average_latency_seconds:.2f}s"
    )

    print()
    print("=" * 72)


# ---------------------------------------------------------
# Result persistence
# ---------------------------------------------------------

def save_results(
    output_path: Path,
    summary: AgentBenchmarkSummary,
    results: list[
        AgentCaseEvaluation
    ],
) -> None:

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    payload = {
        "summary": asdict(
            summary
        ),
        "cases": [
            asdict(result)
            for result in results
        ],
    }

    output_path.write_text(
        json.dumps(
            payload,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )