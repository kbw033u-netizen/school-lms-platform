"""Google Calendar integration for scheduled Google Meet lessons."""

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid

import google.auth.exceptions
from google.auth.transport.requests import Request
from google.oauth2 import service_account


CALENDAR_API_URL = "https://www.googleapis.com/calendar/v3"
CALENDAR_SCOPE = "https://www.googleapis.com/auth/calendar.events"
CONFERENCE_WAIT_ATTEMPTS = 5
CONFERENCE_WAIT_SECONDS = 1


class GoogleMeetError(Exception):
    """Raised when a Google Meet conference cannot be created."""


def _configuration():
    service_account_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", "").strip()
    delegate_email = os.environ.get("GOOGLE_CALENDAR_DELEGATE_EMAIL", "").strip()
    calendar_id = os.environ.get("GOOGLE_CALENDAR_ID", "primary").strip() or "primary"
    if not service_account_json or not delegate_email:
        raise GoogleMeetError(
            "Google Meet scheduling is not configured. Set "
            "GOOGLE_SERVICE_ACCOUNT_JSON and GOOGLE_CALENDAR_DELEGATE_EMAIL. "
            "GOOGLE_CALENDAR_ID is optional and defaults to primary."
        )
    try:
        service_account_info = json.loads(service_account_json)
        credentials = service_account.Credentials.from_service_account_info(
            service_account_info,
            scopes=[CALENDAR_SCOPE],
        ).with_subject(delegate_email)
        credentials.refresh(Request())
    except (ValueError, KeyError, TypeError, google.auth.exceptions.GoogleAuthError) as error:
        raise GoogleMeetError(
            "Google Meet authentication failed. Check the service account key and "
            "Workspace domain-wide delegation settings."
        ) from error
    return credentials.token, calendar_id


def _calendar_request(token, calendar_id, event_id=None, payload=None, conference_data=False):
    encoded_calendar = urllib.parse.quote(calendar_id, safe="")
    path = f"/calendars/{encoded_calendar}/events"
    if event_id:
        path += f"/{urllib.parse.quote(event_id, safe='')}"
    query = urllib.parse.urlencode(
        {"conferenceDataVersion": 1, "sendUpdates": "all"} if conference_data else {}
    )
    query = f"?{query}" if query else ""
    request = urllib.request.Request(
        f"{CALENDAR_API_URL}{path}{query}",
        data=json.dumps(payload).encode("utf-8") if payload is not None else None,
        method="POST" if payload is not None else "GET",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return json.load(response)
    except urllib.error.HTTPError as error:
        try:
            error_body = json.load(error)
        except (json.JSONDecodeError, UnicodeDecodeError):
            error_body = {}
        api_error = error_body.get("error", {}) if isinstance(error_body, dict) else {}
        detail = api_error.get("message") if isinstance(api_error, dict) else None
        if detail:
            raise GoogleMeetError(f"Google Calendar rejected the Meet request: {detail}") from error
        raise GoogleMeetError(
            f"Google Calendar rejected the Meet request (HTTP {error.code})."
        ) from error
    except urllib.error.URLError as error:
        raise GoogleMeetError("Could not connect to the Google Calendar API.") from error
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise GoogleMeetError("Google Calendar returned an unreadable response.") from error


def is_configured():
    return all(
        os.environ.get(name, "").strip()
        for name in ("GOOGLE_SERVICE_ACCOUNT_JSON", "GOOGLE_CALENDAR_DELEGATE_EMAIL")
    )


def create_meeting(topic, start_time, end_time, time_zone, teacher_email):
    """Create a Calendar event with a Google Meet conference and return its details."""
    token, calendar_id = _configuration()
    payload = {
        "summary": topic,
        "start": {"dateTime": start_time, "timeZone": time_zone},
        "end": {"dateTime": end_time, "timeZone": time_zone},
        "attendees": [{"email": teacher_email}],
        "conferenceData": {
            "createRequest": {
                "requestId": uuid.uuid4().hex,
                "conferenceSolutionKey": {"type": "hangoutsMeet"},
            }
        },
    }
    event = _calendar_request(token, calendar_id, payload=payload, conference_data=True)
    event_id = event.get("id") if isinstance(event, dict) else None
    if not event_id:
        raise GoogleMeetError("Google Calendar did not return the scheduled event ID.")

    meeting_url = event.get("hangoutLink")
    for attempt in range(CONFERENCE_WAIT_ATTEMPTS):
        conference_data = event.get("conferenceData")
        create_request = conference_data.get("createRequest") if isinstance(conference_data, dict) else {}
        status = create_request.get("status") if isinstance(create_request, dict) else {}
        conference_status = status.get("statusCode") if isinstance(status, dict) else None
        if meeting_url or conference_status == "failure":
            break
        if attempt + 1 < CONFERENCE_WAIT_ATTEMPTS:
            time.sleep(CONFERENCE_WAIT_SECONDS)
            event = _calendar_request(token, calendar_id, event_id=event_id)
            if not isinstance(event, dict):
                raise GoogleMeetError("Google Calendar returned an unexpected event response.")
            meeting_url = event.get("hangoutLink")

    if not meeting_url:
        raise GoogleMeetError(
            "Google Calendar created the event but did not provide a Google Meet link. "
            f"Check event {event_id} in the delegated calendar before retrying."
        )
    return {"join_url": meeting_url, "event_id": event_id}
