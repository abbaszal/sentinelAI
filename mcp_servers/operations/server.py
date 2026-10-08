from typing import Any

from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError

from database.session import SessionLocal

from sentinel.business.order_rules import (
    OrderNotFoundError,
    calculate_overpayment_amount as rule_calculate_overpayment_amount,
    check_cancellation_eligibility as rule_check_cancellation_eligibility,
    detect_duplicate_payment as rule_detect_duplicate_payment,
    get_completed_payment_total as rule_get_completed_payment_total,
    get_completed_refund_total as rule_get_completed_refund_total,
)


mcp = MCPServer(
    "SentinelAI Operations"
)


@mcp.tool(structured_output=True)
def get_payment_summary(
    order_id: int,
) -> dict[str, Any]:
    """
    Calculate trusted payment totals for an order.

    Returns completed payments, completed refunds and
    any detected overpayment amount.
    """

    try:
        with SessionLocal() as db:
            payment_total = (
                rule_get_completed_payment_total(
                    db,
                    order_id,
                )
            )

            refund_total = (
                rule_get_completed_refund_total(
                    db,
                    order_id,
                )
            )

            overpayment = (
                rule_calculate_overpayment_amount(
                    db,
                    order_id,
                )
            )

            return {
                "order_id": order_id,
                "completed_payment_total": (
                    payment_total
                ),
                "completed_refund_total": (
                    refund_total
                ),
                "overpayment_amount": (
                    overpayment
                ),
            }

    except OrderNotFoundError as exc:
        raise ToolError(
            str(exc)
        ) from exc


@mcp.tool(structured_output=True)
def detect_duplicate_payment(
    order_id: int,
) -> dict[str, Any]:
    """
    Determine whether an order satisfies NovaShop's
    deterministic duplicate-payment rule.
    """

    try:
        with SessionLocal() as db:
            duplicate = (
                rule_detect_duplicate_payment(
                    db,
                    order_id,
                )
            )

            overpayment = (
                rule_calculate_overpayment_amount(
                    db,
                    order_id,
                )
            )

            return {
                "order_id": order_id,
                "duplicate_payment": duplicate,
                "overpayment_amount": (
                    overpayment
                ),
            }

    except OrderNotFoundError as exc:
        raise ToolError(
            str(exc)
        ) from exc


@mcp.tool(structured_output=True)
def check_cancellation_eligibility(
    order_id: int,
) -> dict[str, Any]:
    """
    Determine whether an order can be cancelled under
    NovaShop's deterministic cancellation rule.
    """

    try:
        with SessionLocal() as db:
            eligible = (
                rule_check_cancellation_eligibility(
                    db,
                    order_id,
                )
            )

            return {
                "order_id": order_id,
                "cancellation_eligible": eligible,
            }

    except OrderNotFoundError as exc:
        raise ToolError(
            str(exc)
        ) from exc


if __name__ == "__main__":
    mcp.run()