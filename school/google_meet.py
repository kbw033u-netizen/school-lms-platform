"""Google Meet REST API integration for live lesson spaces."""

import json
import os
import urllib.error
import urllib.request

import google.auth.exceptions
from google.auth.transport.requests import Request
from google.oauth2 import service_account


MEET_API_URL = "https://meet.googleapis.com/v2/spaces"
MEET_SCOPE = "https://www.googleapis.com/auth/meetings.space.created"


class GoogleMeetError(Exception):
    """Raised when a Google Meet space cannot be created."""


def _configuration():
    service_account_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", "").strip()
    delegate_email = os.environ.get("GOOGLE_MEET_DELEGATE_EMAIL", "").strip()
    if not service_account_json or not delegate_email:
        raise GoogleMeetError(
            "Google Meet API is not configured. Set GOOGLE_SERVICE_ACCOUNT_JSON "
            "and GOOGLE_MEET_DELEGATE_EMAIL."
        )
    try:
        service_account_info = json.loads(service_account_json)
        credentials = service_account.Credentials.from_service_account_info(
            service_account_info,
            scopes=[MEET_SCOPE],
        ).with_subject(delegate_email)
        credentials.refresh(Request())
    except (ValueError, KeyError, TypeError, google.auth.exceptions.GoogleAuthError) as error:
        raise GoogleMeetError(
            "Google Meet API authentication failed. Check the service account key "
            "and Workspace domain-wide delegation settings for the Meet API scope."
        ) from error
    return credentials.token


def is_configured():
    return all(
        os.environ.get(name, "").strip()
        for name in ("GOOGLE_SERVICE_ACCOUNT_JSON", "GOOGLE_MEET_DELEGATE_EMAIL")
    )


def create_meeting():
    """Create a Google Meet API space and return its joining URI and resource name."""
    token = _configuration()
    request = urllib.request.Request(
        MEET_API_URL,
        data=json.dumps({}).encode("utf-8"),
        method="POST",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            meeting_space = json.load(response)
    except urllib.error.HTTPError as error:
        try:
            error_body = json.load(error)
        except (json.JSONDecodeError, UnicodeDecodeError):
            error_body = {}
        api_error = error_body.get("error", {}) if isinstance(error_body, dict) else {}
        detail = api_error.get("message") if isinstance(api_error, dict) else None
        if detail:
            raise GoogleMeetError(f"Google Meet API rejected the request: {detail}") from error
        raise GoogleMeetError(
            f"Google Meet API rejected the request (HTTP {error.code})."
        ) from error
    except urllib.error.URLError as error:
        raise GoogleMeetError("Could not connect to the Google Meet API.") from error
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise GoogleMeetError("Google Meet API returned an unreadable response.") from error

    if not isinstance(meeting_space, dict):
        raise GoogleMeetError("Google Meet API returned an unexpected response.")
    meeting_uri = meeting_space.get("meetingUri")
    space_name = meeting_space.get("name")
    if not meeting_uri or not space_name:
        raise GoogleMeetError("Google Meet API did not return a meeting link and space name.")
    return {"join_url": meeting_uri, "space_name": space_name}
