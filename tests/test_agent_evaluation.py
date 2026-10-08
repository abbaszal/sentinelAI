from sentinel.agent.controlled_agent import (
    AgentRunResult,
    AgentToolTrace,
)

from sentinel.evaluation.agent_eval import (
    OracleOrderResult,
    answer_mentions_amount,
    answer_mentions_order,
    grade_answer_fact_coverage,
    grade_duplicate_tool_accuracy,
    grade_duplicate_tool_coverage,
)


def make_duplicate_trace(
    order_id: int,
    duplicate: bool,
    overpayment: float,
):

    return AgentToolTrace(
        step=1,
        tool_name=(
            "detect_duplicate_payment"
        ),
        arguments={
            "order_id": order_id
        },
        is_error=False,
        result={
            "order_id": order_id,
            "duplicate_payment": (
                duplicate
            ),
            "overpayment_amount": (
                overpayment
            ),
        },
        source=(
            "verification_gate"
        ),
    )


def make_run(
    traces,
    answer="",
):

    return AgentRunResult(
        answer=answer,
        finish_reason="completed",
        model_calls=1,
        tool_calls=traces,
    )


def test_duplicate_tool_coverage_passes():

    oracle = [
        OracleOrderResult(
            order_id=2,
            duplicate_payment=True,
            overpayment_amount=49.99,
        ),
        OracleOrderResult(
            order_id=3,
            duplicate_payment=True,
            overpayment_amount=39.90,
        ),
    ]

    run = make_run(
        [
            make_duplicate_trace(
                2,
                True,
                49.99,
            ),
            make_duplicate_trace(
                3,
                True,
                39.90,
            ),
        ]
    )

    assert (
        grade_duplicate_tool_coverage(
            oracle,
            run,
        )
        is True
    )


def test_duplicate_tool_coverage_detects_missing_order():

    oracle = [
        OracleOrderResult(
            order_id=2,
            duplicate_payment=True,
            overpayment_amount=49.99,
        ),
        OracleOrderResult(
            order_id=3,
            duplicate_payment=True,
            overpayment_amount=39.90,
        ),
    ]

    run = make_run(
        [
            make_duplicate_trace(
                3,
                True,
                39.90,
            )
        ]
    )

    assert (
        grade_duplicate_tool_coverage(
            oracle,
            run,
        )
        is False
    )


def test_duplicate_tool_accuracy():

    oracle = [
        OracleOrderResult(
            order_id=2,
            duplicate_payment=True,
            overpayment_amount=49.99,
        )
    ]

    run = make_run(
        [
            make_duplicate_trace(
                2,
                True,
                49.99,
            )
        ]
    )

    assert (
        grade_duplicate_tool_accuracy(
            oracle,
            run,
        )
        is True
    )


def test_answer_mentions_order():

    answer = (
        "Order 2 has a duplicate payment."
    )

    assert (
        answer_mentions_order(
            answer,
            2,
        )
        is True
    )

    assert (
        answer_mentions_order(
            answer,
            3,
        )
        is False
    )


def test_answer_mentions_amount():

    answer = (
        "The overpayment is $49.99."
    )

    assert (
        answer_mentions_amount(
            answer,
            49.99,
        )
        is True
    )


def test_positive_answer_requires_every_duplicate_order():

    oracle = [
        OracleOrderResult(
            order_id=2,
            duplicate_payment=True,
            overpayment_amount=49.99,
        ),
        OracleOrderResult(
            order_id=3,
            duplicate_payment=True,
            overpayment_amount=39.90,
        ),
    ]

    incomplete_answer = (
        "Order 3 has a duplicate payment "
        "with an overpayment of $39.90."
    )

    assert (
        grade_answer_fact_coverage(
            oracle,
            incomplete_answer,
        )
        is False
    )


def test_positive_answer_with_all_facts_passes():

    oracle = [
        OracleOrderResult(
            order_id=2,
            duplicate_payment=True,
            overpayment_amount=49.99,
        ),
        OracleOrderResult(
            order_id=3,
            duplicate_payment=True,
            overpayment_amount=39.90,
        ),
    ]

    answer = (
        "Order 2 has a duplicate payment "
        "with an overpayment of $49.99. "
        "Order 3 also has a duplicate "
        "payment with an overpayment "
        "of $39.90."
    )

    assert (
        grade_answer_fact_coverage(
            oracle,
            answer,
        )
        is True
    )