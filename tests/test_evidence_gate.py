from sentinel.agent.controlled_agent import (
    AgentToolTrace,
)

from sentinel.verification.evidence_gate import (
    EvidenceGate,
)


# ---------------------------------------------------------
# Helper
# ---------------------------------------------------------

def make_trace(
    tool_name,
    arguments,
    result,
    is_error=False,
):

    return AgentToolTrace(
        step=1,
        tool_name=(
            tool_name
        ),
        arguments=(
            arguments
        ),
        is_error=(
            is_error
        ),
        result=(
            result
        ),
    )


# ---------------------------------------------------------
# Missing evidence
# ---------------------------------------------------------

def test_missing_customer_orders_creates_repair_action():

    verifier = EvidenceGate()

    result = verifier.verify(
        user_request=(
            "Customer 2 says they were "
            "charged twice."
        ),
        tool_traces=[],
        proposed_answer=(
            "I cannot confirm the issue."
        ),
    )

    assert (
        result.passed
        is False
    )

    codes = {
        issue.code
        for issue in result.issues
    }

    assert (
        "missing_customer_orders"
        in codes
    )

    assert (
        len(
            result.required_actions
        )
        == 1
    )

    action = (
        result.required_actions[0]
    )

    assert (
        action.tool_name
        == "get_orders"
    )

    assert (
        action.arguments
        == {
            "customer_id": 2
        }
    )


def test_duplicate_case_creates_action_for_each_missing_order():

    verifier = EvidenceGate()

    traces = [
        make_trace(
            tool_name=(
                "get_orders"
            ),
            arguments={
                "customer_id": 2
            },
            result={
                "customer_id": 2,
                "orders": [
                    {
                        "order_id": 2
                    },
                    {
                        "order_id": 3
                    },
                ],
            },
        ),
    ]

    result = verifier.verify(
        user_request=(
            "Customer 2 says they were "
            "charged twice."
        ),
        tool_traces=(
            traces
        ),
        proposed_answer=(
            "No duplicate payment exists."
        ),
    )

    actions = {
        (
            action.tool_name,
            action.arguments[
                "order_id"
            ],
        )
        for action
        in result.required_actions
        if (
            action.tool_name
            == "detect_duplicate_payment"
        )
    }

    assert actions == {
        (
            "detect_duplicate_payment",
            2,
        ),
        (
            "detect_duplicate_payment",
            3,
        ),
    }


def test_only_missing_duplicate_order_is_requested():

    verifier = EvidenceGate()

    traces = [
        make_trace(
            tool_name=(
                "get_orders"
            ),
            arguments={
                "customer_id": 2
            },
            result={
                "customer_id": 2,
                "orders": [
                    {
                        "order_id": 2
                    },
                    {
                        "order_id": 3
                    },
                ],
            },
        ),

        make_trace(
            tool_name=(
                "detect_duplicate_payment"
            ),
            arguments={
                "order_id": 2
            },
            result={
                "order_id": 2,
                "duplicate_payment": True,
                "overpayment_amount": 49.99,
            },
        ),
    ]

    actions = (
        verifier.recommend_next_actions(
            user_request=(
                "Customer 2 says they were "
                "charged twice."
            ),
            tool_traces=(
                traces
            ),
        )
    )

    duplicate_order_ids = {
        action.arguments[
            "order_id"
        ]
        for action in actions
        if (
            action.tool_name
            == "detect_duplicate_payment"
        )
    }

    assert (
        duplicate_order_ids
        == {
            3
        }
    )


# ---------------------------------------------------------
# Policy evidence
# ---------------------------------------------------------

def test_policy_question_creates_search_action():

    verifier = EvidenceGate()

    traces = [
        make_trace(
            tool_name=(
                "get_orders"
            ),
            arguments={
                "customer_id": 2
            },
            result={
                "customer_id": 2,
                "orders": [
                    {
                        "order_id": 2
                    },
                ],
            },
        ),

        make_trace(
            tool_name=(
                "detect_duplicate_payment"
            ),
            arguments={
                "order_id": 2
            },
            result={
                "order_id": 2,
                "duplicate_payment": True,
                "overpayment_amount": 49.99,
            },
        ),
    ]

    result = verifier.verify(
        user_request=(
            "Customer 2 was charged twice. "
            "What does NovaShop policy say "
            "should happen next?"
        ),
        tool_traces=(
            traces
        ),
        proposed_answer=(
            "Order 2 has an overpayment "
            "of 49.99."
        ),
    )

    policy_actions = [
        action
        for action
        in result.required_actions
        if (
            action.tool_name
            == "search_policy"
        )
    ]

    assert (
        len(
            policy_actions
        )
        == 1
    )


# ---------------------------------------------------------
# Contradictions
# ---------------------------------------------------------

def test_verifier_rejects_duplicate_contradiction():

    verifier = EvidenceGate()

    traces = [
        make_trace(
            tool_name=(
                "get_orders"
            ),
            arguments={
                "customer_id": 2
            },
            result={
                "orders": [
                    {
                        "order_id": 2
                    }
                ]
            },
        ),

        make_trace(
            tool_name=(
                "detect_duplicate_payment"
            ),
            arguments={
                "order_id": 2
            },
            result={
                "order_id": 2,
                "duplicate_payment": True,
                "overpayment_amount": 49.99,
            },
        ),
    ]

    result = verifier.verify(
        user_request=(
            "Customer 2 says they were "
            "charged twice."
        ),
        tool_traces=(
            traces
        ),
        proposed_answer=(
            "No duplicate payments were detected. "
            "The customer appears to be mistaken."
        ),
    )

    codes = {
        issue.code
        for issue in result.issues
    }

    assert (
        "duplicate_contradiction"
        in codes
    )

    assert (
        result.required_actions
        == []
    )


# ---------------------------------------------------------
# NEW:
# Answer completeness
# ---------------------------------------------------------

def test_answer_missing_confirmed_order_is_rejected():

    verifier = EvidenceGate()

    traces = [
        make_trace(
            tool_name=(
                "get_orders"
            ),
            arguments={
                "customer_id": 2
            },
            result={
                "orders": [
                    {
                        "order_id": 2
                    },
                    {
                        "order_id": 3
                    },
                ]
            },
        ),

        make_trace(
            tool_name=(
                "detect_duplicate_payment"
            ),
            arguments={
                "order_id": 2
            },
            result={
                "order_id": 2,
                "duplicate_payment": True,
                "overpayment_amount": 49.99,
            },
        ),

        make_trace(
            tool_name=(
                "detect_duplicate_payment"
            ),
            arguments={
                "order_id": 3
            },
            result={
                "order_id": 3,
                "duplicate_payment": True,
                "overpayment_amount": 39.90,
            },
        ),
    ]

    # This reproduces the failure from our real run:
    # evidence exists for Orders 2 and 3,
    # but the model reports only Order 3.

    result = verifier.verify(
        user_request=(
            "Customer 2 says they were "
            "charged twice."
        ),
        tool_traces=(
            traces
        ),
        proposed_answer=(
            "Order 3 has a confirmed duplicate "
            "payment with an overpayment of $39.90."
        ),
    )

    assert (
        result.passed
        is False
    )

    codes = {
        issue.code
        for issue in result.issues
    }

    assert (
        "missing_duplicate_order_fact"
        in codes
    )

    assert any(
        "Order 2"
        in issue.message
        for issue
        in result.issues
    )


def test_answer_missing_overpayment_amount_is_rejected():

    verifier = EvidenceGate()

    traces = [
        make_trace(
            tool_name=(
                "get_orders"
            ),
            arguments={
                "customer_id": 2
            },
            result={
                "orders": [
                    {
                        "order_id": 2
                    }
                ]
            },
        ),

        make_trace(
            tool_name=(
                "detect_duplicate_payment"
            ),
            arguments={
                "order_id": 2
            },
            result={
                "order_id": 2,
                "duplicate_payment": True,
                "overpayment_amount": 49.99,
            },
        ),
    ]

    result = verifier.verify(
        user_request=(
            "Customer 2 says they were "
            "charged twice."
        ),
        tool_traces=(
            traces
        ),
        proposed_answer=(
            "Order 2 has a confirmed duplicate "
            "payment."
        ),
    )

    codes = {
        issue.code
        for issue in result.issues
    }

    assert (
        "missing_overpayment_fact"
        in codes
    )

    assert (
        result.passed
        is False
    )


def test_answer_with_all_confirmed_duplicate_facts_passes():

    verifier = EvidenceGate()

    traces = [
        make_trace(
            tool_name=(
                "get_orders"
            ),
            arguments={
                "customer_id": 2
            },
            result={
                "orders": [
                    {
                        "order_id": 2
                    },
                    {
                        "order_id": 3
                    },
                ]
            },
        ),

        make_trace(
            tool_name=(
                "detect_duplicate_payment"
            ),
            arguments={
                "order_id": 2
            },
            result={
                "order_id": 2,
                "duplicate_payment": True,
                "overpayment_amount": 49.99,
            },
        ),

        make_trace(
            tool_name=(
                "detect_duplicate_payment"
            ),
            arguments={
                "order_id": 3
            },
            result={
                "order_id": 3,
                "duplicate_payment": True,
                "overpayment_amount": 39.90,
            },
        ),
    ]

    result = verifier.verify(
        user_request=(
            "Customer 2 says they were "
            "charged twice."
        ),
        tool_traces=(
            traces
        ),
        proposed_answer=(
            "Order 2 has a confirmed duplicate "
            "payment with an overpayment of $49.99. "
            "Order 3 has a confirmed duplicate "
            "payment with an overpayment of $39.90."
        ),
    )

    assert (
        result.passed
        is True
    )


def test_negative_duplicate_result_does_not_require_amount():

    verifier = EvidenceGate()

    traces = [
        make_trace(
            tool_name=(
                "get_orders"
            ),
            arguments={
                "customer_id": 1
            },
            result={
                "orders": [
                    {
                        "order_id": 1
                    }
                ]
            },
        ),

        make_trace(
            tool_name=(
                "detect_duplicate_payment"
            ),
            arguments={
                "order_id": 1
            },
            result={
                "order_id": 1,
                "duplicate_payment": False,
                "overpayment_amount": 0.0,
            },
        ),
    ]

    result = verifier.verify(
        user_request=(
            "Customer 1 says they were "
            "charged twice."
        ),
        tool_traces=(
            traces
        ),
        proposed_answer=(
            "The investigation did not confirm "
            "a duplicate payment."
        ),
    )

    assert (
        result.passed
        is True
    )


# ---------------------------------------------------------
# Policy + complete answer
# ---------------------------------------------------------

def test_complete_duplicate_policy_case_passes():

    verifier = EvidenceGate()

    traces = [
        make_trace(
            tool_name=(
                "get_orders"
            ),
            arguments={
                "customer_id": 2
            },
            result={
                "orders": [
                    {
                        "order_id": 2
                    },
                    {
                        "order_id": 3
                    },
                ]
            },
        ),

        make_trace(
            tool_name=(
                "detect_duplicate_payment"
            ),
            arguments={
                "order_id": 2
            },
            result={
                "order_id": 2,
                "duplicate_payment": True,
                "overpayment_amount": 49.99,
            },
        ),

        make_trace(
            tool_name=(
                "detect_duplicate_payment"
            ),
            arguments={
                "order_id": 3
            },
            result={
                "order_id": 3,
                "duplicate_payment": True,
                "overpayment_amount": 39.90,
            },
        ),

        make_trace(
            tool_name=(
                "search_policy"
            ),
            arguments={
                "query": (
                    "duplicate payment verification "
                    "refund excess payment"
                ),
                "top_k": 3,
            },
            result={
                "results": [
                    {
                        "document_id": (
                            "payment_policy"
                        ),
                        "section": (
                            "Duplicate Payments"
                        ),
                        "content": (
                            "When a duplicate payment "
                            "is confirmed, the excess "
                            "amount should normally be "
                            "refunded."
                        ),
                    }
                ]
            },
        ),
    ]

    result = verifier.verify(
        user_request=(
            "Customer 2 says they were charged twice. "
            "Explain what NovaShop policy says should "
            "happen next."
        ),
        tool_traces=(
            traces
        ),
        proposed_answer=(
            "Order 2 has a confirmed duplicate "
            "payment with an overpayment of $49.99. "
            "Order 3 has a confirmed duplicate "
            "payment with an overpayment of $39.90. "
            "NovaShop policy says confirmed excess "
            "payments should normally be refunded."
        ),
    )

    assert (
        result.passed
        is True
    )


# ---------------------------------------------------------
# Proactive guidance
# ---------------------------------------------------------

def test_recommendation_initially_requests_get_orders():

    verifier = EvidenceGate()

    actions = (
        verifier.recommend_next_actions(
            user_request=(
                "Customer 2 says they were "
                "charged twice."
            ),
            tool_traces=[],
        )
    )

    assert (
        len(actions)
        == 1
    )

    assert (
        actions[0].tool_name
        == "get_orders"
    )


def test_recommendation_does_not_repeat_get_orders():

    verifier = EvidenceGate()

    traces = [
        make_trace(
            tool_name=(
                "get_orders"
            ),
            arguments={
                "customer_id": 2
            },
            result={
                "orders": [
                    {
                        "order_id": 2
                    },
                    {
                        "order_id": 3
                    },
                ]
            },
        ),
    ]

    actions = (
        verifier.recommend_next_actions(
            user_request=(
                "Customer 2 says they were "
                "charged twice."
            ),
            tool_traces=(
                traces
            ),
        )
    )

    tool_names = {
        action.tool_name
        for action in actions
    }

    assert (
        "get_orders"
        not in tool_names
    )


def test_recommendation_disappears_after_all_duplicate_checks():

    verifier = EvidenceGate()

    traces = [
        make_trace(
            tool_name=(
                "get_orders"
            ),
            arguments={
                "customer_id": 2
            },
            result={
                "orders": [
                    {
                        "order_id": 2
                    },
                    {
                        "order_id": 3
                    },
                ]
            },
        ),

        make_trace(
            tool_name=(
                "detect_duplicate_payment"
            ),
            arguments={
                "order_id": 2
            },
            result={
                "order_id": 2,
                "duplicate_payment": True,
                "overpayment_amount": 49.99,
            },
        ),

        make_trace(
            tool_name=(
                "detect_duplicate_payment"
            ),
            arguments={
                "order_id": 3
            },
            result={
                "order_id": 3,
                "duplicate_payment": True,
                "overpayment_amount": 39.90,
            },
        ),
    ]

    actions = (
        verifier.recommend_next_actions(
            user_request=(
                "Customer 2 says they were "
                "charged twice."
            ),
            tool_traces=(
                traces
            ),
        )
    )

    assert (
        actions
        == []
    )


def test_proactive_check_does_not_create_answer_completeness_problem():

    verifier = EvidenceGate()

    traces = [
        make_trace(
            tool_name=(
                "get_orders"
            ),
            arguments={
                "customer_id": 2
            },
            result={
                "orders": [
                    {
                        "order_id": 2
                    }
                ]
            },
        ),

        make_trace(
            tool_name=(
                "detect_duplicate_payment"
            ),
            arguments={
                "order_id": 2
            },
            result={
                "order_id": 2,
                "duplicate_payment": True,
                "overpayment_amount": 49.99,
            },
        ),
    ]

    # recommend_next_actions uses proposed_answer=""
    # internally. Answer completeness should not matter
    # during planning.

    actions = (
        verifier.recommend_next_actions(
            user_request=(
                "Customer 2 says they were "
                "charged twice."
            ),
            tool_traces=(
                traces
            ),
        )
    )

    assert (
        actions
        == []
    )