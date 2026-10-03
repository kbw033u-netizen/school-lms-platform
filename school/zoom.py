"""Zoom Server-to-Server integration for live classes.

Set ZOOM_ACCOUNT_ID, ZOOM_CLIENT_ID, and ZOOM_CLIENT_SECRET in the
environment to create real Zoom meetings. Without credentials the module
falls back to demo join URLs so the portal still works locally.
"""

import base64
import json
import os
import urllib.parse
import urllib.request
import uuid


ZOOM_OAUTH_URL = "https://zoom.us/oauth/token"
ZOOM_API_URL = "https://api.zoom.us/v2"


def _credentials():
    account_id = os.environ.get("ZOOM_ACCOUNT_ID", "").strip()
    client_id = os.environ.get("ZOOM_CLIENT_ID", "").strip()
    client_secret = os.environ.get("ZOOM_CLIENT_SECRET", "").strip()
    if account_id and client_id and client_secret:
        return account_id, client_id, client_secret
    return None


def _access_token(account_id, client_id, client_secret):
    basic = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    query = urllib.parse.urlencode(
        {"grant_type": "account_credentials", "account_id": account_id}
    )
    request = urllib.request.Request(
        f"{ZOOM_OAUTH_URL}?{query}",
        method="POST",
        headers={"Authorization": f"Basic {basic}"},
    )
    with urllib.request.urlopen(request, timeout=15) as response:
        return json.load(response)["access_token"]


def create_meeting(topic, start_time, duration_minutes=60):
    """Create a Zoom meeting and return its details.

    Returns a dict with join_url, start_url, meeting_id, and passcode.
    Falls back to a demo meeting when Zoom credentials are not configured.
    """
    credentials = _credentials()
    if not credentials:
        demo_id = uuid.uuid4().hex[:10]
        passcode = uuid.uuid4().hex[:8]
        join_url = f"https://zoom.us/j/{demo_id}?pwd={passcode}"
        return {
            "join_url": join_url,
            "start_url": join_url,
            "meeting_id": demo_id,
            "passcode": passcode,
        }

    token = _access_token(*credentials)
    payload = {
        "topic": topic,
        "type": 2,
        "start_time": start_time,
        "duration": duration_minutes,
        "settings": {"join_before_host": False, "waiting_room": True},
    }
    request = urllib.request.Request(
        f"{ZOOM_API_URL}/users/me/meetings",
        data=json.dumps(payload).encode(),
        method="POST",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=15) as response:
        meeting = json.load(response)
    return {
        "join_url": meeting["join_url"],
        "start_url": meeting["start_url"],
        "meeting_id": str(meeting["id"]),
        "passcode": meeting.get("password", ""),
    }
