from sqlalchemy import select
from sqlalchemy.orm import Session

from database.models import (
    Customer,
    Order,
    Payment,
    Refund,
    Shipment,
    SupportCase,
)


def get_customer(
    db: Session,
    customer_id: int,
) -> Customer | None:
    return db.get(Customer, customer_id)


def get_customer_orders(
    db: Session,
    customer_id: int,
) -> list[Order]:
    statement = (
        select(Order)
        .where(Order.customer_id == customer_id)
        .order_by(Order.created_at.desc())
    )

    return list(
        db.scalars(statement).all()
    )


def get_order(
    db: Session,
    order_id: int,
) -> Order | None:
    return db.get(Order, order_id)


def get_order_payments(
    db: Session,
    order_id: int,
) -> list[Payment]:
    statement = (
        select(Payment)
        .where(Payment.order_id == order_id)
        .order_by(Payment.created_at.asc())
    )

    return list(
        db.scalars(statement).all()
    )


def get_order_shipments(
    db: Session,
    order_id: int,
) -> list[Shipment]:
    statement = (
        select(Shipment)
        .where(Shipment.order_id == order_id)
    )

    return list(
        db.scalars(statement).all()
    )


def get_order_refunds(
    db: Session,
    order_id: int,
) -> list[Refund]:
    statement = (
        select(Refund)
        .where(Refund.order_id == order_id)
        .order_by(Refund.created_at.asc())
    )

    return list(
        db.scalars(statement).all()
    )


def get_previous_cases(
    db: Session,
    customer_id: int,
) -> list[SupportCase]:
    statement = (
        select(SupportCase)
        .where(
            SupportCase.customer_id == customer_id
        )
        .order_by(
            SupportCase.created_at.desc()
        )
    )

    return list(
        db.scalars(statement).all()
    )