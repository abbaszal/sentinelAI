import pytest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database.base import Base
from database.models import (
    Customer,
    Order,
    Payment,
    Refund,
    Shipment,
    SupportCase,
)


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite://",
        connect_args={
            "check_same_thread": False
        },
        poolclass=StaticPool,
    )

    TestSessionLocal = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
    )

    Base.metadata.create_all(
        bind=engine
    )

    session = TestSessionLocal()





    customer = Customer(
        id=1,
        name="Test Customer",
        email="test@example.com",
    )

    session.add(customer)





    order = Order(
        id=100,
        customer_id=1,
        status="shipped",
        total_amount=59.99,
    )

    session.add(order)





    payment_1 = Payment(
        id=1000,
        order_id=100,
        amount=59.99,
        status="completed",
        transaction_reference="TEST-TXN-001",
    )

    payment_2 = Payment(
        id=1001,
        order_id=100,
        amount=59.99,
        status="completed",
        transaction_reference="TEST-TXN-002",
    )

    session.add_all([
        payment_1,
        payment_2,
    ])





    shipment = Shipment(
        id=2000,
        order_id=100,
        tracking_id="TEST-TRACK-001",
        status="in_transit",
        carrier="NovaExpress",
    )

    session.add(shipment)





    support_case = SupportCase(
        id=3000,
        customer_id=1,
        subject="Charged twice",
        description=(
            "Customer reports duplicate charge."
        ),
        status="open",
    )

    session.add(support_case)

    session.commit()


    normal_order = Order(
        id=101,
        customer_id=1,
        status="delivered",
        total_amount=100.00,
    )

    session.add(normal_order)
    session.flush()

    normal_payment = Payment(
        id=1002,
        order_id=101,
        amount=100.00,
        status="completed",
        transaction_reference="TEST-TXN-003",
    )

    session.add(normal_payment)

    failed_payment_order = Order(
        id=102,
        customer_id=1,
        status="processing",
        total_amount=75.00,
    )

    session.add(failed_payment_order)
    session.flush()

    successful_payment = Payment(
        id=1003,
        order_id=102,
        amount=75.00,
        status="completed",
        transaction_reference="TEST-TXN-004",
    )

    failed_payment = Payment(
        id=1004,
        order_id=102,
        amount=75.00,
        status="failed",
        transaction_reference="TEST-TXN-005",
    )

    session.add_all([
        successful_payment,
        failed_payment,
    ])


    cancellable_order = Order(
        id=103,
        customer_id=1,
        status="processing",
        total_amount=30.00,
    )

    session.add(cancellable_order)
    session.flush()

    cancellable_payment = Payment(
        id=1005,
        order_id=103,
        amount=30.00,
        status="completed",
        transaction_reference="TEST-TXN-006",
    )

    session.add(cancellable_payment)


    def anyio_backend():
        return "asyncio"


    yield session

    session.close()

    Base.metadata.drop_all(
        bind=engine
    )

    engine.dispose()