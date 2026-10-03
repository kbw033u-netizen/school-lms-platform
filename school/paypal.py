"""PayPal Orders API integration (v2).

Set PAYPAL_CLIENT_ID and PAYPAL_CLIENT_SECRET in the environment to enable
real checkout. PAYPAL_ENV=sandbox (default) uses the sandbox API; set it to
"live" for production. Without credentials, payments fall back to a locally
recorded demo payment so the portal still works.
"""

import base64
import json
import os
import urllib.parse
import urllib.request


API_HOSTS = {
    "sandbox": "https://api-m.sandbox.paypal.com",
    "live": "https://api-m.paypal.com",
}


def _api_host():
    env = os.environ.get("PAYPAL_ENV", "sandbox").strip().lower()
    return API_HOSTS.get(env, API_HOSTS["sandbox"])


def _credentials():
    client_id = os.environ.get("PAYPAL_CLIENT_ID", "").strip()
    client_secret = os.environ.get("PAYPAL_CLIENT_SECRET", "").strip()
    if client_id and client_secret:
        return client_id, client_secret
    return None


def is_configured():
    return _credentials() is not None


def _access_token(client_id, client_secret):
    basic = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    request = urllib.request.Request(
        f"{_api_host()}/v1/oauth2/token",
        data=urllib.parse.urlencode({"grant_type": "client_credentials"}).encode(),
        method="POST",
        headers={"Authorization": f"Basic {basic}", "Content-Type": "application/x-www-form-urlencoded"},
    )
    with urllib.request.urlopen(request, timeout=15) as response:
        return json.load(response)["access_token"]


def create_order(amount, currency, return_url, cancel_url, invoice_number):
    """Create a PayPal order and return (order_id, approve_url).

    Returns (None, None) when PayPal is not configured, signalling the
    caller to record a local demo payment instead.
    """
    credentials = _credentials()
    if not credentials:
        return None, None
    token = _access_token(*credentials)
    payload = {
        "intent": "CAPTURE",
        "purchase_units": [
            {
                "reference_id": invoice_number,
                "amount": {"currency_code": currency, "value": f"{amount:.2f}"},
            }
        ],
        "application_context": {
            "return_url": return_url,
            "cancel_url": cancel_url,
            "user_action": "PAY_NOW",
        },
    }
    request = urllib.request.Request(
        f"{_api_host()}/v2/checkout/orders",
        data=json.dumps(payload).encode(),
        method="POST",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=15) as response:
        order = json.load(response)
    approve_url = next(
        (link["href"] for link in order.get("links", []) if link.get("rel") == "approve"),
        None,
    )
    return order["id"], approve_url


def capture_order(order_id):
    """Capture an approved order. Returns (success, payer_reference)."""
    credentials = _credentials()
    if not credentials:
        return False, ""
    token = _access_token(*credentials)
    request = urllib.request.Request(
        f"{_api_host()}/v2/checkout/orders/{order_id}/capture",
        data=b"{}",
        method="POST",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            result = json.load(response)
    except Exception:
        return False, ""
    if result.get("status") != "COMPLETED":
        return False, ""
    capture = result["purchase_units"][0]["payments"]["captures"][0]
    return True, capture.get("id", order_id)
