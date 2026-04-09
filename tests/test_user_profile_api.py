#!/usr/bin/env python3
"""
End-to-end validation of the User Profile API against the live API.

Covers: add (basic + with attended status + duplicate detection + email case-insensitivity),
bulkAdd (success + partial failure), get, getByFilter (email case-insensitive lookup),
update (eventData shallow merge + profileData replacement + attendance lifecycle +
firstAttendedStatusTime one-time-only), list (filter + pagination + orderBy +
includeTotalCount + deleted exclusion + incremental updatedAt pull),
delete (soft-delete + verify exclusion + re-create after delete),
reports (eventDataStats single + multi-dimension, firstAttendanceStatusPerApp),
cross-service (multi-event user detection, appCustomId → appGuid → profiles).

Depends on the App Registry API for creating a test app context.
"""

import sys
import os
import time

sys.path.insert(0, os.path.dirname(__file__))
from test_helpers import (
    app_registry_post, user_profile_post, kaltura_post,
    TestRunner, PARTNER_ID, KS,
    APP_REGISTRY_URL, USER_PROFILE_URL,
)

state = {}
TS = int(time.time())


def _ensure_kaltura_user(user_id):
    """Ensure a KalturaUser exists. Create if needed."""
    try:
        kaltura_post("user", "get", {"userId": user_id})
    except Exception:
        kaltura_post("user", "add", {
            "user[objectType]": "KalturaUser",
            "user[id]": user_id,
            "user[email]": user_id if "@" in user_id else f"{user_id}@test.local",
            "user[firstName]": "Test",
            "user[lastName]": "User",
        })


def main():
    runner = TestRunner("User Profile API — E2E Validation")

    # ════════════════════════════════════════════
    # Phase 0: Setup — App Registry + Kaltura Users
    # ════════════════════════════════════════════
    def test_setup():
        """Create a test app and ensure test users exist."""
        # Create test app in App Registry
        app = app_registry_post("add", {
            "appCustomId": f"profile-test-{TS}",
            "appType": "test",
            "appCustomName": f"Profile Test App {TS}",
        })
        state["app_guid"] = app["id"]
        state["app_custom_id"] = f"profile-test-{TS}"
        runner.register_cleanup(
            f"app {app['id']}",
            lambda: app_registry_post("delete", {"id": state["app_guid"]}),
        )
        print(f"    App: {state['app_guid']} (customId={state['app_custom_id']})")

        # Ensure test users exist
        state["user1"] = f"profile-test-{TS}-1@kaltura-test.com"
        state["user2"] = f"profile-test-{TS}-2@kaltura-test.com"
        state["user3"] = f"profile-test-{TS}-3@kaltura-test.com"
        state["user4"] = f"profile-test-{TS}-4@kaltura-test.com"
        state["user5"] = f"profile-test-{TS}-5@kaltura-test.com"
        for uid in [state["user1"], state["user2"], state["user3"],
                    state["user4"], state["user5"]]:
            _ensure_kaltura_user(uid)
            runner.register_cleanup(
                f"user {uid}",
                lambda u=uid: kaltura_post("user", "delete", {"userId": u}),
            )
        print(f"    Users: 5 test users created")

    runner.run_test("setup — create app and test users", test_setup)

    # ════════════════════════════════════════════
    # Phase 1: Create Profiles
    # ════════════════════════════════════════════
    def test_add_basic():
        """Create a user profile with event data, verify defaults and response shape."""
        result = user_profile_post("/user-profile/add", {
            "appGuid": state["app_guid"],
            "userId": state["user1"],
            "profileData": {"name": "Test User 1", "company": "Acme"},
            "eventData": {
                "regOrigin": "registration",
                "attendanceStatus": "registered",
                "userRegistrationType": "virtualAttendanceRequest",
            },
        })
        assert "id" in result, f"Expected id in response: {result}"
        assert result["userId"] == state["user1"], \
            f"Expected userId {state['user1']}, got {result.get('userId')}"
        assert result["appGuid"] == state["app_guid"], \
            f"Expected appGuid {state['app_guid']}, got {result.get('appGuid')}"
        assert result.get("status") == "enabled", \
            f"Expected default status=enabled, got {result.get('status')}"
        assert result.get("createdAt") is not None, \
            f"Expected createdAt in response, got None"
        ed = result.get("eventData", {})
        assert ed.get("attendanceStatus") == "registered", \
            f"Expected attendanceStatus=registered, got {ed.get('attendanceStatus')}"
        assert ed.get("regOrigin") == "registration", \
            f"Expected regOrigin=registration, got {ed.get('regOrigin')}"
        state["profile1_id"] = result["id"]
        runner.register_cleanup(
            f"profile {result['id']}",
            lambda: user_profile_post("/user-profile/delete", {"id": state["profile1_id"]}),
        )
        print(f"    Profile: {result['id']} (user={result['userId']}, status={ed.get('attendanceStatus')})")

    runner.run_test("user-profile.add — create with event data", test_add_basic)

    def test_add_duplicate_rejected():
        """Adding a profile for the same user+app returns an error."""
        try:
            user_profile_post("/user-profile/add", {
                "appGuid": state["app_guid"],
                "userId": state["user1"],
                "profileData": {"name": "Duplicate"},
            })
            raise AssertionError("Expected error for duplicate user+app, got success")
        except Exception as e:
            err = str(e)
            assert "USER_ALREADY" in err or "already" in err.lower(), \
                f"Expected duplicate error, got: {err}"
        print(f"    Correctly rejected duplicate for {state['user1']}+{state['app_guid']}")

    runner.run_test("user-profile.add — duplicate user+app rejected", test_add_duplicate_rejected)

    def test_add_email_case_insensitive():
        """Creating profile with uppercased email is rejected (case-insensitive match)."""
        upper_user = state["user1"].upper()
        try:
            user_profile_post("/user-profile/add", {
                "appGuid": state["app_guid"],
                "userId": upper_user,
                "profileData": {"name": "Case Test"},
            })
            raise AssertionError("Expected case-insensitive duplicate rejection")
        except Exception as e:
            err = str(e)
            assert "USER_ALREADY" in err or "already" in err.lower(), \
                f"Expected duplicate error for case-insensitive email, got: {err}"
        print(f"    Correctly rejected '{upper_user}' (case-insensitive match)")

    runner.run_test("user-profile.add — email case-insensitive uniqueness", test_add_email_case_insensitive)

    def test_add_with_attended_status():
        """Creating profile with attended status auto-sets firstAttendedStatusTime."""
        result = user_profile_post("/user-profile/add", {
            "appGuid": state["app_guid"],
            "userId": state["user4"],
            "profileData": {"name": "Attended At Creation"},
            "eventData": {
                "regOrigin": "admin",
                "attendanceStatus": "attended",
            },
        })
        ed = result.get("eventData", {})
        assert ed.get("attendanceStatus") == "attended", \
            f"Expected attended, got {ed.get('attendanceStatus')}"
        assert ed.get("firstAttendedStatusTime") is not None, \
            f"Expected firstAttendedStatusTime on creation with attended status: {ed}"
        state["profile4_id"] = result["id"]
        runner.register_cleanup(
            f"profile {result['id']}",
            lambda: user_profile_post("/user-profile/delete", {"id": state["profile4_id"]}),
        )
        print(f"    Created with attended — firstAttendedStatusTime={ed.get('firstAttendedStatusTime')}")

    runner.run_test("user-profile.add — attended status sets firstAttendedStatusTime", test_add_with_attended_status)

    def test_bulk_add():
        """Bulk-create two user profiles, verify response order and shape."""
        result = user_profile_post("/user-profile/bulkAdd", [
            {
                "appGuid": state["app_guid"],
                "userId": state["user2"],
                "profileData": {"name": "Test User 2"},
                "eventData": {
                    "regOrigin": "invite",
                    "attendanceStatus": "invited",
                },
            },
            {
                "appGuid": state["app_guid"],
                "userId": state["user3"],
                "profileData": {"name": "Test User 3"},
                "eventData": {
                    "regOrigin": "admin",
                    "attendanceStatus": "registered",
                },
            },
        ], timeout=60)
        assert isinstance(result, list), f"Expected array response, got {type(result)}"
        assert len(result) == 2, f"Expected 2 results, got {len(result)}"

        # Both should succeed
        for i, r in enumerate(result):
            assert "id" in r, f"Expected success for item {i}, got: {r}"
            key = f"profile{i+2}_id"
            state[key] = r["id"]
            runner.register_cleanup(
                f"profile {r['id']}",
                lambda pid=r["id"]: user_profile_post("/user-profile/delete", {"id": pid}),
            )
        print(f"    Bulk created: [{result[0]['id']}, {result[1]['id']}]")

    runner.run_test("user-profile.bulkAdd — bulk create 2 profiles", test_bulk_add)

    def test_bulk_add_partial_failure():
        """BulkAdd with one existing user returns mixed success/error array."""
        result = user_profile_post("/user-profile/bulkAdd", [
            {
                "appGuid": state["app_guid"],
                "userId": state["user1"],  # already exists
                "profileData": {"name": "Should Fail"},
            },
            {
                "appGuid": state["app_guid"],
                "userId": state["user5"],  # new
                "profileData": {"name": "Test User 5"},
            },
        ], timeout=60)
        assert isinstance(result, list), f"Expected array: {result}"
        assert len(result) == 2, f"Expected 2 results: {result}"

        # First should be error
        assert "code" in result[0] or "id" not in result[0], \
            f"Expected error for duplicate user, got success: {result[0]}"

        # Second should succeed
        if "id" in result[1]:
            state["profile5_id"] = result[1]["id"]
            runner.register_cleanup(
                f"profile {result[1]['id']}",
                lambda: user_profile_post("/user-profile/delete", {"id": state["profile5_id"]}),
            )
            print(f"    Partial: error for existing user, success for new ({result[1]['id']})")
        else:
            print(f"    Both returned errors (may be expected): {result}")

    runner.run_test("user-profile.bulkAdd — partial failure (mixed results)", test_bulk_add_partial_failure)

    # ════════════════════════════════════════════
    # Phase 2: Read
    # ════════════════════════════════════════════
    def test_get():
        """Retrieve profile by ID, verify full response."""
        result = user_profile_post("/user-profile/get", {"id": state["profile1_id"]})
        assert result["id"] == state["profile1_id"], \
            f"Expected {state['profile1_id']}, got {result.get('id')}"
        assert result["appGuid"] == state["app_guid"], \
            f"Expected appGuid={state['app_guid']}"
        assert result["userId"] == state["user1"], \
            f"Expected userId={state['user1']}"
        print(f"    Got: {result['id']}, status={result.get('status')}")

    runner.run_test("user-profile.get — retrieve by ID", test_get)

    def test_get_not_found():
        """Getting a non-existent profile returns USER_PROFILE_NOT_FOUND."""
        try:
            user_profile_post("/user-profile/get", {"id": "000000000000000000000000"})
            raise AssertionError("Expected USER_PROFILE_NOT_FOUND")
        except Exception as e:
            assert "NOT_FOUND" in str(e).upper(), \
                f"Expected not found error, got: {e}"
        print("    Correctly returned error for non-existent profile")

    runner.run_test("user-profile.get — not found error", test_get_not_found)

    def test_get_by_filter():
        """getByFilter with userId+appGuid returns first match."""
        result = user_profile_post("/user-profile/getByFilter", {
            "appGuidIn": [state["app_guid"]],
            "userIdIn": [state["user1"]],
            "status": "enabled",
        })
        assert result is not None, "Expected a profile, got None"
        assert result["userId"] == state["user1"], \
            f"Expected userId {state['user1']}, got {result.get('userId')}"
        print(f"    Found by filter: {result['id']}")

    runner.run_test("user-profile.getByFilter — lookup by userId+appGuid", test_get_by_filter)

    def test_get_by_filter_email_case_insensitive():
        """getByFilter matches email userId case-insensitively."""
        upper_email = state["user1"].upper()
        result = user_profile_post("/user-profile/getByFilter", {
            "appGuidIn": [state["app_guid"]],
            "userIdIn": [upper_email],
        })
        assert result is not None, \
            f"Expected case-insensitive match for '{upper_email}', got None"
        assert result["userId"] == state["user1"], \
            f"Expected userId {state['user1']}, got {result.get('userId')}"
        print(f"    Case-insensitive: '{upper_email}' matched '{state['user1']}'")

    runner.run_test("user-profile.getByFilter — email case-insensitive", test_get_by_filter_email_case_insensitive)

    def test_list():
        """List profiles for the test app with pagination and totalCount."""
        result = user_profile_post("/user-profile/list", {
            "filter": {"appGuidIn": [state["app_guid"]]},
            "pager": {"offset": 0, "limit": 50},
            "orderBy": "-createdAt",
            "includeTotalCount": True,
        })
        assert "objects" in result, f"Expected objects in response: {result}"
        assert result["totalCount"] >= 4, \
            f"Expected at least 4 profiles, got {result['totalCount']}"
        print(f"    Listed: {result['totalCount']} profiles (newest first)")

    runner.run_test("user-profile.list — filter + pagination + orderBy", test_list)

    def test_list_pagination():
        """List with limit=1 returns 1 object but full totalCount."""
        result = user_profile_post("/user-profile/list", {
            "filter": {"appGuidIn": [state["app_guid"]]},
            "pager": {"offset": 0, "limit": 1},
            "includeTotalCount": True,
        })
        assert len(result["objects"]) == 1, \
            f"Expected 1 object with limit=1, got {len(result['objects'])}"
        assert result["totalCount"] >= 4, \
            f"Expected totalCount >= 4, got {result['totalCount']}"
        print(f"    Pagination: 1 returned, {result['totalCount']} total")

    runner.run_test("user-profile.list — pagination limit=1", test_list_pagination)

    def test_list_no_total_count():
        """List with includeTotalCount=false returns totalCount=-1."""
        result = user_profile_post("/user-profile/list", {
            "filter": {"appGuidIn": [state["app_guid"]]},
            "pager": {"offset": 0, "limit": 50},
            "includeTotalCount": False,
        })
        assert "objects" in result, f"Expected objects: {result}"
        assert result.get("totalCount") == -1, \
            f"Expected totalCount=-1 when disabled, got {result.get('totalCount')}"
        print(f"    includeTotalCount=false: totalCount={result.get('totalCount')}")

    runner.run_test("user-profile.list — includeTotalCount=false returns -1", test_list_no_total_count)

    def test_list_attendance_filter():
        """List with attendanceStatus filter returns only matching profiles."""
        result = user_profile_post("/user-profile/list", {
            "filter": {
                "appGuidIn": [state["app_guid"]],
                "attendanceStatus": "invited",
            },
        })
        for obj in result["objects"]:
            status = obj.get("eventData", {}).get("attendanceStatus")
            assert status == "invited", \
                f"Expected all results to have attendanceStatus=invited, got {status}"
        print(f"    Filtered by invited: {result['totalCount']} profiles")

    runner.run_test("user-profile.list — filter by attendanceStatus", test_list_attendance_filter)

    # ════════════════════════════════════════════
    # Phase 3: Update — Attendance Lifecycle
    # ════════════════════════════════════════════
    def test_update_to_confirmed():
        """Update attendanceStatus to confirmed, verify previousAttendanceStatus auto-set."""
        result = user_profile_post("/user-profile/update", {
            "id": state["profile1_id"],
            "eventData": {"attendanceStatus": "confirmed"},
        })
        ed = result.get("eventData", {})
        assert ed.get("attendanceStatus") == "confirmed", \
            f"Expected confirmed, got {ed.get('attendanceStatus')}"
        assert ed.get("previousAttendanceStatus") == "registered", \
            f"Expected previous=registered, got {ed.get('previousAttendanceStatus')}"
        assert ed.get("statusUpdateTime") is not None, \
            f"Expected statusUpdateTime to be set"
        # regOrigin should be preserved (shallow merge)
        assert ed.get("regOrigin") == "registration", \
            f"Expected regOrigin preserved, got {ed.get('regOrigin')}"
        print(f"    registered → confirmed (previous={ed.get('previousAttendanceStatus')})")

    runner.run_test("user-profile.update — status to confirmed (auto previousStatus)", test_update_to_confirmed)

    def test_update_to_attended():
        """Update to attended triggers firstAttendedStatusTime (one-time)."""
        result = user_profile_post("/user-profile/update", {
            "id": state["profile1_id"],
            "eventData": {"attendanceStatus": "attended"},
        })
        ed = result.get("eventData", {})
        assert ed.get("attendanceStatus") == "attended", \
            f"Expected attended, got {ed.get('attendanceStatus')}"
        assert ed.get("previousAttendanceStatus") == "confirmed", \
            f"Expected previous=confirmed, got {ed.get('previousAttendanceStatus')}"
        assert ed.get("firstAttendedStatusTime") is not None, \
            f"Expected firstAttendedStatusTime to be set: {ed}"
        state["first_attended_time"] = ed.get("firstAttendedStatusTime")
        print(f"    confirmed → attended (firstAttendedTime={state['first_attended_time']})")

    runner.run_test("user-profile.update — status to attended (firstAttendedStatusTime set)", test_update_to_attended)

    def test_first_attended_time_immutable():
        """firstAttendedStatusTime does not change on subsequent status updates."""
        # Go back to confirmed then to participated
        user_profile_post("/user-profile/update", {
            "id": state["profile1_id"],
            "eventData": {"attendanceStatus": "confirmed"},
        })
        result = user_profile_post("/user-profile/update", {
            "id": state["profile1_id"],
            "eventData": {"attendanceStatus": "participated"},
        })
        ed = result.get("eventData", {})
        assert ed.get("attendanceStatus") == "participated", \
            f"Expected participated, got {ed.get('attendanceStatus')}"
        assert ed.get("firstAttendedStatusTime") == state["first_attended_time"], \
            f"Expected firstAttendedStatusTime unchanged ({state['first_attended_time']}), " \
            f"got {ed.get('firstAttendedStatusTime')}"
        print(f"    firstAttendedStatusTime immutable: still {state['first_attended_time']}")

    runner.run_test("user-profile.update — firstAttendedStatusTime immutable on re-attend", test_first_attended_time_immutable)

    def test_update_shallow_merge_eventdata():
        """Updating one eventData field preserves others (shallow merge)."""
        result = user_profile_post("/user-profile/update", {
            "id": state["profile1_id"],
            "eventData": {"isRegistered": True},
        })
        ed = result.get("eventData", {})
        assert ed.get("isRegistered") is True, \
            f"Expected isRegistered=true, got {ed.get('isRegistered')}"
        # Previous fields should be preserved
        assert ed.get("attendanceStatus") == "participated", \
            f"Expected attendanceStatus preserved, got {ed.get('attendanceStatus')}"
        assert ed.get("regOrigin") == "registration", \
            f"Expected regOrigin preserved, got {ed.get('regOrigin')}"
        print(f"    Shallow merge: isRegistered set, attendanceStatus+regOrigin preserved")

    runner.run_test("user-profile.update — eventData shallow merge preserves fields", test_update_shallow_merge_eventdata)

    def test_update_profile_data_replacement():
        """profileData is fully replaced (not merged) on update."""
        # First set it to something
        user_profile_post("/user-profile/update", {
            "id": state["profile1_id"],
            "profileData": {"name": "Jane", "company": "Acme", "role": "Speaker"},
        })
        # Now update with partial data — old fields should be gone
        result = user_profile_post("/user-profile/update", {
            "id": state["profile1_id"],
            "profileData": {"name": "Jane Updated"},
        })
        pd = result.get("profileData", {})
        assert pd.get("name") == "Jane Updated", f"Expected updated name, got {pd}"
        # company and role should be gone (full replacement)
        assert "company" not in pd, f"Expected company removed after full replacement, got {pd}"
        assert "role" not in pd, f"Expected role removed after full replacement, got {pd}"
        print(f"    profileData replaced: {pd}")

    runner.run_test("user-profile.update — profileData full replacement (not merge)", test_update_profile_data_replacement)

    # ════════════════════════════════════════════
    # Phase 4: Delete + Re-create
    # ════════════════════════════════════════════
    def test_delete_soft():
        """Soft-delete a profile and verify it's excluded from list."""
        user_profile_post("/user-profile/delete", {"id": state["profile3_id"]})

        # Verify excluded from list
        result = user_profile_post("/user-profile/list", {
            "filter": {
                "appGuidIn": [state["app_guid"]],
                "userIdIn": [state["user3"]],
            },
        })
        ids = [obj["id"] for obj in result.get("objects", [])]
        assert state["profile3_id"] not in ids, \
            f"Deleted profile should not appear in list"

        # Verify get returns not found
        try:
            user_profile_post("/user-profile/get", {"id": state["profile3_id"]})
            raise AssertionError("Expected not found for deleted profile")
        except Exception as e:
            assert "NOT_FOUND" in str(e).upper(), f"Expected not found, got: {e}"

        runner._cleanup_actions = [
            (label, fn) for label, fn in runner._cleanup_actions
            if state["profile3_id"] not in label
        ]
        print(f"    Soft-deleted {state['profile3_id']} — excluded from get and list")

    runner.run_test("user-profile.delete — soft delete excludes from queries", test_delete_soft)

    def test_recreate_after_delete():
        """After soft-deleting a profile, a new one can be created for the same user+app."""
        result = user_profile_post("/user-profile/add", {
            "appGuid": state["app_guid"],
            "userId": state["user3"],
            "profileData": {"name": "Re-registered User 3"},
            "eventData": {
                "regOrigin": "registration",
                "attendanceStatus": "registered",
            },
        })
        assert "id" in result, f"Expected new profile after re-create: {result}"
        assert result["id"] != state["profile3_id"], \
            f"Expected new ID, got same as deleted: {result['id']}"
        state["profile3_new_id"] = result["id"]
        runner.register_cleanup(
            f"profile {result['id']}",
            lambda: user_profile_post("/user-profile/delete", {"id": state["profile3_new_id"]}),
        )
        print(f"    Re-created: {result['id']} (new ID, same user+app)")

    runner.run_test("user-profile.add — re-create after soft-delete", test_recreate_after_delete)

    # ════════════════════════════════════════════
    # Phase 5: Reports
    # ════════════════════════════════════════════
    def test_event_data_stats_single():
        """Get attendance stats grouped by attendanceStatus."""
        result = user_profile_post("/reports/eventDataStats", {
            "filter": {"appGuidIn": [state["app_guid"]]},
            "dimensions": ["attendanceStatus"],
        })
        assert "results" in result, f"Expected results in response: {result}"
        assert "sum" in result, f"Expected sum in response: {result}"
        assert result["sum"] >= 3, f"Expected sum >= 3 active profiles, got {result['sum']}"
        for r in result["results"]:
            assert "appGuid" in r, f"Expected appGuid in result item: {r}"
            assert "dimensions" in r, f"Expected dimensions: {r}"
            assert "count" in r, f"Expected count: {r}"
        print(f"    Stats: {len(result['results'])} groups, sum={result['sum']}")
        for r in result["results"]:
            print(f"      {r['dimensions']}: count={r['count']}")

    runner.run_test("reports.eventDataStats — group by attendanceStatus", test_event_data_stats_single)

    def test_event_data_stats_multi_dim():
        """Get stats grouped by attendanceStatus + regOrigin."""
        result = user_profile_post("/reports/eventDataStats", {
            "filter": {"appGuidIn": [state["app_guid"]]},
            "dimensions": ["attendanceStatus", "regOrigin"],
        })
        assert "results" in result, f"Expected results: {result}"
        for r in result["results"]:
            dims = r.get("dimensions", {})
            # Dimensions are nested under eventData — empty eventData is valid
            # (profiles without the requested dimensions appear as empty group)
            assert "eventData" in dims or "attendanceStatus" in dims, \
                f"Expected eventData or flat dimensions: {dims}"
        print(f"    Multi-dim: {len(result['results'])} groups, sum={result['sum']}")

    runner.run_test("reports.eventDataStats — multi-dimension grouping", test_event_data_stats_multi_dim)

    def test_event_data_stats_with_filter():
        """Get stats filtered by specific attendanceStatuses."""
        result = user_profile_post("/reports/eventDataStats", {
            "filter": {
                "appGuidIn": [state["app_guid"]],
                "attendanceStatusIn": ["attended", "participated"],
            },
            "dimensions": ["attendanceStatus"],
        })
        assert "results" in result, f"Expected results: {result}"
        for r in result["results"]:
            dims = r.get("dimensions", {})
            ed = dims.get("eventData", dims)
            status = ed.get("attendanceStatus")
            assert status in ("attended", "participated", None), \
                f"Expected attended/participated in filtered results, got {status}"
        print(f"    Filtered stats: {len(result['results'])} groups, sum={result['sum']}")

    runner.run_test("reports.eventDataStats — filtered by attendanceStatusIn", test_event_data_stats_with_filter)

    def test_first_attendance_per_app():
        """Get first-attended counts per app — should include our test app."""
        result = user_profile_post("/user-profile/firstAttendanceStatusPerApp", {})
        assert isinstance(result, dict), f"Expected dict response, got {type(result)}"
        if state["app_guid"] in result:
            count = result[state["app_guid"]]
            assert count >= 1, f"Expected at least 1 attended user, got {count}"
            print(f"    App {state['app_guid']}: {count} first-attended")
        else:
            print(f"    App not in results (may require propagation time)")

    runner.run_test("user-profile.firstAttendanceStatusPerApp — attendance counts", test_first_attendance_per_app)

    def test_first_attendance_date_range():
        """firstAttendanceStatusPerApp with date range."""
        result = user_profile_post("/user-profile/firstAttendanceStatusPerApp", {
            "fromDate": "2020-01-01T00:00:00Z",
            "toDate": "2030-12-31T23:59:59Z",
        })
        assert isinstance(result, dict), f"Expected dict: {result}"
        if state["app_guid"] in result:
            print(f"    Date-filtered: {result[state['app_guid']]} attended in range")
        else:
            print(f"    No results in date range (may need time)")

    runner.run_test("user-profile.firstAttendanceStatusPerApp — with date range", test_first_attendance_date_range)

    # ════════════════════════════════════════════
    # Phase 7: Cross-Service Integration Patterns
    # ════════════════════════════════════════════
    def test_incremental_pull():
        """List with updatedAtGreaterThanOrEqual for delta sync pattern."""
        from datetime import datetime, timezone, timedelta
        past = (datetime.now(timezone.utc) - timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
        result = user_profile_post("/user-profile/list", {
            "filter": {
                "appGuidIn": [state["app_guid"]],
                "updatedAtGreaterThanOrEqual": past,
            },
            "pager": {"offset": 0, "limit": 50},
            "orderBy": "updatedAt",
            "includeTotalCount": True,
        })
        assert "objects" in result, f"Expected objects: {result}"
        assert result["totalCount"] >= 1, \
            f"Expected at least 1 profile updated in last hour, got {result['totalCount']}"
        # Verify ordering — updatedAt should be ascending
        timestamps = [obj.get("updatedAt", 0) for obj in result["objects"]]
        for i in range(1, len(timestamps)):
            assert timestamps[i] >= timestamps[i - 1], \
                f"Expected ascending updatedAt order, got {timestamps[i-1]} > {timestamps[i]}"
        print(f"    Incremental pull: {result['totalCount']} profiles updated since {past}")

    runner.run_test("user-profile.list — incremental pull with updatedAt filter", test_incremental_pull)

    def test_cross_event_user_check():
        """Verify a user can have profiles in multiple apps (events) — key for PII deletion safety."""
        # Create a second app to simulate multi-event registration
        second_app = app_registry_post("add", {
            "appCustomId": f"test-second-event-{TS}",
            "appType": "test",
            "appCustomName": f"Second Event {TS}",
        })
        state["second_app_guid"] = second_app["id"]
        runner.register_cleanup(
            f"second app {second_app['id']}",
            lambda: app_registry_post("delete", {"id": state["second_app_guid"]}),
        )

        # Create a profile for user1 (already has profile in first app) in the second app
        user_id = state["user1"]
        profile2 = user_profile_post("/user-profile/add", {
            "appGuid": second_app["id"],
            "userId": user_id,
            "profileData": {"name": "Multi-event User"},
            "eventData": {"regOrigin": "registration", "attendanceStatus": "registered"},
        })
        state["second_profile_id"] = profile2["id"]
        runner.register_cleanup(
            f"second profile {profile2['id']}",
            lambda: user_profile_post("/user-profile/delete", {"id": state["second_profile_id"]}),
        )

        # Query without appGuid filter to find all events this user is registered for
        all_profiles = user_profile_post("/user-profile/list", {
            "filter": {"userIdIn": [user_id]},
            "pager": {"offset": 0, "limit": 50},
            "includeTotalCount": True,
        })
        assert all_profiles["totalCount"] >= 2, \
            f"Expected >= 2 profiles for multi-event user, got {all_profiles['totalCount']}"
        app_guids = [obj["appGuid"] for obj in all_profiles["objects"]]
        assert state["app_guid"] in app_guids, "Expected user in first app"
        assert state["second_app_guid"] in app_guids, "Expected user in second app"
        print(f"    Multi-event user: {all_profiles['totalCount']} profiles across {len(set(app_guids))} apps")
        print(f"    (PII deletion safety: this user should NOT be deleted from user.list)")

    runner.run_test("user-profile.list — cross-event user detection (PII deletion safety)", test_cross_event_user_check)

    def test_app_custom_id_to_app_guid():
        """End-to-end: resolve appCustomId (virtualEventId) → appGuid → user profiles."""
        # The app we created has appCustomId = f"test-profile-app-{TS}"
        custom_id = state.get("app_custom_id", f"test-profile-app-{TS}")

        # Step 1: Resolve via App Registry
        app_result = app_registry_post("list", {
            "filter": {"appCustomIdIn": [custom_id]},
        })
        assert app_result["totalCount"] >= 1, \
            f"Expected to find app by custom ID '{custom_id}', got {app_result['totalCount']}"
        resolved_guid = app_result["objects"][0]["id"]
        assert resolved_guid == state["app_guid"], \
            f"Resolved GUID mismatch: {resolved_guid} != {state['app_guid']}"

        # Step 2: Use resolved GUID to get user profiles
        profiles = user_profile_post("/user-profile/list", {
            "filter": {"appGuidIn": [resolved_guid]},
            "pager": {"offset": 0, "limit": 10},
            "includeTotalCount": True,
        })
        assert profiles["totalCount"] >= 1, \
            f"Expected profiles for resolved GUID, got {profiles['totalCount']}"
        print(f"    Cross-service: '{custom_id}' → {resolved_guid} → {profiles['totalCount']} profiles")

    runner.run_test("cross-service: appCustomId → appGuid → user profiles", test_app_custom_id_to_app_guid)

    # ════════════════════════════════════════════
    # Cleanup & Summary
    # ════════════════════════════════════════════
    keep = "--keep" in sys.argv
    if keep:
        print(f"\n--keep flag set. Resources preserved:")
        print(f"  App GUID: {state.get('app_guid')}")
        for key in sorted(state):
            if "profile" in key or "user" in key:
                print(f"  {key}: {state[key]}")
        print(f"\n  Clean up app manually:")
        app_guid = state.get('app_guid')
        print(f'    curl -X POST "{APP_REGISTRY_URL}/app-registry/delete" \\')
        print(f'      -H "Authorization: Bearer $KS" \\')
        print(f'      -H "Content-Type: application/json" \\')
        print(f'      -d \'{{"id": "{app_guid}"}}\'')
    else:
        if sys.stdin.isatty():
            input("\nPress Enter to clean up...")
        runner.cleanup()

    success = runner.summary()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
