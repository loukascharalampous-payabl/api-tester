# Changelog

All notable changes to the payabl. API Tester. Newest first.

## v6.17 — Safer sends

- **Capture auto-fill fixed:** the Capture Transaction ID field now updates to
  the latest transaction ID after every response (previously it kept its first
  value, so pre-auth → capture needed a manual copy). Clear TX and switching
  environment also clear it.
- **Fresh Order ID per request:** Init, Direct Payments, Authorize and
  Pre-Authorize generate a new Order ID after each send (previously the same
  ID was reused for the whole session). A ↻ button regenerates it on demand.
- **LIVE confirmation:** in Production every send button (Init, Direct
  Payments, Authorize, Pre-Authorize, Capture) stays disabled until a
  per-request confirmation showing amount, currency, order and merchant is
  ticked. The confirmation resets after each send. Disabled primary buttons
  are now visibly greyed out.
- **Client-side validation** (new `validation.py`): amount format, required
  fields, card number (12–19 digits + Luhn), expiry month/year and not
  expired, CVC, cardholder name. Spaces and dashes in card numbers are
  stripped before sending. A **Validate before sending** toggle lets Sandbox
  users switch it off to test gateway-side errors; Production always
  validates.
- Added a pytest suite (`tests/`) covering validation and the UI flows above
  with the gateway mocked.

## v6.16 — Init purpose

- Added a **Purpose** field to the Init / Hosted Payment Page flow.
- The value is sent as the `purpose` parameter to `/pay/payment/init`.
- Purpose appears immediately in the live Request Preview.
- The field is blank by default.

## v6.15 — Live request preview

- Removed Streamlit form batching from the request-builder tabs.
- Init, Direct Payments, Authorize and Pre-Authorize previews now update immediately as fields change.
- Capture now also has a live request preview.
- Send actions remain explicit buttons, so editing fields never sends a request automatically.
- Merchant ID and signature still appear only in the actual sent request/result view.

## v6.14 — Authorize / Pre-Authorize payment methods

- Authorize and Pre-Authorize now show only payment methods supported by those raw-card forms.
- Currently this means **Cards (1)** only.
- Apple Pay, Google Pay, Trustly and PayPal remain under **Direct Payments**.
- All enabled methods remain available through **Init / Hosted Payment Page**.

## v6.13 — Visible API category tabs

- Restored strong visual separation between API categories.
- Tabs are now compact bordered buttons rather than plain text.
- Active category uses a clear dark selected state.
- Hover state uses the payabl. green accent.
- Kept the rest of the simplified v6.12 UI unchanged.

## v6.12 — Fixed sidebar/main layout

- Fixed the main workspace being rendered underneath the permanent sidebar.
- Main content now explicitly starts to the right of the 300 px sidebar.
- Added fallback selectors for different Streamlit DOM variants.
- Added a small responsive adjustment for narrower desktop windows.

## v6.11 — UI simplification

- Widened the fixed left panel to 300 px.
- Reduced visual noise across the header, workspace and result panel.
- Removed the extra profile chip from the top header.
- Flattened shadows and simplified status panels.
- Made section labels quieter.
- Kept all existing payment functionality and the two-column workflow unchanged.

## v6.10

- Left settings panel is permanently fixed and always visible.
- Removed Streamlit sidebar collapse/expand controls.
- Main workspace reserves the sidebar width so content does not sit underneath it.

## v6.9 — Direct Payments: Apple Pay, Google Pay, Trustly, PayPal

Added a dedicated **Direct Payments** tab.

### Apple Pay
- `payment_method=119`
- `POST /pay/payment/applepay_init`
- parses `redirect_url`
- full-page **Open Apple Pay** action

### Google Pay
- `payment_method=121`
- `POST /pay/payment/googlepay_init`
- no Google-specific `gateway` or `gatewayMerchantId` fields are needed
- parses `redirect_url`
- full-page **Open Google Pay** action

### Trustly
- `payment_method=116`
- `POST /pay/backoffice/payment_preauthorize`
- dedicated country/language handling
- success / failed / return URLs
- parses `status=2000` + `redirect_url`
- full-page **Open Trustly** action

### PayPal
- `payment_method=117`
- `POST /pay/backoffice/payment_preauthorize`
- includes required `accountname`
- success / failed / return URLs
- parses `status=2000` + `redirect_url`
- full-page **Open PayPal** action

The existing Diagnose button works with transaction IDs returned by these flows.

## v6.8 — Hosted Payment Page Init

Added **Init** as the first transaction tab.

Endpoint:
- Sandbox: `https://sandbox.payabl.com/pay/payment/init`
- Production: `https://pay4.payabl.com/pay/payment/init`

Features:
- all enabled merchant payment methods by default
- optional payment-method preselection
- required HPP transaction/customer fields
- collapsed address and advanced fields
- automatic merchant ID + SHA-1 signature
- parses `errorcode`, `sessionid`, `transactionid`, `start_url`, `user_id`
- **Open Hosted Payment Page** button appears in Live Response when `start_url` is returned
- HPP is opened as a full-page link, not embedded in an iframe

## v6.7

- Fixed `StreamlitAPIException` when clicking **Load sandbox profile**.
- `apply_profile()` no longer tries to change the Environment radio widget state
  after that widget has already been instantiated.
- Sandbox profile loading now only updates Base URL, Merchant ID and Secret.

## v6.6 — Explicit Sandbox / Production environment

The sidebar now has an explicit environment selector:

- **Sandbox** → `https://sandbox.payabl.com`
- **Production** → `https://pay4.payabl.com`

Behaviour:

- Base URL is selected automatically and is read-only.
- Sandbox quick profiles are only available in Sandbox.
- Production is clearly marked as **LIVE** in both the sidebar and top header.
- Switching environments clears Merchant ID, Secret, latest transaction, response,
  Diagnose result, and session history so sandbox/live state cannot be mixed.

## v6.5

- Fixed the Diagnose button shrinking after the clear-result icon was added.
- Compact button styling now applies only to the `✕` clear icon.
- Diagnose and other Live Response action buttons stay full width.

## v6.4

- Added a compact **✕ clear icon** in the top-right of the Live Response panel.
- Clicking it clears both the main response and any Diagnose result.
- Removed the redundant `Clear result` button from the sidebar.

## v6.3 — Diagnose interface

The Live Response panel now includes a **Diagnose transaction** button whenever
the latest gateway response contains a transaction ID.

It sends:

```text
POST /pay/backoffice/tx_diagnose
type=tx
transactionid=<latest transaction ID>
```

The response is XML and is shown in three views:

- parsed diagnosis / transaction steps
- raw XML
- signed diagnose request

The Diagnose interface is intentionally manual and is not triggered
automatically for every transaction.

## v6.2

- Payment method selector moved outside the Streamlit form.
- The selected payment method logo now refreshes immediately when the dropdown changes.
- Request fields remain inside the form, so only the selector causes an instant rerun.

## v6.1

- Removed the native Streamlit top header / Deploy toolbar from the UI.
- Restored the original payment-method SVG artwork supplied for this project.
- Payment logos are now bundled locally under `assets/` instead of using generic online icon placeholders.

## v6.0 — UI / UX refresh

This version uses the supplied **official payabl. logo** and the 2025 brand palette.

#### Brand application
- Mint Green `#7CDDAE`
- Charcoal Black `#181818`
- Absolute White `#FFFFFF`
- Soft Orchid `#D597DC`
- Soft Ash `#D7E2E2`
- Pine Teal `#08785F`
- Figtree for the digital interface
- rounded brand dash as a subtle accent

#### Layout
- left: transaction workspace
- right: sticky live-response panel
- primary status, error and transaction ID remain immediately visible
- customer / advanced fields are collapsed to reduce scrolling

#### Card section
The Card details area now has a **solid Charcoal Black payabl. background**
with Mint Green branding and white input surfaces.

#### Logo
The provided official `payabl-logo-black.svg` is bundled under:

```text
assets/payabl-logo-black.svg
```

It is used on a light background with generous surrounding whitespace.
