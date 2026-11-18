"""Headless UI tests using Streamlit's AppTest. The gateway is mocked."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).resolve().parents[1] / "app.py")


def gateway_response(text: str = "status=0&transactionid=216771799&errormessage="):
    response = MagicMock()
    response.status_code = 200
    response.text = text
    return response


@pytest.fixture
def post():
    with patch("payabl_client.requests.post", return_value=gateway_response()) as mock:
        yield mock


@pytest.fixture
def app():
    at = AppTest.from_file(APP, default_timeout=60).run()
    assert not at.exception
    return at


def test_capture_field_follows_latest_transaction(app, post):
    assert app.text_input(key="capture_transaction_id").value == ""

    app.button(key="submit_preauthorize").click().run()

    assert post.called
    assert app.text_input(key="capture_transaction_id").value == "216771799"


def test_clear_tx_empties_capture_field(app, post):
    app.button(key="submit_preauthorize").click().run()
    clear = next(b for b in app.sidebar.button if b.label == "Clear TX")
    clear.click().run()
    assert app.text_input(key="capture_transaction_id").value == ""


def test_order_id_refreshes_after_send(app, post):
    before = app.text_input(key="authorize_orderid").value
    app.run()
    assert app.text_input(key="authorize_orderid").value == before  # stable while editing

    app.button(key="submit_authorize").click().run()

    after = app.text_input(key="authorize_orderid").value
    assert after != before and after.startswith("api-test-")
    assert post.call_args.kwargs["data"]["orderid"] == before


def test_order_id_regenerate_button(app):
    before = app.text_input(key="init_orderid").value
    app.button(key="init_orderid_new").click().run()
    assert app.text_input(key="init_orderid").value != before


def test_invalid_card_is_blocked(app, post):
    app.text_input(key="authorize_ccn").set_value("4111111111111112").run()
    app.button(key="submit_authorize").click().run()

    assert not post.called
    assert "Luhn" in app.session_state["last_result"]["error_message"]


def test_validation_can_be_disabled_in_sandbox(app, post):
    app.toggle(key="validate_requests").set_value(False).run()
    app.text_input(key="authorize_ccn").set_value("4111111111111112").run()
    app.button(key="submit_authorize").click().run()
    assert post.called


def test_card_spaces_are_stripped_before_sending(app, post):
    app.text_input(key="authorize_ccn").set_value("5232 0500 0001 0003").run()
    app.button(key="submit_authorize").click().run()
    assert post.call_args.kwargs["data"]["ccn"] == "5232050000010003"


def test_production_requires_live_confirmation(app, post):
    app.radio(key="environment").set_value("Production").run()
    app.text_input(key="merchant_id").set_value("live_mid").run()
    app.text_input(key="secret").set_value("live_secret").run()

    assert app.button(key="submit_authorize").disabled
    assert app.button(key="submit_capture").disabled

    app.checkbox(key="authorize_live_confirm").check().run()
    assert not app.button(key="submit_authorize").disabled

    app.button(key="submit_authorize").click().run()
    assert post.call_args.args[0] == "https://pay4.payabl.com/pay/backoffice/payment_authorize"

    # Confirmation is per request: it resets after sending.
    assert app.checkbox(key="authorize_live_confirm").value is False
    assert app.button(key="submit_authorize").disabled


def test_sandbox_has_no_live_confirmation(app):
    assert not app.button(key="submit_authorize").disabled
    assert not any(cb.key and cb.key.endswith("_live_confirm") for cb in app.checkbox)
