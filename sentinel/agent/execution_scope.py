from dataclasses import dataclass, field
from typing import Any


ORDER_SCOPED_TOOLS = {
    "get_order",
    "get_payment_status",
    "get_shipment_status",
    "get_refunds",
    "get_payment_summary",
    "detect_duplicate_payment",
    "check_cancellation_eligibility",
}


@dataclass
class ScopeDecision:
    allowed: bool
    reason: str | None = None


@dataclass
class ExecutionScope:
    """
    Dynamic authorization scope for one agent run.

    Example:

        User says:
            Customer 2

        Initially:
            customer_id = 2
            allowed_order_ids = unknown

        After:
            get_orders(customer_id=2)

        Scope becomes:
            allowed_order_ids = {2, 3}

        Therefore:

            get_order(2) -> allowed
            get_order(3) -> allowed
            get_order(1) -> denied
    """

    customer_id: int | None = None

    allowed_order_ids: set[int] = field(
        default_factory=set
    )

    orders_discovered: bool = False

    # -----------------------------------------------------
    # Tool authorization
    # -----------------------------------------------------

    def authorize(
        self,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> ScopeDecision:
        """
        Determine whether a requested tool call is within
        the operational scope of this investigation.
        """

        # ---------------------------------------------
        # Customer discovery
        # ---------------------------------------------

        if tool_name in {
            "get_customer_summary",
            "get_customer_support_cases",
            "get_orders",
        }:

            requested_customer_id = (
                arguments.get(
                    "customer_id"
                )
            )

            if (
                self.customer_id is not None
                and requested_customer_id
                != self.customer_id
            ):
                return ScopeDecision(
                    allowed=False,
                    reason=(
                        "The investigation is scoped to "
                        f"customer {self.customer_id}. "
                        "Access to customer "
                        f"{requested_customer_id} is "
                        "outside the current scope."
                    ),
                )

            return ScopeDecision(
                allowed=True
            )

        # ---------------------------------------------
        # Order-specific tools
        # ---------------------------------------------

        if (
            tool_name
            in ORDER_SCOPED_TOOLS
        ):

            order_id = arguments.get(
                "order_id"
            )

            if not isinstance(
                order_id,
                int,
            ):
                return ScopeDecision(
                    allowed=False,
                    reason=(
                        "An integer order_id is required."
                    ),
                )

            # If customer scope exists, discover their
            # orders BEFORE using arbitrary order IDs.
            if (
                self.customer_id is not None
                and not self.orders_discovered
            ):
                return ScopeDecision(
                    allowed=False,
                    reason=(
                        "Order access is not authorized "
                        "yet. First call get_orders for "
                        f"customer {self.customer_id} "
                        "to establish the customer's "
                        "valid order IDs."
                    ),
                )

            if (
                self.orders_discovered
                and order_id
                not in self.allowed_order_ids
            ):
                return ScopeDecision(
                    allowed=False,
                    reason=(
                        f"Order {order_id} is outside "
                        "the authorized order set for "
                        "this investigation: "
                        f"{sorted(self.allowed_order_ids)}."
                    ),
                )

        return ScopeDecision(
            allowed=True
        )

    # -----------------------------------------------------
    # Update scope from trusted results
    # -----------------------------------------------------

    def observe_tool_result(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        result: Any,
        is_error: bool,
    ) -> None:
        """
        Expand/update authorization scope only from
        successful trusted tool results.
        """

        if is_error:
            return

        if tool_name != "get_orders":
            return

        requested_customer_id = (
            arguments.get(
                "customer_id"
            )
        )

        if (
            self.customer_id is not None
            and requested_customer_id
            != self.customer_id
        ):
            return

        if not isinstance(
            result,
            dict,
        ):
            return

        orders = result.get(
            "orders"
        )

        if not isinstance(
            orders,
            list,
        ):
            return

        discovered_ids: set[int] = set()

        for order in orders:

            if not isinstance(
                order,
                dict,
            ):
                continue

            order_id = order.get(
                "order_id"
            )

            if isinstance(
                order_id,
                int,
            ):
                discovered_ids.add(
                    order_id
                )

        self.allowed_order_ids = (
            discovered_ids
        )

        self.orders_discovered = True