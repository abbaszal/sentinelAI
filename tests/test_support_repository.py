from sentinel.repositories.support_repository import (
    get_customer,
    get_customer_orders,
    get_order,
    get_order_payments,
    get_order_shipments,
    get_previous_cases,
)


def test_get_existing_customer(db):
    customer = get_customer(
        db,
        customer_id=1,
    )

    assert customer is not None
    assert customer.id == 1
    assert customer.name == "Test Customer"


def test_unknown_customer_returns_none(db):
    customer = get_customer(
        db,
        customer_id=999,
    )

    assert customer is None


def test_get_customer_orders(db):
    orders = get_customer_orders(
        db,
        customer_id=1,
    )

    assert len(orders) == 1

    assert orders[0].id == 100

    assert orders[0].total_amount == 59.99


def test_get_order(db):
    order = get_order(
        db,
        order_id=100,
    )

    assert order is not None
    assert order.status == "shipped"


def test_duplicate_payment_case(db):
    payments = get_order_payments(
        db,
        order_id=100,
    )

    assert len(payments) == 2

    assert all(
        payment.status == "completed"
        for payment in payments
    )

    assert payments[0].amount == 59.99

    assert payments[1].amount == 59.99


def test_get_shipment(db):
    shipments = get_order_shipments(
        db,
        order_id=100,
    )

    assert len(shipments) == 1

    assert shipments[0].status == "in_transit"


def test_get_previous_cases(db):
    cases = get_previous_cases(
        db,
        customer_id=1,
    )

    assert len(cases) == 1

    assert cases[0].subject == "Charged twice"