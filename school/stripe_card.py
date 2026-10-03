"""Stripe Checkout integration for card payments (Visa, Mastercard, Amex, etc.).

Set STRIPE_SECRET_KEY in the environment to enable real card checkout.
Stripe Checkout supports all major card brands in a single flow, so Visa,
Mastercard, American Express, Discover, JCB, and UnionPay are all handled.
Without a key, payments fall back to a locally recorded demo payment.
"""

import json
import os
import urllib.parse
import urllib.request
import uuid


STRIPE_API_URL = "https://api.stripe.com/v1"


def _secret_key():
    return os.environ.get("STRIPE_SECRET_KEY", "").strip()


def is_configured():
    return bool(_secret_key())


def _request(path, payload=None, method="POST"):
    key = _secret_key()
    data = urllib.parse.urlencode(payload).encode() if payload is not None else None
    request = urllib.request.Request(
        f"{STRIPE_API_URL}{path}",
        data=data,
        method=method,
        headers={"Authorization": f"Bearer {key}"},
    )
    with urllib.request.urlopen(request, timeout=15) as response:
        return json.load(response)


def create_checkout_session(amount, currency, success_url, cancel_url, invoice_number):
    """Create a Stripe Checkout session and return (session_id, checkout_url).

    Stripe amounts are in the smallest currency unit (cents). Returns
    (None, None) when Stripe is not configured.
    """
    if not is_configured():
        return None, None
    unit_amount = int((amount * 100).quantize(0))
    payload = {
        "mode": "payment",
        "payment_method_types[]": "card",
        "line_items[][price_data][currency]": currency.lower(),
        "line_items[][price_data][unit_amount]": unit_amount,
        "line_items[][price_data][product_data][name]": f"Invoice {invoice_number}",
        "line_items[][quantity]": 1,
        "success_url": success_url,
        "cancel_url": cancel_url,
        "client_reference_id": invoice_number,
    }
    session = _request("/checkout/sessions", payload)
    return session["id"], session["url"]


def retrieve_session(session_id):
    """Return (paid, reference) for a completed checkout session."""
    if not is_configured():
        return False, ""
    try:
        session = _request(f"/checkout/sessions/{session_id}", method="GET")
    except Exception:
        return False, ""
    paid = session.get("payment_status") == "paid"
    reference = session.get("payment_intent") or session_id
    return paid, reference


def demo_reference():
    return f"CARD-DEMO-{uuid.uuid4().hex[:10].upper()}"
