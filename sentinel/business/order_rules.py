from sqlalchemy.orm import Session

from sentinel.repositories.support_repository import (
    get_order,
    get_order_payments,
    get_order_refunds,
    get_order_shipments,
)


class OrderNotFoundError(Exception):
    """Raised when a requested order does not exist."""



def get_completed_payment_total(
    db: Session,
    order_id: int,
) -> float:
    order = get_order(db, order_id)

    if order is None:
        raise OrderNotFoundError(
            f"Order {order_id} does not exist."
        )

    payments = get_order_payments(
        db,
        order_id,
    )

    total = sum(
        payment.amount
        for payment in payments
        if payment.status == "completed"
    )

    return round(total, 2)


def get_completed_refund_total(
    db: Session,
    order_id: int,
) -> float:
    order = get_order(db, order_id)

    if order is None:
        raise OrderNotFoundError(
            f"Order {order_id} does not exist."
        )

    refunds = get_order_refunds(
        db,
        order_id,
    )

    total = sum(
        refund.amount
        for refund in refunds
        if refund.status == "completed"
    )

    return round(total, 2)


def calculate_overpayment_amount(
    db: Session,
    order_id: int,
) -> float:
    order = get_order(db, order_id)

    if order is None:
        raise OrderNotFoundError(
            f"Order {order_id} does not exist."
        )

    payment_total = get_completed_payment_total(
        db,
        order_id,
    )

    overpayment = (
        payment_total
        - order.total_amount
    )

    return round(
        max(overpayment, 0.0),
        2,
    )





def detect_duplicate_payment(
    db: Session,
    order_id: int,
) -> bool:
    order = get_order(db, order_id)

    if order is None:
        raise OrderNotFoundError(
            f"Order {order_id} does not exist."
        )

    payments = get_order_payments(
        db,
        order_id,
    )

    completed_payments = [
        payment
        for payment in payments
        if payment.status == "completed"
    ]

    if len(completed_payments) < 2:
        return False

    overpayment = calculate_overpayment_amount(
        db,
        order_id,
    )

    return overpayment > 0




def check_cancellation_eligibility(
    db: Session,
    order_id: int,
) -> bool:
    order = get_order(db, order_id)

    if order is None:
        raise OrderNotFoundError(
            f"Order {order_id} does not exist."
        )

    if order.status != "processing":
        return False

    shipments = get_order_shipments(
        db,
        order_id,
    )

    if shipments:
        return False

    return True