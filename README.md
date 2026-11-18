# payabl. API Tester

A branded Streamlit utility for exercising the payabl. gateway API against the
**Sandbox** or **Production** environment.

## Supported flows

| Tab | Endpoint | Notes |
| --- | --- | --- |
| Init (Hosted Payment Page) | `POST /pay/payment/init` | Optional payment-method preselection; opens `start_url` full-page |
| Direct Payments — Apple Pay (119) | `POST /pay/payment/applepay_init` | Opens `redirect_url` |
| Direct Payments — Google Pay (121) | `POST /pay/payment/googlepay_init` | Opens `redirect_url` |
| Direct Payments — Trustly (116) | `POST /pay/backoffice/payment_preauthorize` | `status=2000` + `redirect_url` |
| Direct Payments — PayPal (117) | `POST /pay/backoffice/payment_preauthorize` | Requires `accountname` |
| Authorize | `POST /pay/backoffice/payment_authorize` | Raw card (payment method 1) |
| Pre-Authorize | `POST /pay/backoffice/payment_preauthorize` | Raw card (payment method 1) |
| Capture | `POST /pay/backoffice/payment_capture` | Uses the latest transaction ID |
| Diagnose | `POST /pay/backoffice/tx_diagnose` | Manual, from the Live Response panel; XML response |

All requests are signed automatically (SHA-1 over sorted parameter values + secret,
as required by the gateway).

## Environments

| Environment | Base URL |
| --- | --- |
| Sandbox | `https://sandbox.payabl.com` |
| Production | `https://pay4.payabl.com` |

Switching environment clears Merchant ID, Secret, the latest transaction, the
response panel and session history so sandbox and live state cannot be mixed.
Production is clearly marked **LIVE** — requests there can create real
financial transactions, so every send must be confirmed with a per-request
checkbox showing amount, currency, order and merchant.

## Request validation

Before sending, the app checks amount format, required fields and — for
Authorize / Pre-Authorize — card number (Luhn), expiry, CVC and cardholder
name. In Sandbox, the **Validate before sending** toggle can be switched off
to probe the gateway's own error responses; Production always validates.

Each send generates a fresh Order ID (↻ regenerates it manually), and the
Capture tab is pre-filled with the latest transaction ID.

## Run

Requires Python 3.10+.

Windows (PowerShell):

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
py -m pip install -r requirements.txt
py -m streamlit run app.py
```

macOS / Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

## Tests

```bash
pip install -r requirements-dev.txt
pytest
```

The suite covers validation rules and the main UI flows headlessly via
Streamlit's `AppTest`; the gateway is mocked, so no requests leave the machine.

## Project layout

```text
app.py              Streamlit UI (forms, live preview, response panel, styling)
payabl_client.py    Gateway client: signing, POST, response parsing, masking
validation.py       Client-side request validation (pure functions)
tests/              pytest suite (validation + headless UI tests)
assets/             payabl. logo and payment-method SVGs
CHANGELOG.md        Version history
```

## Security notes

- **Never commit live credentials.** Merchant ID and Secret are entered in the
  sidebar at runtime and are held only in the Streamlit session.
- `app.py` ships with the gateway's **public sandbox** test profiles
  (`gateway_test`, `gateway_test_3d`, `gateway_test_cb`). These are shared test
  accounts, not private credentials.
- Card number, CVC and signature are masked in the request preview and in the
  result view.

## Known issues

- The public sandbox currently returns `-6157 Wrong paymentmethod` for the
  documented card flow (payment method `"1"`); this has been confirmed
  independently via raw cURL.

See [CHANGELOG.md](CHANGELOG.md) for version history.
