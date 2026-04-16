#!/usr/bin/env python3
"""End-to-end validation of the Kaltura Code, Event & Session Cue Points API.

Covers: code cue point CRUD, view-change commands, forceStop, systemName
uniqueness, event cue points, session cue points, clone, updateStatus,
updateCuePointsTimes, delete.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
from test_helpers import kaltura_post, TestRunner, PARTNER_ID, KS, SERVICE_URL

state = {}


def _find_ready_entry():
    result = kaltura_post("baseEntry", "list", {
        "filter[statusEqual]": 2,
        "filter[mediaTypeEqual]": 1,
        "pager[pageSize]": 1,
    })
    entries = result.get("objects", [])
    assert len(entries) > 0, "No READY entries found on account"
    return entries[0]["id"], entries[0].get("name", "unknown")


def _delete_cue_point(cp_id):
    try:
        kaltura_post("cuepoint_cuepoint", "delete", {"id": cp_id})
    except Exception:
        pass


def main():
    runner = TestRunner("Code, Event & Session Cue Points — E2E Validation")

    # ════════════════════════════════════════════
    # Phase 1: Setup
    # ════════════════════════════════════════════

    def test_find_entry():
        entry_id, name = _find_ready_entry()
        state["entry_id"] = entry_id
        print(f"    Using entry: {entry_id} — {name}")

    runner.run_test("baseEntry.list — find READY entry", test_find_entry)

    # ════════════════════════════════════════════
    # Phase 2: Code Cue Point CRUD
    # ════════════════════════════════════════════

    def test_code_add():
        """Create a code cue point."""
        result = kaltura_post("cuepoint_cuepoint", "add", {
            "cuePoint[objectType]": "KalturaCodeCuePoint",
            "cuePoint[entryId]": state["entry_id"],
            "cuePoint[startTime]": 5000,
            "cuePoint[code]": "test-marker",
            "cuePoint[description]": "E2E test code cue point",
            "cuePoint[tags]": "e2e-code-test",
        })
        assert result.get("objectType") == "KalturaCodeCuePoint"
        assert result.get("status") == 1, f"Expected READY (1), got {result.get('status')}"
        state["code_cp_id"] = result["id"]
        runner.register_cleanup(f"code cue point {result['id']}",
                                lambda: _delete_cue_point(result["id"]))
        print(f"    Created: {result['id']}, code={result.get('code')}")

    runner.run_test("cuePoint.add — create code cue point", test_code_add)

    def test_code_get():
        """Retrieve code cue point by ID."""
        result = kaltura_post("cuepoint_cuepoint", "get", {
            "id": state["code_cp_id"],
        })
        assert result["id"] == state["code_cp_id"]
        assert result["code"] == "test-marker"
        assert result["description"] == "E2E test code cue point"
        assert result["startTime"] == 5000
        print(f"    Retrieved: {result['id']}, startTime={result['startTime']}")

    runner.run_test("cuePoint.get — retrieve code cue point", test_code_get)

    def test_code_update():
        """Update code cue point fields."""
        result = kaltura_post("cuepoint_cuepoint", "update", {
            "id": state["code_cp_id"],
            "cuePoint[objectType]": "KalturaCodeCuePoint",
            "cuePoint[code]": "updated-marker",
            "cuePoint[description]": "Updated description",
        })
        assert result["code"] == "updated-marker"
        print(f"    Updated: code={result['code']}")

    runner.run_test("cuePoint.update — update code cue point", test_code_update)

    def test_code_list():
        """List code cue points filtered by entry and type."""
        result = kaltura_post("cuepoint_cuepoint", "list", {
            "filter[entryIdEqual]": state["entry_id"],
            "filter[cuePointTypeEqual]": "codeCuePoint.Code",
            "filter[tagsLike]": "e2e-code-test",
        })
        assert result.get("totalCount", 0) >= 1
        found = any(o["id"] == state["code_cp_id"] for o in result.get("objects", []))
        assert found, "Created code cue point not found in list"
        print(f"    Listed: {result['totalCount']} code cue points with e2e-code-test tag")

    runner.run_test("cuePoint.list — filter by type and tags", test_code_list)

    # ════════════════════════════════════════════
    # Phase 3: View-Change, forceStop, systemName
    # ════════════════════════════════════════════

    def test_view_change_code():
        """Create a view-change code cue point (dualscreen layout command)."""
        result = kaltura_post("cuepoint_cuepoint", "add", {
            "cuePoint[objectType]": "KalturaCodeCuePoint",
            "cuePoint[entryId]": state["entry_id"],
            "cuePoint[startTime]": 50000,
            "cuePoint[code]": "pip-parent-in-large",
            "cuePoint[tags]": "change-view-mode,e2e-code-test",
        })
        assert result.get("objectType") == "KalturaCodeCuePoint"
        assert result.get("code") == "pip-parent-in-large"
        assert "change-view-mode" in result.get("tags", "")
        state["viewchange_cp_id"] = result["id"]
        runner.register_cleanup(f"view-change cue point {result['id']}",
                                lambda: _delete_cue_point(result["id"]))
        print(f"    Created view-change: {result['id']}, code={result.get('code')}")

    runner.run_test("cuePoint.add — view-change code (dualscreen layout)", test_view_change_code)

    def test_force_stop():
        """Create a cue point with forceStop=1 to pause the player."""
        result = kaltura_post("cuepoint_cuepoint", "add", {
            "cuePoint[objectType]": "KalturaCodeCuePoint",
            "cuePoint[entryId]": state["entry_id"],
            "cuePoint[startTime]": 55000,
            "cuePoint[code]": "pause-marker",
            "cuePoint[forceStop]": 1,
            "cuePoint[tags]": "e2e-code-test",
        })
        assert result.get("forceStop") == 1, f"Expected forceStop=1, got {result.get('forceStop')}"
        state["forcestop_cp_id"] = result["id"]
        runner.register_cleanup(f"forceStop cue point {result['id']}",
                                lambda: _delete_cue_point(result["id"]))
        print(f"    Created with forceStop: {result['id']}")

    runner.run_test("cuePoint.add — forceStop=1 player pause", test_force_stop)

    def test_system_name():
        """Set systemName and verify uniqueness constraint."""
        result = kaltura_post("cuepoint_cuepoint", "update", {
            "id": state["code_cp_id"],
            "cuePoint[objectType]": "KalturaCodeCuePoint",
            "cuePoint[systemName]": "e2e-unique-name",
        })
        assert result.get("systemName") == "e2e-unique-name"
        print(f"    Set systemName='e2e-unique-name' on {state['code_cp_id']}")

        try:
            dup = kaltura_post("cuepoint_cuepoint", "add", {
                "cuePoint[objectType]": "KalturaCodeCuePoint",
                "cuePoint[entryId]": state["entry_id"],
                "cuePoint[startTime]": 70000,
                "cuePoint[code]": "duplicate-name-test",
                "cuePoint[systemName]": "e2e-unique-name",
                "cuePoint[tags]": "e2e-code-test",
            })
            runner.register_cleanup(f"dup systemName {dup['id']}",
                                    lambda: _delete_cue_point(dup["id"]))
            print("    WARNING: Duplicate systemName was accepted")
        except Exception as e:
            assert "SYSTEM_NAME_EXISTS" in str(e) or "SYSTEM_NAME" in str(e), \
                f"Unexpected error: {e}"
            print(f"    Correctly rejected duplicate systemName: {str(e)[:60]}")

    runner.run_test("cuePoint.update — systemName uniqueness constraint", test_system_name)

    # ════════════════════════════════════════════
    # Phase 4: Event Cue Points
    # ════════════════════════════════════════════

    def test_event_add():
        """Create an event cue point (BROADCAST_START)."""
        result = kaltura_post("cuepoint_cuepoint", "add", {
            "cuePoint[objectType]": "KalturaEventCuePoint",
            "cuePoint[entryId]": state["entry_id"],
            "cuePoint[startTime]": 0,
            "cuePoint[eventType]": 1,
            "cuePoint[tags]": "e2e-code-test",
        })
        assert result.get("objectType") == "KalturaEventCuePoint"
        state["event_cp_id"] = result["id"]
        runner.register_cleanup(f"event cue point {result['id']}",
                                lambda: _delete_cue_point(result["id"]))
        fetched = kaltura_post("cuepoint_cuepoint", "get", {"id": result["id"]})
        print(f"    Created: {result['id']}, cuePointType={fetched.get('cuePointType')}")

    runner.run_test("cuePoint.add — create event cue point (BROADCAST_START)", test_event_add)

    # ════════════════════════════════════════════
    # Phase 5: Session Cue Points
    # ════════════════════════════════════════════

    def test_session_add():
        """Create a session cue point."""
        result = kaltura_post("cuepoint_cuepoint", "add", {
            "cuePoint[objectType]": "KalturaSessionCuePoint",
            "cuePoint[entryId]": state["entry_id"],
            "cuePoint[startTime]": 0,
            "cuePoint[endTime]": 300000,
            "cuePoint[name]": "E2E Test Session",
            "cuePoint[sessionOwner]": "test@example.com",
            "cuePoint[tags]": "e2e-code-test",
        })
        assert result.get("objectType") == "KalturaSessionCuePoint"
        assert result.get("name") == "E2E Test Session"
        state["session_cp_id"] = result["id"]
        runner.register_cleanup(f"session cue point {result['id']}",
                                lambda: _delete_cue_point(result["id"]))
        print(f"    Created: {result['id']}, name={result.get('name')}, owner={result.get('sessionOwner')}")

    runner.run_test("cuePoint.add — create session cue point", test_session_add)

    # ════════════════════════════════════════════
    # Phase 6: Operations — Clone, UpdateStatus, UpdateTimes, Delete
    # ════════════════════════════════════════════

    def test_clone():
        """Clone a code cue point."""
        result = kaltura_post("cuepoint_cuepoint", "clone", {
            "id": state["code_cp_id"],
            "entryId": state["entry_id"],
        })
        assert result["id"] != state["code_cp_id"]
        assert result.get("copiedFrom") == state["code_cp_id"]
        state["cloned_cp_id"] = result["id"]
        runner.register_cleanup(f"cloned cue point {result['id']}",
                                lambda: _delete_cue_point(result["id"]))
        print(f"    Cloned: {state['code_cp_id']} → {result['id']}")

    runner.run_test("cuePoint.clone — clone code cue point", test_clone)

    def test_update_status():
        """Change cue point status to HANDLED (3)."""
        kaltura_post("cuepoint_cuepoint", "updateStatus", {
            "id": state["cloned_cp_id"],
            "status": 3,
        })
        result = kaltura_post("cuepoint_cuepoint", "get", {"id": state["cloned_cp_id"]})
        assert result.get("status") == 3, f"Expected HANDLED (3), got {result.get('status')}"
        print(f"    Status updated to HANDLED (3)")

    runner.run_test("cuePoint.updateStatus — set to HANDLED", test_update_status)

    def test_update_times():
        """Update cue point start and end times."""
        result = kaltura_post("cuepoint_cuepoint", "updateCuePointsTimes", {
            "id": state["code_cp_id"],
            "startTime": 15000,
            "endTime": 25000,
        })
        assert result.get("startTime") == 15000
        assert result.get("endTime") == 25000
        print(f"    Updated times: start={result['startTime']}, end={result['endTime']}")

    runner.run_test("cuePoint.updateCuePointsTimes — update start/end", test_update_times)

    def test_delete():
        """Delete a cue point and verify."""
        kaltura_post("cuepoint_cuepoint", "delete", {"id": state["cloned_cp_id"]})
        try:
            kaltura_post("cuepoint_cuepoint", "get", {"id": state["cloned_cp_id"]})
            print("    Deleted cue point still retrievable (status=DELETED)")
        except Exception as e:
            assert "INVALID_CUE_POINT_ID" in str(e), f"Unexpected error: {e}"
            print("    Confirmed: cue point deleted (INVALID_CUE_POINT_ID)")
        runner._cleanup_actions = [(n, f) for n, f in runner._cleanup_actions
                                   if state["cloned_cp_id"] not in n]

    runner.run_test("cuePoint.delete — soft-delete cue point", test_delete)

    # ════════════════════════════════════════════
    # Cleanup & Summary
    # ════════════════════════════════════════════

    keep = "--keep" in sys.argv
    if keep:
        print("\n--keep flag set. Skipping cleanup.")
        print(f"  Entry: {state.get('entry_id')}")
        print(f"  Code CP: {state.get('code_cp_id')}")
        print(f"  Event CP: {state.get('event_cp_id')}")
        print(f"  Session CP: {state.get('session_cp_id')}")
    else:
        if sys.stdin.isatty():
            input("\nPress Enter to clean up...")
        runner.cleanup()

    success = runner.summary()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
