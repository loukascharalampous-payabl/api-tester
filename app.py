from __future__ import annotations

import base64
from datetime import datetime
import json
from pathlib import Path
import uuid

import streamlit as st

from payabl_client import PayablClient, mask_payload
from validation import (
    INIT_REQUIRED,
    amount_errors,
    card_payment_errors,
    format_errors,
    init_errors,
    normalize_ccn,
    required_errors,
)


# ---------------------------------------------------------------------
# App / brand setup
# ---------------------------------------------------------------------

ROOT = Path(__file__).resolve().parent
ASSET_DIR = ROOT / "assets"
LOGO_PATH = ASSET_DIR / "payabl-logo-black.svg"

st.set_page_config(
    page_title="payabl. API Tester",
    page_icon="💳",
    layout="wide",
    initial_sidebar_state="expanded",
)


def svg_data_uri(path: Path) -> str:
    raw = path.read_bytes()
    encoded = base64.b64encode(raw).decode("ascii")
    return f"data:image/svg+xml;base64,{encoded}"


PAYABL_LOGO_URI = svg_data_uri(LOGO_PATH)

def asset_uri(filename: str) -> str:
    path = ASSET_DIR / filename
    return svg_data_uri(path) if path.exists() else ""

# Official 2025 payabl. brand colours from the supplied brand book.
# Primary:
#   Mint Green      #7CDDAE
#   Charcoal Black  #181818
#   Absolute White  #FFFFFF
#   Soft Orchid     #D597DC
#   Soft Ash        #D7E2E2
#   Pine Teal       #08785F
# Secondary:
#   Graphite Grey   #2B2B2B
#   Charcoal Navy   #1C2A3A
#   Deep Teal       #014D4E
#   Eggplant Purple #3F2A4D
#   Deep Brand Green#1EAF89

st.markdown(
    """
    <style>
      @import url('https://fonts.googleapis.com/css2?family=Figtree:wght@400;500;600;700&display=swap');

      :root {
        --mint: #7CDDAE;
        --charcoal: #181818;
        --white: #FFFFFF;
        --orchid: #D597DC;
        --ash: #D7E2E2;
        --pine: #08785F;

        --graphite: #2B2B2B;
        --navy: #1C2A3A;
        --deep-teal: #014D4E;
        --eggplant: #3F2A4D;
        --brand-green: #1EAF89;

        --soft-bg: #F9FCFC;
        --line: rgba(24,24,24,.09);
        --muted: rgba(24,24,24,.60);
        --danger: #C83A4B;
        --warning: #AD7415;
      }

      html, body, [class*="css"], .stApp {
        font-family: "Figtree", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      }

      /* Remove Streamlit's own top chrome/toolbar so it cannot cover app content. */
      header[data-testid="stHeader"],
      div[data-testid="stToolbar"],
      div[data-testid="stDecoration"],
      div[data-testid="stStatusWidget"] {
        display: none !important;
      }

      .stApp {
        padding-top: 0 !important;
      }


      .stApp {
        background: #F7FAFA;
        color: var(--charcoal);
      }

      .block-container {
        padding-top: 0.55rem;
        padding-bottom: 1rem;
        max-width: 1560px;
      }

      /* ---------------- Header ---------------- */

      .payabl-topbar {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 24px;
        background: rgba(255,255,255,.96);
        border: 1px solid var(--line);
        border-radius: 14px;
        padding: 11px 16px;
        margin-bottom: 10px;
        box-shadow: 0 4px 14px rgba(24,24,24,.04);
      }

      .payabl-brand-wrap {
        display: flex;
        align-items: center;
        gap: 20px;
        min-width: 0;
      }

      .payabl-logo-safe {
        display: flex;
        align-items: center;
        padding: 7px 12px 7px 4px;
        min-width: 138px;
      }

      .payabl-logo-safe img {
        display: block;
        width: 132px;
        height: auto;
      }

      .brand-divider {
        height: 36px;
        width: 1px;
        background: var(--ash);
      }

      .app-name {
        min-width: 0;
      }

      .app-name-title {
        color: var(--charcoal);
        font-size: 1.02rem;
        font-weight: 700;
        line-height: 1.15;
      }

      .app-name-sub {
        color: var(--muted);
        font-size: .82rem;
        margin-top: 4px;
      }

      .top-statuses {
        display: flex;
        align-items: center;
        justify-content: flex-end;
        gap: 8px;
        flex-wrap: wrap;
      }

      .top-chip {
        display: inline-flex;
        align-items: center;
        gap: 7px;
        border: 1px solid var(--line);
        background: var(--soft-bg);
        color: var(--charcoal);
        border-radius: 999px;
        padding: 7px 11px;
        font-size: .78rem;
        font-weight: 600;
        white-space: nowrap;
      }

      .top-chip.mint {
        background: rgba(124,221,174,.16);
        border-color: rgba(8,120,95,.14);
        color: var(--pine);
      }

      .top-chip.live {
        background: rgba(200,58,75,.10);
        border-color: rgba(200,58,75,.22);
        color: #A52738;
      }

      .live-dot {
        display: inline-block;
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background: #C83A4B;
        box-shadow: 0 0 0 4px rgba(200,58,75,.10);
      }

      .brand-dash {
        display: inline-block;
        width: 18px;
        height: 5px;
        border-radius: 999px;
        background: linear-gradient(90deg, var(--mint), var(--brand-green));
        vertical-align: middle;
      }

      /* ---------------- Main panels ---------------- */

      .workspace-heading {
        display: flex;
        align-items: center;
        gap: 10px;
        margin: 2px 0 4px;
      }

      .workspace-title {
        color: var(--charcoal);
        font-size: 1.12rem;
        font-weight: 700;
      }

      .workspace-sub {
        color: var(--muted);
        font-size: .86rem;
        margin: 0 0 10px;
      }

      .section-label {
        color: var(--muted);
        font-size: .78rem;
        font-weight: 600;
        text-transform: none;
        letter-spacing: 0;
        margin: 4px 0 6px;
      }

      .payment-method-meta {
        color: var(--muted);
        font-size: .78rem;
        margin-top: -6px;
        margin-bottom: 8px;
      }

      .direct-method-note {
        border: 1px solid rgba(8,120,95,.14);
        background: linear-gradient(135deg, rgba(124,221,174,.10), rgba(249,252,252,.95));
        border-radius: 13px;
        padding: 10px 12px;
        margin: 6px 0 10px;
        color: var(--muted);
        font-size: .78rem;
      }

      .direct-method-note strong {
        color: var(--charcoal);
      }

      .pm-logo-shell {
        height: 58px;
        display: flex;
        align-items: center;
        justify-content: center;
        border: 1px solid var(--line);
        background: var(--white);
        border-radius: 13px;
        padding: 8px 12px;
      }

      .pm-logo-shell img {
        max-width: 118px;
        max-height: 38px;
        object-fit: contain;
      }

      /* ---------------- Branded card section ---------------- */

      .card-section-heading {
        display: flex;
        align-items: center;
        gap: 10px;
        color: #FFFFFF;
        font-size: .98rem;
        font-weight: 700;
        margin: 0 0 3px;
      }

      .card-section-copy {
        color: rgba(255,255,255,.62);
        font-size: .79rem;
        margin-bottom: 11px;
      }

      /* Keyed Streamlit containers receive st-key-<key> */
      .st-key-authorize_card_section,
      .st-key-preauthorize_card_section {
        background: var(--charcoal);
        border: 1px solid #2B2B2B;
        border-radius: 18px;
        padding: 16px 17px 12px;
        margin: 10px 0 12px;
        box-shadow:
          inset 0 1px 0 rgba(255,255,255,.04),
          0 11px 28px rgba(24,24,24,.10);
      }

      .st-key-authorize_card_section label,
      .st-key-preauthorize_card_section label,
      .st-key-authorize_card_section [data-testid="stWidgetLabel"] p,
      .st-key-preauthorize_card_section [data-testid="stWidgetLabel"] p {
        color: rgba(255,255,255,.88) !important;
      }

      .st-key-authorize_card_section div[data-baseweb="input"] > div,
      .st-key-preauthorize_card_section div[data-baseweb="input"] > div,
      .st-key-authorize_card_section div[data-baseweb="select"] > div,
      .st-key-preauthorize_card_section div[data-baseweb="select"] > div {
        background: #FFFFFF !important;
        border-color: rgba(255,255,255,.12) !important;
      }

      .st-key-authorize_card_section input,
      .st-key-preauthorize_card_section input {
        color: #181818 !important;
      }

      .st-key-authorize_card_section [data-baseweb="select"] *,
      .st-key-preauthorize_card_section [data-baseweb="select"] * {
        color: #181818 !important;
      }

      /* ---------------- Buttons ---------------- */

      .stButton > button[kind="primary"],
      .stFormSubmitButton > button[kind="primary"] {
        background: var(--pine);
        border-color: var(--pine);
        color: #FFFFFF;
        border-radius: 11px;
        font-weight: 700;
        min-height: 42px;
        box-shadow: 0 7px 18px rgba(8,120,95,.18);
      }

      .stButton > button[kind="primary"]:hover,
      .stFormSubmitButton > button[kind="primary"]:hover {
        background: #0F9773;
        border-color: #0F9773;
      }

      /* Locked until confirmed (e.g. LIVE confirmation in Production). */
      .stButton > button[kind="primary"]:disabled,
      .stButton > button[kind="primary"]:disabled:hover {
        background: var(--ash, #D7E2E2);
        border-color: var(--ash, #D7E2E2);
        color: rgba(24,24,24,.45);
        box-shadow: none;
        cursor: not-allowed;
      }

      /* ---------------- Inputs / tabs / expanders ---------------- */

      div[data-baseweb="input"] > div,
      div[data-baseweb="select"] > div {
        border-radius: 10px !important;
      }


      div[data-testid="stTabs"] button[aria-selected="true"] {
        color: var(--pine);
      }

      div[data-testid="stTabs"] [data-baseweb="tab-highlight"] {
        background-color: var(--brand-green);
      }

      div[data-testid="stExpander"] {
        border: 1px solid var(--line);
        border-radius: 13px;
        background: rgba(255,255,255,.74);
      }

      /* ---------------- Result panel ---------------- */

      .st-key-live_result {
        position: sticky;
        top: 0.75rem;
        align-self: flex-start;
        background: #FFFFFF;
        border: 1px solid var(--line);
        border-radius: 14px;
        padding: 14px 15px 12px;
        box-shadow: 0 4px 14px rgba(24,24,24,.04);
      }

      /* Only the clear-result icon is compact. */
      .st-key-clear_live_result_icon .stButton > button {
        min-height: 34px !important;
        height: 34px !important;
        width: 34px !important;
        padding: 0 !important;
        border-radius: 999px !important;
        border: 1px solid var(--line) !important;
        background: #FFFFFF !important;
        color: var(--charcoal) !important;
        font-size: 1rem !important;
        font-weight: 700 !important;
        box-shadow: none !important;
      }

      .st-key-clear_live_result_icon .stButton > button:hover {
        background: #F9FCFC !important;
        border-color: rgba(8,120,95,.22) !important;
        color: var(--pine) !important;
      }

      /* Diagnose and any other response actions stay full width. */
      .st-key-live_result .stButton > button {
        width: 100%;
      }


      .result-head {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 12px;
        margin-bottom: 3px;
      }

      .result-title {
        color: var(--charcoal);
        font-size: 1.04rem;
        font-weight: 700;
      }

      .result-sub {
        color: var(--muted);
        font-size: .80rem;
        margin-bottom: 10px;
      }

      .result-empty {
        border-radius: 15px;
        padding: 28px 18px;
        border: 1px dashed rgba(8,120,95,.24);
        background: linear-gradient(135deg, rgba(124,221,174,.10), rgba(215,226,226,.18));
        text-align: center;
        color: var(--muted);
      }

      .result-empty strong {
        display: block;
        color: var(--charcoal);
        margin-bottom: 5px;
      }

      .result-banner {
        border-radius: 10px;
        padding: 9px 11px;
        margin: 6px 0 9px;
        border-left: 3px solid transparent;
      }

      .result-banner.success {
        background: rgba(124,221,174,.16);
        border-left-color: var(--pine);
      }

      .result-banner.warning {
        background: rgba(213,151,220,.12);
        border-left-color: var(--orchid);
      }

      .result-banner.error {
        background: rgba(200,58,75,.07);
        border-left-color: var(--danger);
      }

      .diagnose-panel {
        border: 1px solid rgba(8,120,95,.16);
        background: linear-gradient(135deg, rgba(124,221,174,.09), rgba(249,252,252,.95));
        border-radius: 14px;
        padding: 11px 12px;
        margin: 10px 0;
      }

      .diagnose-title {
        display: flex;
        align-items: center;
        justify-content: space-between;
        color: var(--charcoal);
        font-size: .86rem;
        font-weight: 700;
        margin-bottom: 3px;
      }

      .diagnose-copy {
        color: var(--muted);
        font-size: .75rem;
      }


      .result-banner-title {
        color: var(--charcoal);
        font-weight: 700;
        font-size: .90rem;
      }

      .result-banner-meta {
        color: var(--muted);
        font-size: .75rem;
        margin-top: 3px;
      }

      div[data-testid="stMetric"] {
        background: var(--soft-bg);
        border: 1px solid var(--line);
        padding: 7px 9px;
        border-radius: 12px;
      }

      div[data-testid="stMetric"] label {
        font-size: .70rem;
      }

      div[data-testid="stMetric"] [data-testid="stMetricValue"] {
        font-size: .94rem;
      }

      /* ---------------- Sidebar ---------------- */

      /* Permanent left settings panel: always visible, no collapse control. */
      section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #FFFFFF 0%, #F9FCFC 100%);
        border-right: 1px solid var(--line);
        min-width: 300px !important;
        max-width: 300px !important;
        width: 300px !important;
        transform: none !important;
        position: fixed !important;
        left: 0 !important;
        top: 0 !important;
        bottom: 0 !important;
        height: 100vh !important;
        z-index: 100 !important;
      }

      section[data-testid="stSidebar"] > div {
        width: 300px !important;
        min-width: 300px !important;
        max-width: 300px !important;
        height: 100vh !important;
        overflow-y: auto !important;
      }

      /*
        The sidebar is intentionally position:fixed, so Streamlit no longer
        reserves layout space for it automatically. Offset the real main
        container explicitly.
      */
      section[data-testid="stMain"] {
        margin-left: 300px !important;
        width: calc(100% - 300px) !important;
      }

      div[data-testid="stMain"] {
        margin-left: 300px !important;
        width: calc(100% - 300px) !important;
      }

      main[data-testid="stMain"] {
        margin-left: 300px !important;
        width: calc(100% - 300px) !important;
      }

      /* Fallback for Streamlit builds where the main area is a plain <main>. */
      div[data-testid="stAppViewContainer"] > main {
        margin-left: 300px !important;
        width: calc(100% - 300px) !important;
      }

      /* Hide Streamlit's sidebar collapse / expand affordances. */
      [data-testid="stSidebarCollapseButton"],
      [data-testid="collapsedControl"],
      button[data-testid="baseButton-headerNoPadding"],
      section[data-testid="stSidebar"] button[kind="header"] {
        display: none !important;
        visibility: hidden !important;
        pointer-events: none !important;
      }


      .sidebar-brand {
        padding: 6px 4px 10px;
      }

      .sidebar-brand img {
        width: 112px;
        height: auto;
      }

      .sidebar-label {
        color: var(--muted);
        font-size: .74rem;
        font-weight: 600;
        text-transform: none;
        letter-spacing: 0;
        margin: 8px 0 4px;
      }

      /* Responsive */
      @media (max-width: 900px) {
        .payabl-topbar {
          align-items: flex-start;
          flex-direction: column;
        }

        .brand-divider {
          display: none;
        }

        .top-statuses {
          justify-content: flex-start;
        }

        .st-key-live_result {
          position: static;
        }
      }
    
      @media (max-width: 1150px) {
        section[data-testid="stSidebar"] {
          min-width: 280px !important;
          max-width: 280px !important;
          width: 280px !important;
        }

        section[data-testid="stSidebar"] > div {
          min-width: 280px !important;
          max-width: 280px !important;
          width: 280px !important;
        }

        section[data-testid="stMain"],
        div[data-testid="stMain"],
        main[data-testid="stMain"],
        div[data-testid="stAppViewContainer"] > main {
          margin-left: 280px !important;
          width: calc(100% - 280px) !important;
        }
      }


      /* API category navigation: clearly visible, compact tabs. */
      div[data-testid="stTabs"] [role="tablist"] {
        gap: 8px !important;
        border-bottom: 1px solid var(--line) !important;
        padding: 0 0 10px 0 !important;
        margin-bottom: 10px !important;
      }

      div[data-testid="stTabs"] button[role="tab"] {
        background: #FFFFFF !important;
        border: 1px solid #D7E2E2 !important;
        border-radius: 10px !important;
        min-height: 38px !important;
        padding: 7px 14px !important;
        color: #465154 !important;
        font-weight: 600 !important;
        font-size: .84rem !important;
        line-height: 1.1 !important;
        box-shadow: none !important;
      }

      div[data-testid="stTabs"] button[role="tab"]:hover {
        border-color: #9ECDBB !important;
        background: #F8FCFA !important;
        color: #08785F !important;
      }

      div[data-testid="stTabs"] button[role="tab"][aria-selected="true"] {
        background: #181818 !important;
        border-color: #181818 !important;
        color: #FFFFFF !important;
        box-shadow: 0 2px 7px rgba(24,24,24,.10) !important;
      }

      /* Hide Streamlit's thin active-tab underline; the selected tab itself
         now provides the active state. */
      div[data-testid="stTabs"] [data-baseweb="tab-highlight"] {
        display: none !important;
      }

      div[data-testid="stTabs"] [data-baseweb="tab-border"] {
        display: none !important;
      }

</style>
    """,
    unsafe_allow_html=True,
)


# ---------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------

PAYMENT_METHODS = [
    {
        "id": "1",
        "label": "Cards",
        "asset": "CreditCard.svg",
        "supported": True,
        "note": "Raw card flow supported.",
    },
    {
        "id": "116",
        "label": "Trustly",
        "asset": "Trustly.svg",
        "supported": False,
        "note": "Not implemented in this tester yet.",
    },
    {
        "id": "117",
        "label": "PayPal",
        "asset": "PayPal.svg",
        "supported": False,
        "note": "Not implemented in this tester yet.",
    },
    {
        "id": "118",
        "label": "EPS",
        "asset": "EPS.svg",
        "supported": False,
        "note": "Not implemented in this tester yet.",
    },
    {
        "id": "119",
        "label": "Apple Pay",
        "asset": "ApplePay.svg",
        "supported": False,
        "note": "Not implemented in this tester yet.",
    },
    {
        "id": "120",
        "label": "Przelewy24",
        "asset": "P24.svg",
        "supported": False,
        "note": "Not implemented in this tester yet.",
    },
    {
        "id": "121",
        "label": "Google Pay",
        "asset": "GooglePay.svg",
        "supported": False,
        "note": "Not implemented in this tester yet.",
    },
    {
        "id": "123",
        "label": "Instant Bank Transfer / Open Banking",
        "asset": "Instant Bank Transfer.svg",
        "supported": False,
        "note": "Not implemented in this tester yet.",
    },
    {
        "id": "139",
        "label": "SEPA Direct Debit",
        "asset": "CreditCard.svg",
        "supported": False,
        "note": "Not implemented in this tester yet.",
    },
    {
        "id": "200",
        "label": "Multibanco / MB Way",
        "asset": "CreditCard.svg",
        "supported": False,
        "note": "Not implemented in this tester yet.",
    },
    {
        "id": "213",
        "label": "Wero",
        "asset": "Wero.svg",
        "supported": False,
        "note": "Not implemented in this tester yet.",
    },
]

PM_OPTIONS = [f'{pm["label"]} ({pm["id"]})' for pm in PAYMENT_METHODS]
PM_BY_OPTION = {f'{pm["label"]} ({pm["id"]})': pm for pm in PAYMENT_METHODS}

SUPPORTED_CARD_PAYMENT_METHODS = [
    pm for pm in PAYMENT_METHODS if pm.get("supported")
]
SUPPORTED_CARD_PM_OPTIONS = [
    f'{pm["label"]} ({pm["id"]})' for pm in SUPPORTED_CARD_PAYMENT_METHODS
]

DIRECT_PAYMENT_METHODS = [
    {
        "id": "119",
        "label": "Apple Pay",
        "asset": "ApplePay.svg",
        "flow": "wallet",
        "sandbox_profile": "gateway_test",
        "description": "Dedicated Apple Pay initialization flow.",
    },
    {
        "id": "121",
        "label": "Google Pay",
        "asset": "GooglePay.svg",
        "flow": "wallet",
        "sandbox_profile": "gateway_test_cb",
        "description": "Dedicated Google Pay initialization flow.",
    },
    {
        "id": "116",
        "label": "Trustly",
        "asset": "Trustly.svg",
        "flow": "apm",
        "sandbox_profile": "gateway_test",
        "description": "Online banking redirect flow via Pre-Authorization.",
    },
    {
        "id": "117",
        "label": "PayPal",
        "asset": "PayPal.svg",
        "flow": "apm",
        "sandbox_profile": "gateway_test",
        "description": "PayPal redirect flow via Pre-Authorization.",
    },
]

DIRECT_PM_OPTIONS = [f'{pm["label"]} ({pm["id"]})' for pm in DIRECT_PAYMENT_METHODS]
DIRECT_PM_BY_OPTION = {
    f'{pm["label"]} ({pm["id"]})': pm for pm in DIRECT_PAYMENT_METHODS
}

ENVIRONMENT_URLS = {
    "Sandbox": "https://sandbox.payabl.com",
    "Production": "https://pay4.payabl.com",
}

SANDBOX_PROFILES = {
    "Manual": {
        "base_url": "https://sandbox.payabl.com",
        "merchant_id": "",
        "secret": "",
    },
    "Public sandbox - gateway_test": {
        "base_url": "https://sandbox.payabl.com",
        "merchant_id": "gateway_test",
        "secret": "b185",
    },
    "Public sandbox - gateway_test_3d": {
        "base_url": "https://sandbox.payabl.com",
        "merchant_id": "gateway_test_3d",
        "secret": "b185",
    },
    "Public sandbox - gateway_test_cb": {
        "base_url": "https://sandbox.payabl.com",
        "merchant_id": "gateway_test_cb",
        "secret": "b185",
    },
}

DEFAULT_STATE = {
    "last_transaction_id": "",
    "history": [],
    "last_result": None,
    "diagnose_result": None,
    "environment": "Sandbox",
    "base_url": "https://sandbox.payabl.com",
    "merchant_id": "",
    "secret": "",
    "timeout": 30,
    "sandbox_profile": "Manual",
    "capture_transaction_id": "",
    "validate_requests": True,
}

for key, default in DEFAULT_STATE.items():
    if key not in st.session_state:
        st.session_state[key] = default


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------

def clean_optional(value: str) -> str | None:
    value = (value or "").strip()
    return value if value else None


def make_order_id() -> str:
    return f"api-test-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:5]}"


def apply_profile(profile_name: str) -> None:
    p = SANDBOX_PROFILES[profile_name]

    # This action is only shown while the Sandbox environment is selected.
    # Do not mutate st.session_state.environment here: once the Environment
    # radio widget is instantiated, Streamlit does not allow its state to be
    # reassigned during the same run.
    st.session_state.base_url = ENVIRONMENT_URLS["Sandbox"]
    st.session_state.merchant_id = p["merchant_id"]
    st.session_state.secret = p["secret"]


def change_environment() -> None:
    environment = st.session_state.environment

    # Never carry credentials or transaction state between sandbox and live.
    st.session_state.base_url = ENVIRONMENT_URLS[environment]
    st.session_state.merchant_id = ""
    st.session_state.secret = ""
    st.session_state.sandbox_profile = "Manual"
    st.session_state.last_transaction_id = ""
    set_capture_transaction_id("")
    st.session_state.last_result = None
    st.session_state.diagnose_result = None
    st.session_state.history = []


# Streamlit forbids writing a widget's session-state key after that widget
# has been rendered in the current run. Values that must change in response
# to a send are therefore queued here and applied just before the widget is
# rendered on the next run (every send handler ends with st.rerun()).

def set_capture_transaction_id(value: str) -> None:
    st.session_state.pending_capture_tx = value


def refresh_order_id(prefix: str) -> None:
    # Used as an on_click callback, which runs before widgets are rendered.
    st.session_state[f"{prefix}_orderid"] = make_order_id()


def mark_request_sent(prefix: str) -> None:
    """Call once a request has been handed to the gateway client."""
    st.session_state[f"{prefix}_orderid_stale"] = True
    st.session_state[f"{prefix}_live_confirm_reset"] = True


def order_id_input(prefix: str) -> str:
    key = f"{prefix}_orderid"
    if key not in st.session_state or st.session_state.pop(f"{prefix}_orderid_stale", False):
        st.session_state[key] = make_order_id()

    field_col, button_col = st.columns([1, 0.22], vertical_alignment="bottom")
    with field_col:
        value = st.text_input("Order ID", key=key)
    with button_col:
        st.button(
            "↻",
            key=f"{prefix}_orderid_new",
            help="Generate a new order ID",
            on_click=refresh_order_id,
            args=(prefix,),
            use_container_width=True,
        )
    return value


def validation_enabled() -> bool:
    # Production always validates; Sandbox may switch it off to probe
    # gateway-side error handling with deliberately invalid input.
    return st.session_state.environment == "Production" or bool(
        st.session_state.get("validate_requests", True)
    )


def live_send_confirmed(prefix: str, summary: str) -> bool:
    """In Production, require an explicit per-request confirmation."""
    if st.session_state.environment != "Production":
        return True

    key = f"{prefix}_live_confirm"
    if st.session_state.pop(f"{key}_reset", False):
        st.session_state[key] = False

    return st.checkbox(f"Confirm **LIVE** request: {summary}", key=key)


def live_summary(params: dict) -> str:
    return (
        f"{params.get('amount') or '—'} {params.get('currency') or ''} · "
        f"order {params.get('orderid') or '—'} · merchant {st.session_state.merchant_id or '—'}"
    )


def save_result(label: str, result) -> None:
    st.session_state.diagnose_result = None
    data = result.data
    transaction_id = str(data.get("transactionid", "") or data.get("transid", "")).strip()

    if transaction_id and transaction_id.lower() != "undef":
        st.session_state.last_transaction_id = transaction_id
        set_capture_transaction_id(transaction_id)

    status = str(data.get("status", ""))
    error_code = str(data.get("errorcode", ""))
    error_message = str(data.get("errormessage", "") or data.get("errmsg", ""))

    # Backoffice flows primarily use `status`; HPP Init primarily uses
    # `errorcode`. Treat any explicit non-zero value from either field as failure.
    ok = (
        result.http_status == 200
        and status in {"", "0", "2000"}
        and error_code in {"", "0"}
    )

    banner_type = "success"
    banner_title = f"{label} completed."

    if ok and status == "2000":
        banner_type = "warning"
        banner_title = f"{label} returned pending / 3DS flow."
    elif not ok:
        banner_type = "error"
        banner_title = f"{label} returned an error or decline."

    st.session_state.last_result = {
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "operation": label,
        "ok": ok,
        "banner_type": banner_type,
        "banner_title": banner_title,
        "http_status": result.http_status,
        "status": status,
        "error_code": error_code,
        "error_message": error_message,
        "transaction_id": transaction_id,
        "session_id": str(data.get("sessionid", "") or ""),
        "start_url": str(data.get("start_url", "") or ""),
        "redirect_url": str(data.get("redirect_url", "") or ""),
        "orderid": data.get("orderid", ""),
        "parsed": data,
        "raw": result.raw_text,
        "request_url": result.request_url,
        "request_payload": mask_payload(result.request_payload),
    }

    st.session_state.history.insert(
        0,
        {
            "time": st.session_state.last_result["time"],
            "operation": label,
            "http": result.http_status,
            "status": status,
            "errorcode": error_code,
            "transactionid": transaction_id,
            "orderid": data.get("orderid", ""),
            "message": error_message,
        },
    )
    st.session_state.history = st.session_state.history[:50]


def save_exception(label: str, exc: Exception) -> None:
    st.session_state.diagnose_result = None
    st.session_state.last_result = {
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "operation": label,
        "ok": False,
        "banner_type": "error",
        "banner_title": f"{label} failed before receiving a gateway response.",
        "http_status": "—",
        "status": "—",
        "error_code": exc.__class__.__name__,
        "error_message": str(exc),
        "transaction_id": "",
        "session_id": "",
        "start_url": "",
        "redirect_url": "",
        "orderid": "",
        "parsed": {
            "exception": str(exc),
            "type": exc.__class__.__name__,
        },
        "raw": "",
        "request_url": "",
        "request_payload": {},
    }


def render_payment_method(prefix: str) -> dict:
    dropdown_col, logo_col = st.columns([3.25, 1], vertical_alignment="bottom")

    with dropdown_col:
        selected = st.selectbox(
            "Payment method",
            SUPPORTED_CARD_PM_OPTIONS,
            index=0,
            key=f"{prefix}_payment_method_select",
        )

    selected_pm = PM_BY_OPTION[selected]

    with logo_col:
        st.markdown(
            f"""
            <div class="pm-logo-shell">
                <img src="{asset_uri(selected_pm["asset"])}" alt="{selected_pm["label"]}">
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown(
        f'<div class="payment-method-meta">payment_method = <strong>{selected_pm["id"]}</strong> · supported</div>',
        unsafe_allow_html=True,
    )

    return selected_pm



def render_init_payment_method(prefix: str) -> dict | None:
    all_option = "All enabled payment methods"
    init_options = [all_option] + PM_OPTIONS

    dropdown_col, logo_col = st.columns([3.25, 1], vertical_alignment="bottom")

    with dropdown_col:
        selected = st.selectbox(
            "Payment method on HPP",
            init_options,
            index=0,
            key=f"{prefix}_payment_method_select",
            help="Leave as All enabled methods to let the Hosted Payment Page show all methods configured for the merchant.",
        )

    if selected == all_option:
        with logo_col:
            st.markdown(
                f"""
                <div class="pm-logo-shell">
                    <img src="{PAYABL_LOGO_URI}" alt="payabl.">
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.markdown(
            '<div class="payment-method-meta"><strong>payment_method omitted</strong> · HPP shows enabled methods</div>',
            unsafe_allow_html=True,
        )
        return None

    selected_pm = PM_BY_OPTION[selected]

    with logo_col:
        st.markdown(
            f"""
            <div class="pm-logo-shell">
                <img src="{asset_uri(selected_pm["asset"])}" alt="{selected_pm["label"]}">
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown(
        f'<div class="payment-method-meta">payment_method = <strong>{selected_pm["id"]}</strong> · preselected on HPP</div>',
        unsafe_allow_html=True,
    )

    return selected_pm


def init_form(prefix: str, selected_pm: dict | None) -> dict:
    st.markdown('<div class="section-label">Hosted Payment Page</div>', unsafe_allow_html=True)

    top1, top2, top3 = st.columns([1, .8, 1.65])
    with top1:
        amount = st.text_input("Amount", value="1.23", key=f"{prefix}_amount")
    with top2:
        currency = st.selectbox(
            "Currency",
            ["EUR", "USD", "GBP", "CHF"],
            key=f"{prefix}_currency",
        )
    with top3:
        order_id = order_id_input(prefix)

    c1, c2 = st.columns([1, 1])
    with c1:
        language = st.selectbox(
            "Language",
            ["en", "de"],
            key=f"{prefix}_language",
        )
    with c2:
        url_return = st.text_input(
            "Return URL",
            value="https://payabl.com/results",
            key=f"{prefix}_url_return",
            help="Required. Customer is redirected here after the payment flow.",
        )

    purpose = st.text_input(
        "Purpose",
        value="",
        key=f"{prefix}_purpose",
        placeholder="e.g. Order payment",
        help="Sent as the `purpose` parameter in the Init request.",
    )

    st.markdown('<div class="section-label">Customer</div>', unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    with c1:
        email = st.text_input(
            "Email",
            value="test@example.com",
            key=f"{prefix}_email",
        )
        firstname = st.text_input(
            "First name",
            value="Test",
            key=f"{prefix}_firstname",
        )
    with c2:
        customerip = st.text_input(
            "Customer IP",
            value="127.0.0.1",
            key=f"{prefix}_customerip",
        )
        lastname = st.text_input(
            "Last name",
            value="Customer",
            key=f"{prefix}_lastname",
        )

    with st.expander("Address / customer details", expanded=False):
        a1, a2, a3 = st.columns(3)
        with a1:
            country = st.text_input("Country", value="CYP", key=f"{prefix}_country")
            street = st.text_input("Street", value="Test Street", key=f"{prefix}_street")
            house = st.text_input("House", value="1", key=f"{prefix}_house")
        with a2:
            city = st.text_input("City", value="Limassol", key=f"{prefix}_city")
            zip_code = st.text_input("ZIP", value="3030", key=f"{prefix}_zip")
            state = st.text_input(
                "State / province",
                value="",
                key=f"{prefix}_state",
                help="Relevant for USA / Canada.",
            )
        with a3:
            salutation = st.text_input("Salutation", value="", key=f"{prefix}_salutation")
            title = st.text_input("Title", value="", key=f"{prefix}_title")
            gender = st.selectbox(
                "Gender",
                ["", "M", "F"],
                key=f"{prefix}_gender",
            )

        b1, b2, b3 = st.columns(3)
        with b1:
            birthday = st.text_input(
                "Birthday",
                value="",
                key=f"{prefix}_birthday",
                placeholder="ddmmyyyy",
            )
            postbox = st.text_input("Postbox", value="", key=f"{prefix}_postbox")
        with b2:
            company = st.text_input("Company", value="", key=f"{prefix}_company")
            customerid = st.text_input("Customer ID", value="", key=f"{prefix}_customerid")
        with b3:
            phone = st.text_input("Phone", value="", key=f"{prefix}_phone")
            mobile = st.text_input("Mobile", value="", key=f"{prefix}_mobile")
            fax = st.text_input("Fax", value="", key=f"{prefix}_fax")

    with st.expander("Callbacks / advanced", expanded=False):
        notification_url = st.text_input(
            "Notification URL",
            value="",
            key=f"{prefix}_notification_url",
        )
        shop_url = st.text_input(
            "Shop URL",
            value="",
            key=f"{prefix}_shop_url",
        )
        external_id = st.text_input(
            "External ID",
            value="",
            key=f"{prefix}_external_id",
        )
        recurring_id = st.text_input(
            "Recurring ID",
            value="",
            key=f"{prefix}_recurring_id",
            help="Only needed for recurring flows.",
        )

        x1, x2, x3 = st.columns(3)
        with x1:
            custom1 = st.text_input("Custom 1", value="", key=f"{prefix}_custom1")
        with x2:
            custom2 = st.text_input("Custom 2", value="", key=f"{prefix}_custom2")
        with x3:
            custom3 = st.text_input("Custom 3", value="", key=f"{prefix}_custom3")

    params = {
        "amount": amount.strip(),
        "currency": currency,
        "orderid": order_id.strip(),
        "language": language,
        "url_return": url_return.strip(),
        "purpose": clean_optional(purpose),
        "email": email.strip(),
        "firstname": firstname.strip(),
        "lastname": lastname.strip(),
        "customerip": customerip.strip(),
        "country": clean_optional(st.session_state.get(f"{prefix}_country", "CYP")),
        "street": clean_optional(st.session_state.get(f"{prefix}_street", "Test Street")),
        "house": clean_optional(st.session_state.get(f"{prefix}_house", "1")),
        "city": clean_optional(st.session_state.get(f"{prefix}_city", "Limassol")),
        "zip": clean_optional(st.session_state.get(f"{prefix}_zip", "3030")),
        "state": clean_optional(st.session_state.get(f"{prefix}_state", "")),
        "salutation": clean_optional(st.session_state.get(f"{prefix}_salutation", "")),
        "title": clean_optional(st.session_state.get(f"{prefix}_title", "")),
        "gender": clean_optional(st.session_state.get(f"{prefix}_gender", "")),
        "birthday": clean_optional(st.session_state.get(f"{prefix}_birthday", "")),
        "postbox": clean_optional(st.session_state.get(f"{prefix}_postbox", "")),
        "company": clean_optional(st.session_state.get(f"{prefix}_company", "")),
        "customerid": clean_optional(st.session_state.get(f"{prefix}_customerid", "")),
        "phone": clean_optional(st.session_state.get(f"{prefix}_phone", "")),
        "mobile": clean_optional(st.session_state.get(f"{prefix}_mobile", "")),
        "fax": clean_optional(st.session_state.get(f"{prefix}_fax", "")),
        "notification_url": clean_optional(st.session_state.get(f"{prefix}_notification_url", "")),
        "shop_url": clean_optional(st.session_state.get(f"{prefix}_shop_url", "")),
        "external_id": clean_optional(st.session_state.get(f"{prefix}_external_id", "")),
        "recurring_id": clean_optional(st.session_state.get(f"{prefix}_recurring_id", "")),
        "custom1": clean_optional(st.session_state.get(f"{prefix}_custom1", "")),
        "custom2": clean_optional(st.session_state.get(f"{prefix}_custom2", "")),
        "custom3": clean_optional(st.session_state.get(f"{prefix}_custom3", "")),
    }

    if selected_pm is not None:
        params["payment_method"] = str(selected_pm["id"])

    return params


def render_direct_payment_method(prefix: str) -> dict:
    dropdown_col, logo_col = st.columns([3.25, 1], vertical_alignment="bottom")

    with dropdown_col:
        selected = st.selectbox(
            "Payment method",
            DIRECT_PM_OPTIONS,
            index=0,
            key=f"{prefix}_direct_payment_method",
        )

    selected_pm = DIRECT_PM_BY_OPTION[selected]

    with logo_col:
        st.markdown(
            f"""
            <div class="pm-logo-shell">
                <img src="{asset_uri(selected_pm["asset"])}" alt="{selected_pm["label"]}">
            </div>
            """,
            unsafe_allow_html=True,
        )

    endpoint_label = (
        f"/pay/payment/{'applepay_init' if selected_pm['id'] == '119' else 'googlepay_init'}"
        if selected_pm["flow"] == "wallet"
        else "/pay/backoffice/payment_preauthorize"
    )

    st.markdown(
        f"""
        <div class="direct-method-note">
          <strong>{selected_pm["label"]}</strong> · payment_method={selected_pm["id"]}<br>
          {selected_pm["description"]}<br>
          Endpoint: <code>{endpoint_label}</code><br>
          Sandbox docs/profile: <strong>{selected_pm["sandbox_profile"]}</strong>
        </div>
        """,
        unsafe_allow_html=True,
    )

    return selected_pm


def direct_payment_form(prefix: str, selected_pm: dict) -> dict:
    st.markdown('<div class="section-label">Direct payment</div>', unsafe_allow_html=True)

    top1, top2, top3 = st.columns([1, .8, 1.65])
    with top1:
        default_amount = "10.00" if selected_pm["id"] == "116" else "9.99"
        amount = st.text_input(
            "Amount",
            value=default_amount,
            key=f"{prefix}_amount",
        )
    with top2:
        currency = st.selectbox(
            "Currency",
            ["EUR", "USD", "GBP", "SEK", "NOK", "DKK", "PLN"],
            key=f"{prefix}_currency",
        )
    with top3:
        order_id = order_id_input(prefix)

    st.markdown('<div class="section-label">Customer</div>', unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    with c1:
        email = st.text_input(
            "Email",
            value="test@example.com",
            key=f"{prefix}_email",
        )
        firstname = st.text_input(
            "First name",
            value="Test",
            key=f"{prefix}_firstname",
        )
        country_default = "SWE" if selected_pm["id"] == "116" else "CYP"
        country = st.text_input(
            "Country",
            value=country_default,
            key=f"{prefix}_country",
            help="ISO 3166-1 alpha-3 country code.",
        )

    with c2:
        customerip = st.text_input(
            "Customer IP",
            value="127.0.0.1",
            key=f"{prefix}_customerip",
        )
        lastname = st.text_input(
            "Last name",
            value="Customer",
            key=f"{prefix}_lastname",
        )

        if selected_pm["id"] == "116":
            language = st.selectbox(
                "Language",
                ["en", "sv", "de", "da", "fi", "no", "nl", "pl", "es", "fr", "et", "lt", "lv", "ru", "sk"],
                key=f"{prefix}_language",
            )
        else:
            language = st.selectbox(
                "Language",
                ["en", "de"],
                key=f"{prefix}_language",
            )

    accountname = None
    if selected_pm["id"] == "117":
        accountname = st.text_input(
            "PayPal account name",
            value="Test Customer",
            key=f"{prefix}_accountname",
            help="PayPal requires accountname.",
        )

    st.markdown('<div class="section-label">Redirects</div>', unsafe_allow_html=True)

    u1, u2 = st.columns(2)

    with u1:
        url_return = st.text_input(
            "Return URL",
            value="https://payabl.com/results",
            key=f"{prefix}_url_return",
        )
        notification_url = st.text_input(
            "Notification URL",
            value="",
            key=f"{prefix}_notification_url",
            help="Recommended so you can receive the final asynchronous status.",
        )

    with u2:
        if selected_pm["flow"] == "apm":
            url_success = st.text_input(
                "Success URL",
                value="https://payabl.com/results?status=success",
                key=f"{prefix}_url_success",
            )
            url_failed = st.text_input(
                "Failed URL",
                value="https://payabl.com/results?status=failed",
                key=f"{prefix}_url_failed",
            )
        else:
            url_success = None
            url_failed = None
            st.caption(
                "Apple Pay / Google Pay direct flow uses url_return. "
                "Final status should still be taken from notification_url or Diagnose."
            )

    with st.expander("Address / advanced", expanded=False):
        a1, a2, a3 = st.columns(3)
        with a1:
            zip_code = st.text_input(
                "ZIP",
                value="3035",
                key=f"{prefix}_zip",
            )
            street = st.text_input(
                "Street",
                value="Olympion",
                key=f"{prefix}_street",
            )
        with a2:
            house = st.text_input(
                "House",
                value="23",
                key=f"{prefix}_house",
            )
            city_default = "Stockholm" if selected_pm["id"] == "116" else "Limassol"
            city = st.text_input(
                "City",
                value=city_default,
                key=f"{prefix}_city",
            )
        with a3:
            shop_url = st.text_input(
                "Shop URL",
                value="",
                key=f"{prefix}_shop_url",
            )
            external_id = st.text_input(
                "External ID",
                value="",
                key=f"{prefix}_external_id",
            )

    params = {
        "amount": amount.strip(),
        "currency": currency,
        "orderid": order_id.strip(),
        "payment_method": str(selected_pm["id"]),
        "language": language,
        "email": email.strip(),
        "firstname": firstname.strip(),
        "lastname": lastname.strip(),
        "country": country.strip(),
        "customerip": customerip.strip(),
        "url_return": url_return.strip(),
        "notification_url": clean_optional(notification_url),
        "zip": clean_optional(st.session_state.get(f"{prefix}_zip", "3035")),
        "street": clean_optional(st.session_state.get(f"{prefix}_street", "Olympion")),
        "house": clean_optional(st.session_state.get(f"{prefix}_house", "23")),
        "city": clean_optional(st.session_state.get(f"{prefix}_city", "")),
        "shop_url": clean_optional(st.session_state.get(f"{prefix}_shop_url", "")),
        "external_id": clean_optional(st.session_state.get(f"{prefix}_external_id", "")),
    }

    if selected_pm["flow"] == "apm":
        params["url_success"] = clean_optional(url_success)
        params["url_failed"] = clean_optional(url_failed)

    if selected_pm["id"] == "117":
        params["accountname"] = clean_optional(accountname)

    return params


def validate_direct_payment(selected_pm: dict, params: dict) -> list[str]:
    required = [
        "amount",
        "currency",
        "payment_method",
        "email",
        "firstname",
        "lastname",
        "url_return",
    ]

    if selected_pm["flow"] == "apm":
        required.extend(["country", "url_success", "url_failed"])

    if selected_pm["id"] == "117":
        required.append("accountname")

    return [name for name in required if not params.get(name)]

def payment_common_form(prefix: str, selected_pm: dict) -> dict:
    st.markdown('<div class="section-label">Transaction</div>', unsafe_allow_html=True)

    top1, top2, top3 = st.columns([1, .8, 1.65])
    with top1:
        amount = st.text_input("Amount", value="1.23", key=f"{prefix}_amount")
    with top2:
        currency = st.selectbox(
            "Currency",
            ["EUR", "USD", "GBP", "CHF"],
            key=f"{prefix}_currency",
        )
    with top3:
        order_id = order_id_input(prefix)

    card_disabled = not selected_pm["supported"]

    # Actual widgets sit inside a keyed container, allowing the whole section
    # to receive the solid official Charcoal Black background.
    with st.container(key=f"{prefix}_card_section"):
        st.markdown(
            """
            <div class="card-section-heading">
                <span class="brand-dash"></span>
                Card details
            </div>
            <div class="card-section-copy">
                Test card credentials are sent server-to-server to the selected payabl. sandbox profile.
            </div>
            """,
            unsafe_allow_html=True,
        )

        c1, c2 = st.columns([1.45, 1])
        with c1:
            ccn = st.text_input(
                "Card number",
                value="5232050000010003",
                key=f"{prefix}_ccn",
                disabled=card_disabled,
            )
            cardholder_name = st.text_input(
                "Cardholder name",
                value="Test Customer",
                key=f"{prefix}_cardholder",
                disabled=card_disabled,
            )
        with c2:
            e1, e2, e3 = st.columns([1, 1, 1])
            with e1:
                exp_month = st.text_input(
                    "Month",
                    value="12",
                    key=f"{prefix}_exp_month",
                    disabled=card_disabled,
                )
            with e2:
                exp_year = st.text_input(
                    "Year",
                    value="2040",
                    key=f"{prefix}_exp_year",
                    disabled=card_disabled,
                )
            with e3:
                cvc_code = st.text_input(
                    "CVC",
                    value="123",
                    type="password",
                    key=f"{prefix}_cvc_code",
                    disabled=card_disabled,
                )

            language = st.selectbox(
                "Language",
                ["en", "de"],
                key=f"{prefix}_language",
            )

    with st.expander("Customer details", expanded=False):
        c1, c2, c3 = st.columns(3)
        with c1:
            email = st.text_input(
                "Email",
                value="test@example.com",
                key=f"{prefix}_email",
            )
            customerip = st.text_input(
                "Customer IP",
                value="127.0.0.1",
                key=f"{prefix}_customerip",
            )
        with c2:
            firstname = st.text_input(
                "First name",
                value="Test",
                key=f"{prefix}_firstname",
            )
            lastname = st.text_input(
                "Last name",
                value="Customer",
                key=f"{prefix}_lastname",
            )
        with c3:
            country = st.text_input(
                "Country",
                value="CYP",
                key=f"{prefix}_country",
            )
            city = st.text_input(
                "City",
                value="Limassol",
                key=f"{prefix}_city",
            )

        a1, a2, a3 = st.columns(3)
        with a1:
            street = st.text_input(
                "Street",
                value="Test Street",
                key=f"{prefix}_street",
            )
        with a2:
            house = st.text_input(
                "House",
                value="1",
                key=f"{prefix}_house",
            )
        with a3:
            zip_code = st.text_input(
                "ZIP",
                value="3030",
                key=f"{prefix}_zip",
            )

    with st.expander("Optional URLs / advanced", expanded=False):
        notification_url = st.text_input(
            "Notification URL",
            value="",
            key=f"{prefix}_notification_url",
        )
        url_return = st.text_input(
            "Return URL",
            value="",
            key=f"{prefix}_url_return",
        )
        shop_url = st.text_input(
            "Shop URL",
            value="",
            key=f"{prefix}_shop_url",
        )
        external_id = st.text_input(
            "External ID",
            value="",
            key=f"{prefix}_external_id",
        )

    params = {
        "amount": amount.strip(),
        "currency": currency,
        "orderid": order_id.strip(),
        "payment_method": str(selected_pm["id"]),
        "language": language,
        "email": st.session_state.get(f"{prefix}_email", "test@example.com").strip(),
        "customerip": st.session_state.get(f"{prefix}_customerip", "127.0.0.1").strip(),
        "firstname": st.session_state.get(f"{prefix}_firstname", "Test").strip(),
        "lastname": st.session_state.get(f"{prefix}_lastname", "Customer").strip(),
        "country": clean_optional(st.session_state.get(f"{prefix}_country", "CYP")),
        "city": clean_optional(st.session_state.get(f"{prefix}_city", "Limassol")),
        "street": clean_optional(st.session_state.get(f"{prefix}_street", "Test Street")),
        "house": clean_optional(st.session_state.get(f"{prefix}_house", "1")),
        "zip": clean_optional(st.session_state.get(f"{prefix}_zip", "3030")),
        "notification_url": clean_optional(st.session_state.get(f"{prefix}_notification_url", "")),
        "url_return": clean_optional(st.session_state.get(f"{prefix}_url_return", "")),
        "shop_url": clean_optional(st.session_state.get(f"{prefix}_shop_url", "")),
        "external_id": clean_optional(st.session_state.get(f"{prefix}_external_id", "")),
        "ccn": normalize_ccn(ccn),
        "exp_month": exp_month.strip(),
        "exp_year": exp_year.strip(),
        "cvc_code": cvc_code.strip(),
        "cardholder_name": cardholder_name.strip(),
    }

    return params



def _diagnose_process_and_transactions(parsed: dict) -> tuple[dict, list]:
    response = parsed.get("response", {}) if isinstance(parsed, dict) else {}
    if not isinstance(response, dict):
        return {}, []

    process = response.get("process", {})
    transactions = response.get("transaction", [])

    if isinstance(transactions, dict):
        transactions = [transactions]
    elif not isinstance(transactions, list):
        transactions = []

    return process if isinstance(process, dict) else {}, transactions


def save_diagnose_result(result) -> None:
    process, transactions = _diagnose_process_and_transactions(result.data)

    st.session_state.diagnose_result = {
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "http_status": result.http_status,
        "process": process,
        "transactions": transactions,
        "parsed": result.data,
        "raw": result.raw_text,
        "request_url": result.request_url,
        "request_payload": mask_payload(result.request_payload),
    }


def diagnose_summary_table(transactions: list) -> list[dict]:
    rows: list[dict] = []

    for tx in transactions:
        if not isinstance(tx, dict):
            continue

        tx_id = tx.get("transaction_id", "")
        status = tx.get("transaction_status", {})

        if isinstance(status, dict):
            for step_name, step in status.items():
                steps = step if isinstance(step, list) else [step]

                for step_item in steps:
                    if not isinstance(step_item, dict):
                        continue

                    rows.append({
                        "step": step_name,
                        "type": step_item.get("type", ""),
                        "transaction_id": tx_id,
                        "order_id": step_item.get("order_id", ""),
                        "amount": step_item.get("amount", ""),
                        "currency": step_item.get("currency", ""),
                        "error_code": step_item.get("error_code", ""),
                        "creation_date": step_item.get("creation_date", ""),
                    })
        else:
            rows.append({
                "step": "",
                "type": tx.get("type", ""),
                "transaction_id": tx_id,
                "order_id": tx.get("order_id", ""),
                "amount": tx.get("amount", ""),
                "currency": tx.get("currency", ""),
                "error_code": tx.get("error_code", ""),
                "creation_date": tx.get("transaction_date", tx.get("issue_date", "")),
            })

    return rows

def result_panel() -> None:
    with st.container(key="live_result"):
        title_col, clear_col = st.columns([1, 0.12], vertical_alignment="center")

        with title_col:
            st.markdown(
                """
                <div class="result-head">
                  <div class="result-title">Live response</div>
                </div>
                <div class="result-sub">The latest gateway result stays here while you work.</div>
                """,
                unsafe_allow_html=True,
            )

        with clear_col:
            if st.button(
                "✕",
                key="clear_live_result_icon",
                help="Clear live result",
                use_container_width=True,
            ):
                st.session_state.last_result = None
                st.session_state.diagnose_result = None
                st.rerun()

        result = st.session_state.get("last_result")

        if not result:
            st.markdown(
                """
                <div class="result-empty">
                  <strong>No request sent yet</strong>
                  Init, authorize, pre-authorize or capture from the left. The response will appear here immediately.
                </div>
                """,
                unsafe_allow_html=True,
            )
            return

        banner_class = result.get("banner_type", "warning")

        st.markdown(
            f"""
            <div class="result-banner {banner_class}">
              <div class="result-banner-title">{result["banner_title"]}</div>
              <div class="result-banner-meta">{result["time"]} · {result["operation"]}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Keep primary response data above the fold.
        m1, m2, m3 = st.columns([.85, .85, 1.3])
        m1.metric("HTTP", result["http_status"])
        display_status = result["status"] or result["error_code"] or "—"
        m2.metric("Status", display_status)
        m3.metric("Transaction ID", result["transaction_id"] or "—")

        if result.get("error_message"):
            st.error(result["error_message"])

        start_url = result.get("start_url", "")
        redirect_url = result.get("redirect_url", "")
        session_id = result.get("session_id", "")

        if start_url:
            st.link_button(
                "Open Hosted Payment Page ↗",
                start_url,
                use_container_width=True,
            )

        if redirect_url:
            operation = result.get("operation", "")
            button_label = {
                "Apple Pay": "Open Apple Pay ↗",
                "Google Pay": "Open Google Pay ↗",
                "Trustly": "Open Trustly ↗",
                "PayPal": "Open PayPal ↗",
            }.get(operation, "Open payment page ↗")

            st.link_button(
                button_label,
                redirect_url,
                use_container_width=True,
            )

        if session_id:
            st.caption(f"Session ID: `{session_id}`")

        transaction_id = result.get("transaction_id", "")

        if transaction_id:
            st.markdown(
                """
                <div class="diagnose-panel">
                  <div class="diagnose-title">
                    <span>Transaction diagnosis</span>
                  </div>
                  <div class="diagnose-copy">
                    Re-confirm this transaction's gateway status using payabl.'s Diagnose interface.
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            if st.button(
                "Diagnose transaction",
                key=f"diagnose_{transaction_id}",
                use_container_width=True,
            ):
                try:
                    save_diagnose_result(
                        client.diagnose_transaction(transaction_id)
                    )
                except Exception as exc:
                    st.session_state.diagnose_result = {
                        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "http_status": "—",
                        "process": {
                            "status": "error",
                            "error_message": str(exc),
                        },
                        "transactions": [],
                        "parsed": {
                            "exception": str(exc),
                            "type": exc.__class__.__name__,
                        },
                        "raw": "",
                        "request_url": "",
                        "request_payload": {},
                    }
                st.rerun()

            diagnosis = st.session_state.get("diagnose_result")

            if diagnosis:
                process = diagnosis.get("process", {})
                process_status = str(process.get("status", ""))
                process_error = str(process.get("error_message", "") or "")

                if process_status == "0":
                    st.success(
                        f"Diagnose completed · {len(diagnosis.get('transactions', []))} transaction record(s)"
                    )
                elif process_error:
                    st.warning(f"Diagnose: {process_error}")
                else:
                    st.info("Diagnose response received.")

                diagnose_rows = diagnose_summary_table(
                    diagnosis.get("transactions", [])
                )

                diag_tabs = st.tabs(["Diagnosis", "Diagnose XML", "Diagnose request"])

                with diag_tabs[0]:
                    if diagnose_rows:
                        st.dataframe(
                            diagnose_rows,
                            use_container_width=True,
                            hide_index=True,
                        )
                    else:
                        st.json(diagnosis.get("parsed", {}))

                with diag_tabs[1]:
                    st.code(
                        diagnosis.get("raw", "") or "(empty XML response)",
                        language="xml",
                    )

                with diag_tabs[2]:
                    if diagnosis.get("request_url"):
                        st.caption(diagnosis["request_url"])
                    st.json(diagnosis.get("request_payload", {}))

                st.caption(
                    "Diagnose is intended for specific re-checks/reporting cases, not for every transaction."
                )

        parsed = result.get("parsed", {})
        if parsed.get("url_3ds"):
            st.link_button(
                "Open 3DS challenge",
                str(parsed["url_3ds"]),
                use_container_width=True,
            )

        detail_tabs = st.tabs(["Parsed", "Request", "Raw", "History"])

        with detail_tabs[0]:
            st.json(parsed)

        with detail_tabs[1]:
            if result.get("request_url"):
                st.caption(result["request_url"])
            st.json(result.get("request_payload", {}))

        with detail_tabs[2]:
            st.code(
                result.get("raw", "") or "(empty response)",
                language="text",
            )

        with detail_tabs[3]:
            if not st.session_state.history:
                st.caption("No request history yet.")
            else:
                st.dataframe(
                    st.session_state.history,
                    use_container_width=True,
                    hide_index=True,
                )
                st.download_button(
                    "Download history JSON",
                    data=json.dumps(st.session_state.history, indent=2),
                    file_name="payabl_api_test_history.json",
                    mime="application/json",
                    use_container_width=True,
                )


# ---------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------

with st.sidebar:
    st.markdown(
        f"""
        <div class="sidebar-brand">
          <img src="{PAYABL_LOGO_URI}" alt="payabl.">
        </div>
        <div class="sidebar-label">API tester settings</div>
        """,
        unsafe_allow_html=True,
    )

    st.radio(
        "Environment",
        ["Sandbox", "Production"],
        key="environment",
        horizontal=True,
        on_change=change_environment,
    )

    environment = st.session_state.environment

    if environment == "Production":
        # Production URL supplied in the official production endpoint list.
        st.session_state.base_url = ENVIRONMENT_URLS["Production"]
        st.error("LIVE environment — requests can create real financial transactions.")
    else:
        st.session_state.base_url = ENVIRONMENT_URLS["Sandbox"]

        selected_profile = st.selectbox(
            "Quick profile",
            list(SANDBOX_PROFILES.keys()),
            key="sandbox_profile",
        )

        if st.button("Load sandbox profile", use_container_width=True):
            apply_profile(selected_profile)
            st.rerun()

        st.toggle(
            "Validate before sending",
            key="validate_requests",
            help=(
                "Checks amount, required fields and card format (Luhn, expiry, CVC) "
                "before a request is sent. Switch off in Sandbox to test the gateway's "
                "own error responses. Always on in Production."
            ),
        )

    st.text_input(
        "Base URL",
        key="base_url",
        disabled=True,
        help="Automatically selected from the Environment above.",
    )

    st.text_input(
        "Merchant ID",
        key="merchant_id",
        placeholder="Live merchant ID" if environment == "Production" else "Sandbox merchant ID",
    )

    st.text_input(
        "Secret",
        key="secret",
        type="password",
        placeholder="Live secret" if environment == "Production" else "Sandbox secret",
    )

    st.number_input(
        "HTTP timeout",
        min_value=5,
        max_value=120,
        step=5,
        key="timeout",
        help="Seconds before the HTTP request times out.",
    )

    st.divider()
    st.markdown('<div class="sidebar-label">Workflow</div>', unsafe_allow_html=True)

    if st.session_state.last_transaction_id:
        st.success(f"Last transaction: {st.session_state.last_transaction_id}")
    else:
        st.caption("No transaction captured yet.")

    if st.button("Clear TX", use_container_width=True):
        st.session_state.last_transaction_id = ""
        set_capture_transaction_id("")
        st.rerun()


# ---------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------

environment_display = st.session_state.get("environment", "Sandbox")
profile_display = (
    st.session_state.get("sandbox_profile", "Manual")
    if environment_display == "Sandbox"
    else "Production"
)
merchant_display = st.session_state.merchant_id or "No merchant"
environment_chip_class = "live" if environment_display == "Production" else "mint"
environment_chip_label = "LIVE" if environment_display == "Production" else "Sandbox"
environment_chip_icon = '<span class="live-dot"></span>' if environment_display == "Production" else '<span class="brand-dash"></span>'

st.markdown(
    f"""
    <div class="payabl-topbar">
      <div class="payabl-brand-wrap">
        <div class="payabl-logo-safe">
          <img src="{PAYABL_LOGO_URI}" alt="payabl.">
        </div>
        <div class="brand-divider"></div>
        <div class="app-name">
          <div class="app-name-title">API Tester</div>
          <div class="app-name-sub">Gateway API testing</div>
        </div>
      </div>

      <div class="top-statuses">
        <div class="top-chip {environment_chip_class}">{environment_chip_icon} {environment_chip_label}</div>
        <div class="top-chip">{merchant_display}</div>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

if not st.session_state.merchant_id or not st.session_state.secret:
    if st.session_state.environment == "Production":
        st.warning("Enter the LIVE Merchant ID and Secret in the sidebar.")
    else:
        st.warning("Enter Sandbox Merchant ID and Secret, or load a sandbox profile.")


# ---------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------

client = PayablClient(
    merchant_id=st.session_state.merchant_id,
    secret=st.session_state.secret,
    base_url=st.session_state.base_url,
    timeout=int(st.session_state.timeout),
)


# ---------------------------------------------------------------------
# Main workspace
# ---------------------------------------------------------------------

left_col, right_col = st.columns([1.22, .78], gap="large")

with left_col:
    st.markdown(
        """
        <div class="workspace-heading">
          <div class="workspace-title">Transaction workspace</div>
        </div>
        <div class="workspace-sub">
          Choose a flow and send the request. Advanced fields stay collapsed until needed.
        </div>
        """,
        unsafe_allow_html=True,
    )

    tab_init, tab_direct, tab_auth, tab_preauth, tab_capture = st.tabs(
        ["Init", "Direct Payments", "Authorize", "Pre-Authorize", "Capture"]
    )

    with tab_init:
        init_pm = render_init_payment_method("init")

        # Keep request-builder widgets outside st.form so Streamlit reruns on
        # every edit and the Request Preview reflects the current values live.
        init_params = init_form(
            "init",
            init_pm,
        )

        with st.expander("Request preview · live", expanded=False):
            st.caption("Updates as you edit. Merchant ID and signature are appended only when the request is sent.")
            st.json(mask_payload(init_params))

        init_confirmed = live_send_confirmed("init", live_summary(init_params))
        submit_init = st.button(
            "Create Hosted Payment Page",
            key="submit_init",
            type="primary",
            use_container_width=True,
            disabled=not init_confirmed,
        )

        if submit_init:
            if validation_enabled():
                errors = init_errors(init_params)
            else:
                errors = required_errors(init_params, ["amount", *INIT_REQUIRED])

            if errors:
                save_exception("Init", ValueError(format_errors(errors)))
            else:
                mark_request_sent("init")
                try:
                    save_result(
                        "Init",
                        client.init_transaction(init_params),
                    )
                except Exception as exc:
                    save_exception("Init", exc)
            st.rerun()

    with tab_direct:
        direct_pm = render_direct_payment_method("direct")

        direct_params = direct_payment_form(
            "direct",
            direct_pm,
        )

        with st.expander("Request preview · live", expanded=False):
            st.caption("Updates as you edit. Merchant ID and signature are appended only when the request is sent.")
            st.json(mask_payload(direct_params))

        direct_confirmed = live_send_confirmed("direct", live_summary(direct_params))
        submit_direct = st.button(
            f"Start {direct_pm['label']}",
            key="submit_direct_payment",
            type="primary",
            use_container_width=True,
            disabled=not direct_confirmed,
        )

        if submit_direct:
            errors = []
            if validation_enabled():
                errors += amount_errors(direct_params.get("amount"))
            missing = validate_direct_payment(direct_pm, direct_params)
            if missing:
                errors.append("Missing required field(s): " + ", ".join(missing) + ".")

            if errors:
                save_exception(direct_pm["label"], ValueError(format_errors(errors)))
            else:
                mark_request_sent("direct")
                try:
                    if direct_pm["id"] == "119":
                        result = client.apple_pay_init(direct_params)
                    elif direct_pm["id"] == "121":
                        result = client.google_pay_init(direct_params)
                    elif direct_pm["id"] in {"116", "117"}:
                        result = client.preauthorize(direct_params)
                    else:
                        raise ValueError("Unsupported direct payment method.")

                    save_result(direct_pm["label"], result)

                except Exception as exc:
                    save_exception(direct_pm["label"], exc)

            st.rerun()

    with tab_auth:
        auth_pm = render_payment_method("authorize")

        auth_params = payment_common_form(
            "authorize",
            auth_pm,
        )

        with st.expander("Request preview · live", expanded=False):
            st.caption("Updates as you edit. Merchant ID and signature are appended only when the request is sent.")
            st.json(mask_payload(auth_params))

        auth_confirmed = live_send_confirmed("authorize", live_summary(auth_params))
        submit_auth = st.button(
            "Send Authorization",
            key="submit_authorize",
            type="primary",
            use_container_width=True,
            disabled=not auth_confirmed,
        )

        if submit_auth:
            errors = card_payment_errors(auth_params) if validation_enabled() else []

            if errors:
                save_exception("Authorize", ValueError(format_errors(errors)))
            else:
                mark_request_sent("authorize")
                try:
                    save_result(
                        "Authorize",
                        client.authorize(auth_params),
                    )
                except Exception as exc:
                    save_exception("Authorize", exc)
            st.rerun()

    with tab_preauth:
        preauth_pm = render_payment_method("preauthorize")

        preauth_params = payment_common_form(
            "preauthorize",
            preauth_pm,
        )

        with st.expander("Request preview · live", expanded=False):
            st.caption("Updates as you edit. Merchant ID and signature are appended only when the request is sent.")
            st.json(mask_payload(preauth_params))

        preauth_confirmed = live_send_confirmed("preauthorize", live_summary(preauth_params))
        submit_preauth = st.button(
            "Send Pre-Authorization",
            key="submit_preauthorize",
            type="primary",
            use_container_width=True,
            disabled=not preauth_confirmed,
        )

        if submit_preauth:
            errors = card_payment_errors(preauth_params) if validation_enabled() else []

            if errors:
                save_exception("Pre-Authorize", ValueError(format_errors(errors)))
            else:
                mark_request_sent("preauthorize")
                try:
                    save_result(
                        "Pre-Authorize",
                        client.preauthorize(preauth_params),
                    )
                except Exception as exc:
                    save_exception("Pre-Authorize", exc)
            st.rerun()

    with tab_capture:
        st.markdown('<div class="section-label">Capture</div>', unsafe_allow_html=True)

        pending_capture_tx = st.session_state.pop("pending_capture_tx", None)
        if pending_capture_tx is not None:
            st.session_state.capture_transaction_id = pending_capture_tx

        transaction_id = st.text_input(
            "Transaction ID",
            key="capture_transaction_id",
            placeholder="e.g. 216771799",
            help="Filled automatically with the latest transaction ID.",
        )
        language = st.selectbox(
            "Language",
            ["en", "de"],
            key="capture_language",
        )

        capture_preview = {
            "transactionid": transaction_id.strip(),
            "language": language,
        }

        with st.expander("Request preview · live", expanded=False):
            st.caption("Updates as you edit. Merchant ID and signature are appended only when the request is sent.")
            st.json(capture_preview)

        st.caption("Capture completes a previous pre-authorization.")

        capture_confirmed = live_send_confirmed(
            "capture",
            f"capture transaction {transaction_id.strip() or '—'} · "
            f"merchant {st.session_state.merchant_id or '—'}",
        )
        submit_capture = st.button(
            "Capture Transaction",
            key="submit_capture",
            type="primary",
            use_container_width=True,
            disabled=not capture_confirmed,
        )

        if submit_capture:
            if not transaction_id.strip():
                save_exception(
                    "Capture",
                    ValueError("Transaction ID is required."),
                )
            else:
                mark_request_sent("capture")
                try:
                    save_result(
                        "Capture",
                        client.capture(
                            transaction_id=transaction_id,
                            language=language,
                        ),
                    )
                except Exception as exc:
                    save_exception("Capture", exc)
            st.rerun()


with right_col:
    result_panel()


st.caption(
    "Sandbox test utility. Do not process real cardholder data unless the environment "
    "and handling meet your PCI DSS obligations."
)
