"""M-Pesa (Safaricom Daraja) STK push integration.

Set MPESA_CONSUMER_KEY, MPESA_CONSUMER_SECRET, MPESA_SHORTCODE, and
MPESA_PASSKEY in the environment to enable real STK pushes.
MPESA_ENV=sandbox (default) uses the Daraja sandbox; set it to
"production" for live payments. MPESA_CALLBACK_URL can override the
callback sent to Safaricom. Without credentials, payments fall back to a
locally recorded demo payment so the portal still works.
"""

import base64
import json
import os
import urllib.request
from datetime import datetime


API_HOSTS = {
    "sandbox": "https://sandbox.safaricom.co.ke",
    "production": "https://api.safaricom.co.ke",
}


def _api_host():
    env = os.environ.get("MPESA_ENV", "sandbox").strip().lower()
    return API_HOSTS.get(env, API_HOSTS["sandbox"])


def _credentials():
    consumer_key = os.environ.get("MPESA_CONSUMER_KEY", "").strip()
    consumer_secret = os.environ.get("MPESA_CONSUMER_SECRET", "").strip()
    shortcode = os.environ.get("MPESA_SHORTCODE", "").strip()
    passkey = os.environ.get("MPESA_PASSKEY", "").strip()
    if consumer_key and consumer_secret and shortcode and passkey:
        return consumer_key, consumer_secret, shortcode, passkey
    return None


def is_configured():
    return _credentials() is not None


def normalize_phone(phone):
    """Normalize a Kenyan phone number to the 2547XXXXXXXX format."""
    digits = "".join(ch for ch in phone if ch.isdigit())
    if digits.startswith("0"):
        digits = "254" + digits[1:]
    elif digits.startswith("+"):
        digits = digits[1:]
    if digits.startswith("254") and len(digits) == 12:
        return digits
    return ""


def _access_token(consumer_key, consumer_secret):
    basic = base64.b64encode(f"{consumer_key}:{consumer_secret}".encode()).decode()
    request = urllib.request.Request(
        f"{_api_host()}/oauth/v1/generate?grant_type=client_credentials",
        headers={"Authorization": f"Basic {basic}"},
    )
    with urllib.request.urlopen(request, timeout=15) as response:
        return json.load(response)["access_token"]


def _password(shortcode, passkey):
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    raw = f"{shortcode}{passkey}{timestamp}".encode()
    return base64.b64encode(raw).decode(), timestamp


def stk_push(amount, phone, account_reference, callback_url):
    """Initiate an STK push. Returns (checkout_request_id, error).

    Returns (None, None) when Daraja credentials are not configured,
    signalling the caller to record a local demo payment instead.
    """
    credentials = _credentials()
    if not credentials:
        return None, None
    consumer_key, consumer_secret, shortcode, passkey = credentials
    token = _access_token(consumer_key, consumer_secret)
    password, timestamp = _password(shortcode, passkey)
    payload = {
        "BusinessShortCode": shortcode,
        "Password": password,
        "Timestamp": timestamp,
        "TransactionType": "CustomerPayBillOnline",
        "Amount": int(amount),
        "PartyA": phone,
        "PartyB": shortcode,
        "PhoneNumber": phone,
        "CallBackURL": callback_url,
        "AccountReference": account_reference,
        "TransactionDesc": f"School fees {account_reference}",
    }
    request = urllib.request.Request(
        f"{_api_host()}/mpesa/stkpush/v1/processrequest",
        data=json.dumps(payload).encode(),
        method="POST",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            result = json.load(response)
    except Exception as exc:
        return None, str(exc)
    if result.get("ResponseCode") != "0":
        return None, result.get("ResponseDescription", "STK push rejected")
    return result.get("CheckoutRequestID"), None


def stk_query(checkout_request_id):
    """Query an STK push result. Returns True when the payment completed."""
    credentials = _credentials()
    if not credentials:
        return False
    consumer_key, consumer_secret, shortcode, passkey = credentials
    token = _access_token(consumer_key, consumer_secret)
    password, timestamp = _password(shortcode, passkey)
    payload = {
        "BusinessShortCode": shortcode,
        "Password": password,
        "Timestamp": timestamp,
        "CheckoutRequestID": checkout_request_id,
    }
    request = urllib.request.Request(
        f"{_api_host()}/mpesa/stkpushquery/v1/query",
        data=json.dumps(payload).encode(),
        method="POST",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            result = json.load(response)
    except Exception:
        return False
    return str(result.get("ResultCode")) == "0"
