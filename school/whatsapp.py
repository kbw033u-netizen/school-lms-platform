"""WhatsApp Cloud API messaging for API-managed groups."""

import json
import os
import re
import urllib.error
import urllib.request
from urllib.parse import quote


class WhatsAppAPIError(Exception):
    """Raised when WhatsApp group messaging is unavailable or rejected."""


def _configuration():
    values = {
        "access_token": os.environ.get("WHATSAPP_ACCESS_TOKEN", "").strip(),
        "phone_number_id": os.environ.get("WHATSAPP_PHONE_NUMBER_ID", "").strip(),
        "group_id": os.environ.get("WHATSAPP_GROUP_ID", "").strip(),
        "api_version": os.environ.get("WHATSAPP_API_VERSION", "").strip(),
    }
    missing = [key for key, value in values.items() if not value]
    if missing:
        env_names = {
            "access_token": "WHATSAPP_ACCESS_TOKEN",
            "phone_number_id": "WHATSAPP_PHONE_NUMBER_ID",
            "group_id": "WHATSAPP_GROUP_ID",
            "api_version": "WHATSAPP_API_VERSION",
        }
        raise WhatsAppAPIError(
            "Direct WhatsApp group messaging is not configured. Set "
            + ", ".join(env_names[key] for key in missing)
            + "."
        )
    if not re.fullmatch(r"v\d+\.\d+", values["api_version"]):
        raise WhatsAppAPIError("WHATSAPP_API_VERSION must use the Meta version format, such as vXX.0.")
    return values


def is_configured():
    required = (
        "WHATSAPP_ACCESS_TOKEN",
        "WHATSAPP_PHONE_NUMBER_ID",
        "WHATSAPP_GROUP_ID",
        "WHATSAPP_API_VERSION",
    )
    return all(os.environ.get(name, "").strip() for name in required)


def send_group_message(message):
    """Send text to the configured API-managed WhatsApp group."""
    configuration = _configuration()
    endpoint = (
        "https://graph.facebook.com/"
        f"{configuration['api_version']}/"
        f"{quote(configuration['phone_number_id'], safe='')}/messages"
    )
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "group",
        "to": configuration["group_id"],
        "type": "text",
        "text": {"body": message, "preview_url": True},
    }
    request = urllib.request.Request(
        endpoint,
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={
            "Authorization": f"Bearer {configuration['access_token']}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            result = json.load(response)
    except urllib.error.HTTPError as error:
        try:
            error_body = json.load(error)
        except (json.JSONDecodeError, UnicodeDecodeError):
            error_body = {}
        api_error = error_body.get("error", {})
        detail = api_error.get("message")
        if detail:
            raise WhatsAppAPIError(f"WhatsApp rejected the group message: {detail}") from error
        raise WhatsAppAPIError(
            f"WhatsApp rejected the group message (HTTP {error.code})."
        ) from error
    except urllib.error.URLError as error:
        raise WhatsAppAPIError("Could not connect to the WhatsApp Cloud API.") from error
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise WhatsAppAPIError("WhatsApp returned an unreadable response.") from error

    if not isinstance(result, dict):
        raise WhatsAppAPIError("WhatsApp returned an unexpected response.")
    messages = result.get("messages")
    if (
        not isinstance(messages, list)
        or not messages
        or not isinstance(messages[0], dict)
        or not messages[0].get("id")
    ):
        raise WhatsAppAPIError("WhatsApp did not confirm delivery of the group message.")
    return messages[0]["id"]
