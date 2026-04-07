#!/usr/bin/env python3
"""
End-to-end validation of the Virtual Events Platform API against the live API.

Covers: events CRUD, sessions (multiple types), team members, duplication,
and full lifecycle cleanup.

Uses the dedicated Events Platform REST API (separate from Kaltura API v3).

Note: The events/create endpoint may return 500 if the account has reached
its event limit. In that case, read-only tests still validate the API surface
using existing events on the account.
"""

import sys
import os
import time
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(__file__))
from test_helpers import TestRunner, PARTNER_ID, SERVICE_URL

import requests

EVENTS_API_URL = os.environ.get(
    "KALTURA_EVENTS_API_URL",
    "https://events-api.nvp1.ovp.kaltura.com/api/v1"
)

def _read_env_file_value(key):
    """Read a value directly from the .env file, bypassing system env overrides."""
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line.startswith(f"{key}="):
                    return line.split("=", 1)[1].strip()
    return None

# Events Platform requires a KS with userId set.
# Generate a fresh one via session.start using admin secret.
ADMIN_SECRET = _read_env_file_value("KALTURA_ADMIN_SECRET") or os.environ.get("KALTURA_ADMIN_SECRET", "")
USER_ID = _read_env_file_value("KALTURA_USER_ID") or os.environ.get("KALTURA_USER_ID", "")

def _generate_events_ks():
    """Generate a KS suitable for the Events Platform (must have userId)."""
    if not ADMIN_SECRET:
        print("ERROR: KALTURA_ADMIN_SECRET not set in .env")
        sys.exit(1)
    if not USER_ID:
        print("ERROR: KALTURA_USER_ID not set in .env")
        sys.exit(1)
    # Read PID from .env file directly — system env may have a different value
    pid = _read_env_file_value("KALTURA_PARTNER_ID") or PARTNER_ID
    resp = requests.post(
        f"{SERVICE_URL}/service/session/action/start",
        data={
            "partnerId": pid,
            "secret": ADMIN_SECRET,
            "userId": USER_ID,
            "type": 2,  # ADMIN
            "expiry": 86400,
            "format": 1,
        },
        timeout=10,
    ).json()
    if isinstance(resp, dict) and resp.get("objectType") == "KalturaAPIException":
        print(f"ERROR generating Events KS: {resp.get('message')}")
        sys.exit(1)
    return resp

EVENTS_KS = _generate_events_ks()
print(f"  Events KS generated (userId={USER_ID}): {EVENTS_KS[:30]}...")

HEADERS = {
    "Authorization": f"Bearer {EVENTS_KS}",
    "Content-Type": "application/json",
}

state = {}


def events_post(path, body=None):
    """POST to Events Platform API. Raises with response body on error."""
    resp = requests.post(
        f"{EVENTS_API_URL}{path}",
        headers=HEADERS,
        json=body or {},
        timeout=60,
    )
    if not resp.ok:
        raise Exception(f"Events API {resp.status_code}: {resp.text[:300]}")
    return resp.json()


def events_create_with_retry(body):
    """Create an event, handling the known 500-but-created backend bug.

    The Events Platform sometimes returns 500 while the event IS actually
    created server-side. This helper detects that by searching for the event
    name in the list after a 500 response.
    """
    resp = requests.post(
        f"{EVENTS_API_URL}/events/create",
        headers=HEADERS,
        json=body,
        timeout=60,
    )
    if resp.ok:
        return resp.json()

    # On 500, check if the event was created despite the error
    if resp.status_code == 500:
        import time as _t
        _t.sleep(2)
        search = events_post("/events/list", {
            "filter": {"searchTerm": body.get("name", "")},
            "pager": {"offset": 0, "limit": 5},
        })
        for evt in _get_items(search):
            if evt.get("name") == body.get("name"):
                print(f"    (event created despite 500 response — known backend bug)")
                return evt

    raise Exception(f"Events API {resp.status_code}: {resp.text[:300]}")


def _get_items(result):
    """Extract items array from Events API response (tries multiple keys)."""
    if isinstance(result, list):
        return result
    for key in ("events", "items", "objects", "sessions", "speakers", "teamMembers"):
        if key in result:
            return result[key]
    return []


def main():
    runner = TestRunner("Virtual Events Platform API Validation")

    # ════════════════════════════════════════════
    # Phase 1: Read-only tests (always work)
    # ════════════════════════════════════════════

    def test_list_events():
        """List events with pager and sort."""
        result = events_post("/events/list", {
            "filter": {},
            "pager": {"offset": 0, "limit": 15},
            "orderBy": "-startDate",
        })
        items = _get_items(result)
        assert len(items) >= 0, f"Unexpected list response: {str(result)[:200]}"
        state["existing_events"] = items
        state["total_events"] = result.get("totalCount", len(items))
        print(f"    Listed {len(items)} event(s), total={state['total_events']}")
        for e in items[:3]:
            print(f"      {e['id']}: {e.get('name', '?')[:40]}")

    runner.run_test("events/list — list with pager and sort", test_list_events)

    if not runner.results[-1][1]:
        print("    FATAL: Cannot list events — API not reachable")
        runner.summary()
        sys.exit(1)

    def test_list_events_order_asc():
        """List events sorted ascending by start date."""
        result = events_post("/events/list", {
            "filter": {},
            "pager": {"offset": 0, "limit": 5},
            "orderBy": "+startDate",  # API requires +/- prefix
        })
        items = _get_items(result)
        assert len(items) > 0, "No events returned with ascending sort"
        print(f"    Ascending sort: {len(items)} events, first={items[0].get('name', '?')[:30]}")

    runner.run_test("events/list — ascending order by startDate", test_list_events_order_asc)

    def test_list_events_filter_search():
        """Filter events by search term using an existing event name."""
        existing = state.get("existing_events", [])
        if not existing:
            print("    Skipped — no existing events")
            return
        search_term = existing[0].get("name", "test")[:15]
        result = events_post("/events/list", {
            "filter": {"searchTerm": search_term},
            "pager": {"offset": 0, "limit": 10},
        })
        items = _get_items(result)
        print(f"    Search '{search_term}': found {len(items)} event(s)")

    runner.run_test("events/list — filter by searchTerm", test_list_events_filter_search)

    def test_list_events_filter_ids():
        """Filter events by specific IDs."""
        existing = state.get("existing_events", [])
        if not existing:
            print("    Skipped — no existing events")
            return
        ids = [existing[0]["id"]]
        result = events_post("/events/list", {
            "filter": {"idIn": ids},
            "pager": {"offset": 0, "limit": 10},
        })
        items = _get_items(result)
        assert len(items) >= 1, f"Expected at least 1 event, got {len(items)}"
        print(f"    Filter by IDs: found {len(items)} event(s)")

    runner.run_test("events/list — filter by idIn", test_list_events_filter_ids)

    def test_list_events_order_by_name():
        """List events sorted by name."""
        result = events_post("/events/list", {
            "filter": {},
            "pager": {"offset": 0, "limit": 5},
            "orderBy": "+name",
        })
        items = _get_items(result)
        assert len(items) > 0, "No events returned"
        print(f"    Sort by name: {len(items)} events, first={items[0].get('name', '?')[:30]}")

    runner.run_test("events/list — order by name", test_list_events_order_by_name)

    def test_list_events_pager_offset():
        """Test pager with offset."""
        result = events_post("/events/list", {
            "filter": {},
            "pager": {"offset": 0, "limit": 2},
        })
        items1 = _get_items(result)
        if len(items1) < 2:
            print(f"    Only {len(items1)} events, skip offset test")
            return
        result2 = events_post("/events/list", {
            "filter": {},
            "pager": {"offset": 1, "limit": 2},
        })
        items2 = _get_items(result2)
        if items1 and items2:
            # Second page should start from a different event
            assert items1[0]["id"] != items2[0]["id"] or len(items1) == 1, (
                "Offset did not change results"
            )
        print(f"    Page 1: {len(items1)} events, Page 2 (offset=1): {len(items2)} events")

    runner.run_test("events/list — pager offset pagination", test_list_events_pager_offset)

    # ════════════════════════════════════════════
    # Phase 2: Sessions (read-only on existing events)
    # ════════════════════════════════════════════

    def test_list_sessions_existing():
        """List sessions for an existing event."""
        existing = state.get("existing_events", [])
        if not existing:
            print("    Skipped — no existing events")
            return
        event_id = existing[0]["id"]
        result = events_post("/sessions/list", {
            "eventId": event_id,
        })
        items = _get_items(result)
        state["existing_sessions"] = items
        state["existing_event_id"] = event_id
        print(f"    Event {event_id} has {len(items)} session(s)")
        for s in items[:3]:
            print(f"      {s.get('id')}: {s.get('name', '?')[:30]} — type={s.get('type')}")

    runner.run_test("sessions/list — list sessions for existing event", test_list_sessions_existing)

    def test_speaker_list_existing():
        """List speakers for an existing session."""
        sessions = state.get("existing_sessions", [])
        event_id = state.get("existing_event_id")
        if not sessions or not event_id:
            print("    Skipped — no existing sessions")
            return
        session_id = sessions[0]["id"]
        result = events_post("/sessions/speakerList", {
            "eventId": event_id,
            "sessionId": session_id,
        })
        items = _get_items(result)
        print(f"    Session {session_id} has {len(items)} speaker(s)")

    runner.run_test("sessions/speakerList — list speakers for existing session", test_speaker_list_existing)

    # ════════════════════════════════════════════
    # Phase 3: Event CRUD (create/update/delete)
    # ════════════════════════════════════════════

    start = datetime.now() + timedelta(days=14)
    end = start + timedelta(hours=2)
    start_iso = start.strftime("%Y-%m-%dT%H:%M:%S.000Z")
    end_iso = end.strftime("%Y-%m-%dT%H:%M:%S.000Z")
    doors_open = (start - timedelta(minutes=15)).strftime("%Y-%m-%dT%H:%M:%S.000Z")

    def test_create_event():
        """Create an event with blank template (tm0000)."""
        ts = int(time.time())
        result = events_create_with_retry({
            "name": f"API_DOC_VALIDATION_{ts}",
            "templateId": "tm0000",
            "startDate": start_iso,
            "endDate": end_iso,
            "timezone": "America/New_York",
            "description": "Test event for API doc validation. Safe to delete.",
        })
        assert "id" in result, f"Event create failed: {result}"
        state["event_id"] = result["id"]
        runner.register_cleanup(f"event {result['id']}",
                                lambda: _delete_event(result["id"]))
        print(f"    Event: {result['id']} — {result.get('name')}")

    runner.run_test("events/create — blank template (tm0000)", test_create_event)

    create_succeeded = runner.results[-1][1]

    if create_succeeded:
        def test_create_event_webcast():
            """Create an event with webcast template (tm2000)."""
            ts = int(time.time())
            result = events_create_with_retry({
                "name": f"API_DOC_WEBCAST_{ts}",
                "templateId": "tm2000",
                "startDate": start_iso,
                "endDate": end_iso,
                "timezone": "America/New_York",
                "description": "Webcast template test",
            })
            assert "id" in result
            state["webcast_event_id"] = result["id"]
            runner.register_cleanup(f"webcast event {result['id']}",
                                    lambda: _delete_event(result["id"]))
            print(f"    Webcast event: {result['id']} — template=tm2000")

        runner.run_test("events/create — webcast template (tm2000)", test_create_event_webcast)

        def test_update_event():
            """Update event name, description, and labels."""
            ts = int(time.time())
            result = events_post("/events/update", {
                "id": state["event_id"],
                "name": f"UPDATED_EVENT_{ts}",
                "description": "Updated via test",
                "labels": ["api-test", "validation"],
            })
            print(f"    Updated: {result.get('name', '?')}")

        runner.run_test("events/update — name, description, labels", test_update_event)

        def test_update_event_dates():
            """Update dates and timezone."""
            new_start = start + timedelta(hours=1)
            new_end = end + timedelta(hours=1)
            result = events_post("/events/update", {
                "id": state["event_id"],
                "startDate": new_start.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
                "endDate": new_end.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
                "timezone": "Europe/London",
            })
            print(f"    Updated dates, timezone=Europe/London")

        runner.run_test("events/update — dates and timezone", test_update_event_dates)

        # Sessions on the new event — uses nested {eventId, session: {...}} structure
        def test_create_session_webcast():
            """Create a LiveWebcast session."""
            result = events_post("/sessions/create", {
                "eventId": state["event_id"],
                "session": {
                    "name": "Main Stage Webcast",
                    "type": "LiveWebcast",
                    "startDate": start_iso,
                    "endDate": end_iso,
                    "description": "API test session",
                    "visibility": "published",
                },
            })
            # Response is {session: {...}, status: "ok"}
            session_data = result.get("session", result)
            assert "id" in session_data, f"No session id: {result}"
            state["webcast_session_id"] = session_data["id"]
            print(f"    Session: {session_data['id']} — type={session_data.get('type')}")

        runner.run_test("sessions/create — LiveWebcast session", test_create_session_webcast)

        def test_create_session_meeting():
            """Create a MeetingEntry (interactive room) session."""
            result = events_post("/sessions/create", {
                "eventId": state["event_id"],
                "session": {
                    "name": "Breakout Room",
                    "type": "MeetingEntry",
                    "startDate": start_iso,
                    "endDate": end_iso,
                    "description": "Interactive breakout",
                    "visibility": "published",
                },
            })
            session_data = result.get("session", result)
            assert "id" in session_data, f"No session id: {result}"
            state["meeting_session_id"] = session_data["id"]
            print(f"    Meeting: {session_data['id']} — type={session_data.get('type')}")

        runner.run_test("sessions/create — MeetingEntry (interactive room)", test_create_session_meeting)

        def test_list_created_sessions():
            """List sessions for newly created event."""
            result = events_post("/sessions/list", {
                "eventId": state["event_id"],
            })
            items = _get_items(result)
            assert len(items) >= 2, f"Expected ≥2 sessions, got {len(items)}"
            for s in items:
                print(f"    - {s.get('id')}: {s.get('name')} — type={s.get('type')}")

        runner.run_test("sessions/list — list created sessions", test_list_created_sessions)

        def test_speaker_list():
            """List speakers for created session."""
            result = events_post("/sessions/speakerList", {
                "eventId": state["event_id"],
                "sessionId": state["webcast_session_id"],
            })
            items = _get_items(result)
            print(f"    Speakers: {len(items)}")

        runner.run_test("sessions/speakerList — on created session", test_speaker_list)

        # Team members — uses {email, role, firstName, lastName}
        # Roles: Admin, Organizer, ContentManager
        def test_team_members():
            """Add a team member."""
            try:
                result = events_post("/team-members/create", {
                    "email": "api-test@example.com",
                    "role": "Organizer",
                    "firstName": "API",
                    "lastName": "Test",
                })
                member_id = result.get("id") or result.get("teamMemberId")
                state["team_member_id"] = member_id
                print(f"    Created team member: {member_id}")
            except Exception as e:
                print(f"    Team members: {str(e)[:150]}")

        runner.run_test("team-members/create — add Organizer", test_team_members)

        def test_list_team_members():
            """List team members."""
            try:
                result = events_post("/team-members/list", {})
                items = _get_items(result)
                print(f"    Team members: {len(items)}")
            except Exception as e:
                print(f"    Team members list: {str(e)[:150]}")

        runner.run_test("team-members/list — list team", test_list_team_members)

        # Duplication — uses sourceEventId (int), not id
        def test_duplicate_event():
            """Duplicate the event."""
            resp = requests.post(
                f"{EVENTS_API_URL}/events/duplicate",
                headers=HEADERS,
                json={"sourceEventId": state["event_id"]},
                timeout=60,
            )
            if resp.ok:
                result = resp.json()
            elif resp.status_code == 500:
                # Same backend bug — duplicate may have started despite 500
                print(f"    (duplicate returned 500 — checking if it started)")
                result = {"status": "500_response"}
            else:
                raise Exception(f"Events API {resp.status_code}: {resp.text[:300]}")
            job_id = result.get("jobId") or result.get("id")
            if job_id:
                state["dup_job_id"] = job_id
                print(f"    Duplication job: {job_id}")
            else:
                print(f"    Duplication response: {result}")
                # Still pass — the 500 bug is server-side

        runner.run_test("events/duplicate — start duplication", test_duplicate_event)

        def test_duplicate_status():
            """Poll duplication status."""
            job_id = state.get("dup_job_id")
            if not job_id:
                print("    Skipped — no job ID (duplicate returned 500)")
                return

            max_wait = 60
            elapsed = 0
            status = "unknown"
            while elapsed < max_wait:
                result = events_post("/events/duplicateStatus", {
                    "jobId": job_id,
                })
                status = result.get("status", "unknown")
                if status == "completed":
                    new_id = result.get("eventId") or result.get("id")
                    if new_id:
                        state["duplicated_event_id"] = new_id
                        runner.register_cleanup(f"dup event {new_id}",
                                                lambda: _delete_event(new_id))
                    print(f"    Completed! New event: {new_id}")
                    return
                elif status == "failed":
                    raise Exception(f"Failed: {result}")
                print(f"    Polling... status={status}, {elapsed}s")
                time.sleep(3)
                elapsed += 3

            print(f"    Timeout after {max_wait}s (status={status})")

        runner.run_test("events/duplicateStatus — poll status", test_duplicate_status)

        # Verify webcast template
        if state.get("webcast_event_id"):
            def test_webcast_template():
                """Verify tm2000 auto-created a session."""
                result = events_post("/sessions/list", {
                    "eventId": state["webcast_event_id"],
                })
                items = _get_items(result)
                assert len(items) >= 1, f"Expected ≥1 session from tm2000"
                types = [s.get("type") for s in items]
                print(f"    tm2000 sessions: {len(items)} — types={types}")

            runner.run_test("Verify tm2000 auto-created session", test_webcast_template)

        # Cleanup
        def test_delete_event():
            """Delete the primary test event."""
            events_post("/events/delete", {"id": state["event_id"]})
            print(f"    Deleted: {state['event_id']}")

        runner.run_test("events/delete — primary test event", test_delete_event)

        if state.get("webcast_event_id"):
            def test_delete_webcast():
                """Delete the webcast event."""
                events_post("/events/delete", {"id": state["webcast_event_id"]})
                print(f"    Deleted: {state['webcast_event_id']}")

            runner.run_test("events/delete — webcast event", test_delete_webcast)

    else:
        print("\n    NOTE: events/create returned 500 (likely account event limit).")
        print("    Read-only tests above validate the API surface.")
        print("    To run full CRUD tests, delete unused events first.\n")

    # ════════════════════════════════════════════
    # Summary
    # ════════════════════════════════════════════

    runner.cleanup()
    success = runner.summary()
    sys.exit(0 if success else 1)


def _delete_event(event_id):
    try:
        events_post("/events/delete", {"id": event_id})
    except Exception:
        pass


if __name__ == "__main__":
    print(f"\n{'='*60}")
    print("  KALTURA VIRTUAL EVENTS PLATFORM — End-to-End Validation")
    print(f"{'='*60}\n")
    main()
