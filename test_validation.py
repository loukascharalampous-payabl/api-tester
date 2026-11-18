from datetime import date

import pytest

from validation import (
    amount_errors,
    card_errors,
    card_payment_errors,
    init_errors,
    luhn_valid,
    normalize_ccn,
)

TODAY = date(2026, 11, 18)

VALID_CARD = {
    "ccn": "5232050000010003",
    "exp_month": "12",
    "exp_year": "2040",
    "cvc_code": "123",
    "cardholder_name": "Test Customer",
}


@pytest.mark.parametrize("number", ["5232050000010003", "4111111111111111", "378282246310005"])
def test_luhn_valid_numbers(number):
    assert luhn_valid(number)


@pytest.mark.parametrize("number", ["4111111111111112", "", "41111111abcd1111"])
def test_luhn_invalid_numbers(number):
    assert not luhn_valid(number)


def test_normalize_ccn_strips_spaces_and_dashes():
    assert normalize_ccn(" 5232 0500-0001 0003 ") == "5232050000010003"


@pytest.mark.parametrize("value", ["1.23", "10", "0.01", "1000.5"])
def test_amount_ok(value):
    assert amount_errors(value) == []


@pytest.mark.parametrize(
    "value, fragment",
    [
        ("", "required"),
        ("abc", "not a number"),
        ("1,23", "not a number"),
        ("0", "greater than 0"),
        ("-5", "greater than 0"),
        ("NaN", "greater than 0"),
        ("1.234", "2 decimal"),
    ],
)
def test_amount_errors(value, fragment):
    errors = amount_errors(value)
    assert len(errors) == 1 and fragment in errors[0]


def test_valid_card_has_no_errors():
    assert card_errors(VALID_CARD, TODAY) == []


def test_card_with_spaces_is_accepted():
    assert card_errors({**VALID_CARD, "ccn": "5232 0500 0001 0003"}, TODAY) == []


@pytest.mark.parametrize(
    "override, fragment",
    [
        ({"ccn": ""}, "Card number is required"),
        ({"ccn": "12345"}, "12–19 digits"),
        ({"ccn": "4111111111111112"}, "Luhn"),
        ({"exp_month": "13"}, "month"),
        ({"exp_year": "240"}, "year"),
        ({"exp_month": "10", "exp_year": "2026"}, "expired"),
        ({"exp_month": "10", "exp_year": "26"}, "expired"),
        ({"cvc_code": "12"}, "CVC"),
        ({"cardholder_name": " "}, "Cardholder"),
    ],
)
def test_card_errors(override, fragment):
    errors = card_errors({**VALID_CARD, **override}, TODAY)
    assert any(fragment in e for e in errors), errors


def test_current_month_is_not_expired():
    assert card_errors({**VALID_CARD, "exp_month": "11", "exp_year": "2026"}, TODAY) == []


def test_card_payment_requires_order_id():
    params = {**VALID_CARD, "amount": "1.23", "currency": "EUR", "payment_method": "1", "orderid": ""}
    assert any("orderid" in e for e in card_payment_errors(params, TODAY))


def test_init_errors_lists_missing_fields():
    errors = init_errors({"amount": "1.23", "currency": "EUR", "orderid": "x"})
    assert errors == [
        "Missing required field(s): email, firstname, lastname, customerip, url_return."
    ]
