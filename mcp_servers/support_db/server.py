from typing import Any

from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError

from database.session import SessionLocal

from sentinel.repositories.support_repository import (
    get_customer,
    get_customer_orders,
    get_order as repository_get_order,
    get_order_payments,
    get_order_refunds,
    get_order_shipments,
    get_previous_cases,
)


mcp = MCPServer(
    "SentinelAI Support Database"
)


@mcp.tool(structured_output=True)
def get_customer_summary(
    customer_id: int,
) -> dict[str, Any]:
    """
    Return basic information about a NovaShop customer,
    including counts of their orders and support cases.
    """

    with SessionLocal() as db:
        customer = get_customer(
            db,
            customer_id,
        )

        if customer is None:
            raise ToolError(
                f"Customer {customer_id} does not exist."
            )

        orders = get_customer_orders(
            db,
            customer_id,
        )

        cases = get_previous_cases(
            db,
            customer_id,
        )

        return {
            "customer_id": customer.id,
            "name": customer.name,
            "email": customer.email,
            "order_count": len(orders),
            "support_case_count": len(cases),
        }


@mcp.tool(structured_output=True)
def get_orders(
    customer_id: int,
) -> dict[str, Any]:
    """
    Return all orders belonging to a NovaShop customer.
    """

    with SessionLocal() as db:
        customer = get_customer(
            db,
            customer_id,
        )

        if customer is None:
            raise ToolError(
                f"Customer {customer_id} does not exist."
            )

        orders = get_customer_orders(
            db,
            customer_id,
        )

        return {
            "customer_id": customer_id,
            "orders": [
                {
                    "order_id": order.id,
                    "status": order.status,
                    "total_amount": order.total_amount,
                    "created_at": (
                        order.created_at.isoformat()
                        if order.created_at
                        else None
                    ),
                }
                for order in orders
            ],
        }


@mcp.tool(structured_output=True)
def get_order(
    order_id: int,
) -> dict[str, Any]:
    """
    Return the basic operational record for one order.
    """

    with SessionLocal() as db:
        order = repository_get_order(
            db,
            order_id,
        )

        if order is None:
            raise ToolError(
                f"Order {order_id} does not exist."
            )

        return {
            "order_id": order.id,
            "customer_id": order.customer_id,
            "status": order.status,
            "total_amount": order.total_amount,
            "created_at": (
                order.created_at.isoformat()
                if order.created_at
                else None
            ),
        }


@mcp.tool(structured_output=True)
def get_payment_status(
    order_id: int,
) -> dict[str, Any]:
    """
    Return every payment record associated with an order.

    Multiple payment records are returned because an order
    may contain duplicate, failed, or retried payments.
    """

    with SessionLocal() as db:
        order = repository_get_order(
            db,
            order_id,
        )

        if order is None:
            raise ToolError(
                f"Order {order_id} does not exist."
            )

        payments = get_order_payments(
            db,
            order_id,
        )

        return {
            "order_id": order_id,
            "payments": [
                {
                    "payment_id": payment.id,
                    "amount": payment.amount,
                    "status": payment.status,
                    "transaction_reference": (
                        payment.transaction_reference
                    ),
                    "created_at": (
                        payment.created_at.isoformat()
                        if payment.created_at
                        else None
                    ),
                }
                for payment in payments
            ],
        }


@mcp.tool(structured_output=True)
def get_shipment_status(
    order_id: int,
) -> dict[str, Any]:
    """
    Return shipment records associated with an order.
    """

    with SessionLocal() as db:
        order = repository_get_order(
            db,
            order_id,
        )

        if order is None:
            raise ToolError(
                f"Order {order_id} does not exist."
            )

        shipments = get_order_shipments(
            db,
            order_id,
        )

        return {
            "order_id": order_id,
            "shipments": [
                {
                    "shipment_id": shipment.id,
                    "tracking_id": shipment.tracking_id,
                    "status": shipment.status,
                    "carrier": shipment.carrier,
                }
                for shipment in shipments
            ],
        }


@mcp.tool(structured_output=True)
def get_refunds(
    order_id: int,
) -> dict[str, Any]:
    """
    Return all refund records associated with an order.
    """

    with SessionLocal() as db:
        order = repository_get_order(
            db,
            order_id,
        )

        if order is None:
            raise ToolError(
                f"Order {order_id} does not exist."
            )

        refunds = get_order_refunds(
            db,
            order_id,
        )

        return {
            "order_id": order_id,
            "refunds": [
                {
                    "refund_id": refund.id,
                    "amount": refund.amount,
                    "status": refund.status,
                    "reason": refund.reason,
                    "created_at": (
                        refund.created_at.isoformat()
                        if refund.created_at
                        else None
                    ),
                }
                for refund in refunds
            ],
        }


@mcp.tool(structured_output=True)
def get_customer_support_cases(
    customer_id: int,
) -> dict[str, Any]:
    """
    Return previous support cases belonging to a customer.
    """

    with SessionLocal() as db:
        customer = get_customer(
            db,
            customer_id,
        )

        if customer is None:
            raise ToolError(
                f"Customer {customer_id} does not exist."
            )

        cases = get_previous_cases(
            db,
            customer_id,
        )

        return {
            "customer_id": customer_id,
            "cases": [
                {
                    "case_id": case.id,
                    "subject": case.subject,
                    "description": case.description,
                    "status": case.status,
                    "created_at": (
                        case.created_at.isoformat()
                        if case.created_at
                        else None
                    ),
                }
                for case in cases
            ],
        }


if __name__ == "__main__":
    mcp.run()