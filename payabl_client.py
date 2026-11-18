from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any
from urllib.parse import parse_qs
import xml.etree.ElementTree as ET

import requests


@dataclass
class PayablResponse:
    http_status: int
    raw_text: str
    data: dict[str, Any]
    request_url: str
    request_payload: dict[str, Any]


def _stringify(value: Any) -> str:
    if value is None:
        return ""
    return str(value)


def generate_signature(params: dict[str, Any], secret: str) -> str:
    clean = {
        str(key): _stringify(value)
        for key, value in params.items()
        if key != "signature" and value is not None
    }
    signature_source = "".join(clean[key] for key in sorted(clean)) + secret
    return hashlib.sha1(signature_source.encode("utf-8")).hexdigest().lower()


def mask_payload(payload: dict[str, Any]) -> dict[str, Any]:
    masked = dict(payload)

    if masked.get("ccn"):
        ccn = str(masked["ccn"])
        masked["ccn"] = f"{'*' * max(len(ccn) - 4, 0)}{ccn[-4:]}"

    if masked.get("cvc_code"):
        masked["cvc_code"] = "***"

    if masked.get("signature"):
        sig = str(masked["signature"])
        masked["signature"] = f"{sig[:6]}...{sig[-6:]}" if len(sig) > 12 else "***"

    return masked


def parse_gateway_response(text: str) -> dict[str, Any]:
    parsed = parse_qs(text, keep_blank_values=True)
    if not parsed:
        return {"raw": text}

    result: dict[str, Any] = {}
    for key, values in parsed.items():
        result[key] = values[0] if len(values) == 1 else values
    return result


def _xml_element_to_obj(element: ET.Element) -> Any:
    children = list(element)

    if not children:
        text = (element.text or "").strip()
        return text

    result: dict[str, Any] = {}

    for child in children:
        value = _xml_element_to_obj(child)

        if child.tag in result:
            existing = result[child.tag]
            if not isinstance(existing, list):
                result[child.tag] = [existing]
            result[child.tag].append(value)
        else:
            result[child.tag] = value

    return result


def parse_xml_response(text: str) -> dict[str, Any]:
    try:
        root = ET.fromstring(text)
    except ET.ParseError:
        return {"raw": text}

    return {root.tag: _xml_element_to_obj(root)}


class PayablClient:
    def __init__(
        self,
        merchant_id: str,
        secret: str,
        base_url: str = "https://sandbox.payabl.com",
        timeout: int = 30,
    ) -> None:
        self.merchant_id = merchant_id.strip()
        self.secret = secret
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def _post(
        self,
        endpoint: str,
        params: dict[str, Any],
        *,
        response_format: str = "form",
        path_prefix: str = "/pay/backoffice",
    ) -> PayablResponse:
        payload = {
            key: value
            for key, value in params.items()
            if value is not None and str(value) != ""
        }

        payload["merchantid"] = self.merchant_id
        payload["signature"] = generate_signature(payload, self.secret)

        url = f"{self.base_url}{path_prefix}/{endpoint}"

        response = requests.post(
            url,
            data=payload,
            timeout=self.timeout,
            headers={
                "User-Agent": "payabl-streamlit-api-tester/1.0",
                "Accept": "application/xml, text/xml, application/x-www-form-urlencoded, */*",
            },
        )

        if response_format == "xml":
            parsed = parse_xml_response(response.text)
        else:
            parsed = parse_gateway_response(response.text)

        return PayablResponse(
            http_status=response.status_code,
            raw_text=response.text,
            data=parsed,
            request_url=url,
            request_payload=payload,
        )

    def init_transaction(self, params: dict[str, Any]) -> PayablResponse:
        return self._post(
            "init",
            params,
            path_prefix="/pay/payment",
        )

    def apple_pay_init(self, params: dict[str, Any]) -> PayablResponse:
        return self._post(
            "applepay_init",
            params,
            path_prefix="/pay/payment",
        )

    def google_pay_init(self, params: dict[str, Any]) -> PayablResponse:
        return self._post(
            "googlepay_init",
            params,
            path_prefix="/pay/payment",
        )

    def authorize(self, params: dict[str, Any]) -> PayablResponse:
        return self._post("payment_authorize", params)

    def preauthorize(self, params: dict[str, Any]) -> PayablResponse:
        return self._post("payment_preauthorize", params)

    def capture(self, transaction_id: str, language: str = "en") -> PayablResponse:
        params: dict[str, Any] = {"transactionid": str(transaction_id).strip()}
        if language:
            params["language"] = language
        return self._post("payment_capture", params)

    def diagnose_transaction(self, transaction_id: str) -> PayablResponse:
        params: dict[str, Any] = {
            "type": "tx",
            "transactionid": str(transaction_id).strip(),
        }
        return self._post(
            "tx_diagnose",
            params,
            response_format="xml",
        )
