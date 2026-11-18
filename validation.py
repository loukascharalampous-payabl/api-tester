"""Client-side request validation for the payabl. API Tester.

Pure functions only (no Streamlit), so they can be unit-tested directly.
Each validator returns a list of human-readable error messages; an empty
list means the request looks sendable.
"""

from __future__ import annotations

import re
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any, Iterable

_CARD_SEPARATORS = re.compile(r"[\s-]")

INIT_REQUIRED = ["currency", "orderid", "email", "firstname", "lastname", "customerip", "url_return"]


def normalize_ccn(value: Any) -> str:
    """Strip spaces and dashes so '5232 0500 0001 0003' is sent as digits."""
    return _CARD_SEPARATORS.sub("", str(value or ""))


def luhn_valid(number: str) -> bool:
    if not number or not number.isdigit():
        return False

    total = 0
    for index, char in enumerate(reversed(number)):
        digit = int(char)
        if index % 2 == 1:
            digit *= 2
            if digit > 9:
                digit -= 9
        total += digit
    return total % 10 == 0


def amount_errors(value: Any) -> list[str]:
    text = str(value or "").strip()
    if not text:
        return ["Amount is required."]

    try:
        amount = Decimal(text)
    except InvalidOperation:
        return [f"Amount '{text}' is not a number (use a dot as decimal separator)."]

    if not amount.is_finite() or amount <= 0:
        return ["Amount must be greater than 0."]

    exponent = amount.as_tuple().exponent
    if isinstance(exponent, int) and exponent < -2:
        return ["Amount can have at most 2 decimal places."]

    return []


def required_errors(params: dict[str, Any], names: Iterable[str]) -> list[str]:
    missing = [name for name in names if not str(params.get(name) or "").strip()]
    if not missing:
        return []
    return ["Missing required field(s): " + ", ".join(missing) + "."]


def card_errors(params: dict[str, Any], today: date | None = None) -> list[str]:
    today = today or date.today()
    errors: list[str] = []

    ccn = normalize_ccn(params.get("ccn"))
    if not ccn:
        errors.append("Card number is required.")
    elif not ccn.isdigit() or not 12 <= len(ccn) <= 19:
        errors.append("Card number must be 12–19 digits.")
    elif not luhn_valid(ccn):
        errors.append("Card number fails the Luhn check — probably a typo.")

    month_text = str(params.get("exp_month") or "").strip()
    year_text = str(params.get("exp_year") or "").strip()

    month_ok = month_text.isdigit() and 1 <= int(month_text) <= 12
    year_ok = year_text.isdigit() and len(year_text) in (2, 4)

    if not month_ok:
        errors.append("Expiry month must be 1–12.")
    if not year_ok:
        errors.append("Expiry year must be 2 or 4 digits.")

    if month_ok and year_ok:
        year = int(year_text) + (2000 if len(year_text) == 2 else 0)
        if (year, int(month_text)) < (today.year, today.month):
            errors.append(f"Card expired ({month_text}/{year_text}).")

    cvc = str(params.get("cvc_code") or "").strip()
    if not (cvc.isdigit() and len(cvc) in (3, 4)):
        errors.append("CVC must be 3 or 4 digits.")

    if not str(params.get("cardholder_name") or "").strip():
        errors.append("Cardholder name is required.")

    return errors


def init_errors(params: dict[str, Any]) -> list[str]:
    errors = amount_errors(params.get("amount"))
    errors += required_errors(params, INIT_REQUIRED)
    return errors


def card_payment_errors(params: dict[str, Any], today: date | None = None) -> list[str]:
    errors = amount_errors(params.get("amount"))
    errors += required_errors(params, ["currency", "orderid", "payment_method"])
    errors += card_errors(params, today)
    return errors


def format_errors(errors: list[str]) -> str:
    return "\n".join(f"- {error}" for error in errors)
