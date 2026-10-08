import pytest

from sentinel.business.order_rules import (
    OrderNotFoundError,
    calculate_overpayment_amount,
    check_cancellation_eligibility,
    detect_duplicate_payment,
    get_completed_payment_total,
)


def test_completed_payment_total_for_duplicate_order(db):
    total = get_completed_payment_total(
        db,
        order_id=100,
    )

    assert total == 119.98


def test_duplicate_payment_detected(db):
    result = detect_duplicate_payment(
        db,
        order_id=100,
    )

    assert result is True


def test_duplicate_overpayment_amount(db):
    amount = calculate_overpayment_amount(
        db,
        order_id=100,
    )

    assert amount == 59.99


def test_normal_order_is_not_duplicate(db):
    result = detect_duplicate_payment(
        db,
        order_id=101,
    )

    assert result is False


def test_failed_payment_does_not_count_as_duplicate(db):
    result = detect_duplicate_payment(
        db,
        order_id=102,
    )

    assert result is False


def test_failed_payment_not_in_completed_total(db):
    total = get_completed_payment_total(
        db,
        order_id=102,
    )

    assert total == 75.00


def test_processing_order_can_be_cancelled(db):
    result = check_cancellation_eligibility(
        db,
        order_id=103,
    )

    assert result is True


def test_shipped_order_cannot_be_cancelled(db):
    result = check_cancellation_eligibility(
        db,
        order_id=100,
    )

    assert result is False


def test_unknown_order_raises_error(db):
    with pytest.raises(OrderNotFoundError):
        detect_duplicate_payment(
            db,
            order_id=999999,
        )