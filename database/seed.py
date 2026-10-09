from datetime import datetime, timedelta
import random

from database.models import (
    Customer,
    Order,
    Payment,
    Refund,
    Shipment,
    SupportCase,
)
from database.session import SessionLocal






RANDOM_SEED = 42
NUMBER_OF_CUSTOMERS = 30

random.seed(RANDOM_SEED)


FIRST_NAMES = [
    "Alice",
    "Marco",
    "Giulia",
    "Luca",
    "Sofia",
    "Matteo",
    "Emma",
    "Leonardo",
    "Anna",
    "Andrea",
    "Francesca",
    "Davide",
    "Chiara",
    "Alessandro",
    "Sara",
    "Simone",
    "Elena",
    "Federico",
    "Martina",
    "Stefano",
    "Laura",
    "Giorgio",
    "Valentina",
    "Nicola",
    "Elisa",
    "Antonio",
    "Silvia",
    "Paolo",
    "Beatrice",
    "Roberto",
]

LAST_NAMES = [
    "Rossi",
    "Bianchi",
    "Romano",
    "Ferrari",
    "Esposito",
    "Ricci",
    "Marino",
    "Greco",
    "Bruno",
    "Gallo",
    "Conti",
    "De Luca",
    "Mancini",
    "Costa",
    "Giordano",
    "Rizzo",
    "Lombardi",
    "Moretti",
    "Barbieri",
    "Fontana",
    "Santoro",
    "Mariani",
    "Rinaldi",
    "Caruso",
    "Ferrara",
    "Galli",
    "Martini",
    "Leone",
    "Longo",
    "Gentile",
]


ORDER_AMOUNTS = [
    19.99,
    24.50,
    29.99,
    39.90,
    49.99,
    59.99,
    75.50,
    89.99,
    99.90,
    120.00,
    149.99,
    199.00,
]






def make_date(days_ago: int) -> datetime:
    return datetime.utcnow() - timedelta(days=days_ago)


def create_payment(
    db,
    order,
    payment_number,
    status="completed",
    amount=None,
):
    payment = Payment(
        order_id=order.id,
        amount=amount if amount is not None else order.total_amount,
        status=status,
        transaction_reference=f"TXN-{payment_number:05d}",
        created_at=order.created_at,
    )

    db.add(payment)

    return payment


def create_shipment(
    db,
    order,
    shipment_number,
    status,
):
    shipment = Shipment(
        order_id=order.id,
        tracking_id=f"NOVA-{shipment_number:05d}",
        status=status,
        carrier="NovaExpress",
    )

    db.add(shipment)

    return shipment


def create_support_case(
    db,
    customer,
    subject,
    description,
    status="open",
):
    support_case = SupportCase(
        customer_id=customer.id,
        subject=subject,
        description=description,
        status=status,
    )

    db.add(support_case)

    return support_case






def seed_database() -> None:

    db = SessionLocal()

    try:

        existing_customer = db.query(Customer).first()

        if existing_customer:
            print(
                "Database already contains data. "
                "Delete sentinel.db before reseeding."
            )
            return

        payment_counter = 1
        shipment_counter = 1

        customers = []





        for index in range(NUMBER_OF_CUSTOMERS):

            first_name = FIRST_NAMES[index]
            last_name = LAST_NAMES[index]

            customer = Customer(
                name=f"{first_name} {last_name}",
                email=(
                    f"{first_name.lower()}."
                    f"{last_name.lower().replace(' ', '')}"
                    f"@example.com"
                ),
                created_at=make_date(
                    random.randint(30, 700)
                ),
            )

            db.add(customer)

            customers.append(customer)

        db.flush()





        for index, customer in enumerate(customers, start=1):



            number_of_orders = random.randint(1, 3)

            for order_index in range(number_of_orders):

                order_amount = random.choice(ORDER_AMOUNTS)

                days_ago = random.randint(1, 120)

                order = Order(
                    customer_id=customer.id,
                    status="processing",
                    total_amount=order_amount,
                    created_at=make_date(days_ago),
                )

                db.add(order)
                db.flush()






                if index % 6 == 1:

                    order.status = "delivered"

                    create_payment(
                        db,
                        order,
                        payment_counter,
                    )

                    payment_counter += 1

                    create_shipment(
                        db,
                        order,
                        shipment_counter,
                        "delivered",
                    )

                    shipment_counter += 1






                elif index % 6 == 2:

                    order.status = "shipped"

                    create_payment(
                        db,
                        order,
                        payment_counter,
                    )

                    payment_counter += 1


                    create_payment(
                        db,
                        order,
                        payment_counter,
                    )

                    payment_counter += 1

                    create_shipment(
                        db,
                        order,
                        shipment_counter,
                        "in_transit",
                    )

                    shipment_counter += 1

                    if order_index == 0:

                        create_support_case(
                            db,
                            customer,
                            subject="Charged twice",
                            description=(
                                f"Customer believes order "
                                f"{order.id} was charged twice."
                            ),
                        )






                elif index % 6 == 3:

                    order.status = "processing"

                    create_payment(
                        db,
                        order,
                        payment_counter,
                    )

                    payment_counter += 1






                elif index % 6 == 4:

                    order.status = "cancelled"

                    create_payment(
                        db,
                        order,
                        payment_counter,
                    )

                    payment_counter += 1

                    if order_index == 0:

                        create_support_case(
                            db,
                            customer,
                            subject="Charged after cancellation",
                            description=(
                                f"Customer cancelled order "
                                f"{order.id} but sees a completed "
                                f"payment."
                            ),
                        )






                elif index % 6 == 5:

                    order.status = "payment_failed"

                    create_payment(
                        db,
                        order,
                        payment_counter,
                        status="failed",
                    )

                    payment_counter += 1

                    if order_index == 0:

                        create_support_case(
                            db,
                            customer,
                            subject="Payment problem",
                            description=(
                                f"Payment for order "
                                f"{order.id} failed."
                            ),
                        )






                else:

                    order.status = "delivered"

                    create_payment(
                        db,
                        order,
                        payment_counter,
                    )

                    payment_counter += 1

                    create_shipment(
                        db,
                        order,
                        shipment_counter,
                        "delivered",
                    )

                    shipment_counter += 1

                    refund_amount = round(
                        order.total_amount * 0.25,
                        2,
                    )

                    refund = Refund(
                        order_id=order.id,
                        amount=refund_amount,
                        status="completed",
                        reason="Partial refund for damaged item",
                    )

                    db.add(refund)

                    if order_index == 0:

                        create_support_case(
                            db,
                            customer,
                            subject="Damaged item",
                            description=(
                                f"Customer reports damage "
                                f"for order {order.id}."
                            ),
                            status="resolved",
                        )

        db.commit()





        customer_count = db.query(Customer).count()
        order_count = db.query(Order).count()
        payment_count = db.query(Payment).count()
        shipment_count = db.query(Shipment).count()
        refund_count = db.query(Refund).count()
        support_case_count = db.query(SupportCase).count()

        print()
        print("NovaShop synthetic database created!")
        print("------------------------------------")
        print(f"Customers:     {customer_count}")
        print(f"Orders:        {order_count}")
        print(f"Payments:      {payment_count}")
        print(f"Shipments:     {shipment_count}")
        print(f"Refunds:       {refund_count}")
        print(f"Support cases: {support_case_count}")
        print("------------------------------------")

    except Exception:

        db.rollback()

        raise

    finally:

        db.close()


if __name__ == "__main__":
    seed_database()