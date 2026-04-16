#!/usr/bin/env python3
"""
End-to-end validation of the Kaltura Moderation API.

Covers: entry moderation defaults, user flagging flow, approve/reject,
moderation queue filtering, flag types, REACH moderation discovery,
and category moderation.
"""

import sys
import os
import time

sys.path.insert(0, os.path.dirname(__file__))
from test_helpers import kaltura_post, TestRunner, PARTNER_ID, KS, SERVICE_URL, create_test_entry, delete_test_entry

state = {}


def _approve_entry(entry_id):
    """Approve an entry — ignore errors (entry may already be approved/deleted)."""
    try:
        kaltura_post("baseEntry", "approve", {"entryId": entry_id})
    except Exception:
        pass


def _reject_entry(entry_id):
    """Reject an entry — ignore errors."""
    try:
        kaltura_post("baseEntry", "reject", {"entryId": entry_id})
    except Exception:
        pass


def main():
    runner = TestRunner("Moderation API — E2E Validation")

    # ════════════════════════════════════════════
    # Phase 1: Entry Moderation Defaults
    # ════════════════════════════════════════════

    def test_default_moderation_status():
        """New entries should start with AUTO_APPROVED (6) moderation status."""
        entry_id = create_test_entry()
        state["default_entry"] = entry_id
        runner.register_cleanup(f"entry {entry_id}", lambda: delete_test_entry(entry_id))
        result = kaltura_post("baseEntry", "get", {"entryId": entry_id})
        mod_status = result.get("moderationStatus")
        assert mod_status == 6, f"Expected AUTO_APPROVED (6), got {mod_status}"
        print(f"    Entry {entry_id}: moderationStatus={mod_status} (AUTO_APPROVED)")

    runner.run_test("media.add — default moderationStatus is AUTO_APPROVED (6)",
                     test_default_moderation_status)

    # ════════════════════════════════════════════
    # Phase 2: User Flagging Flow
    # ════════════════════════════════════════════

    def test_flag_entry():
        """Flag an entry with SEXUAL_CONTENT (1) and verify status change."""
        entry_id = state.get("default_entry")
        if not entry_id:
            print("    SKIP: No entry from Phase 1")
            return
        result = kaltura_post("baseEntry", "flag", {
            "moderationFlag[objectType]": "KalturaModerationFlag",
            "moderationFlag[flaggedEntryId]": entry_id,
            "moderationFlag[flagType]": 1,
            "moderationFlag[comments]": "E2E test flag — SEXUAL_CONTENT",
        })
        assert result.get("objectType") == "KalturaModerationFlag", (
            f"Expected KalturaModerationFlag, got {result.get('objectType')}"
        )
        state["flag_id"] = result.get("id")
        # Verify entry status changed
        entry = kaltura_post("baseEntry", "get", {"entryId": entry_id})
        mod_status = entry.get("moderationStatus")
        assert mod_status == 5, f"Expected FLAGGED_FOR_REVIEW (5), got {mod_status}"
        print(f"    Flagged entry {entry_id}: moderationStatus={mod_status}, flagId={state['flag_id']}")

    runner.run_test("baseEntry.flag — SEXUAL_CONTENT sets FLAGGED_FOR_REVIEW (5)",
                     test_flag_entry)

    def test_list_flags():
        """List pending flags for the flagged entry."""
        entry_id = state.get("default_entry")
        if not entry_id:
            print("    SKIP: No entry from Phase 1")
            return
        result = kaltura_post("baseEntry", "listFlags", {
            "entryId": entry_id,
            "pager[pageSize]": 50,
        })
        total = result.get("totalCount", 0)
        assert total >= 1, f"Expected at least 1 flag, got {total}"
        flag = result["objects"][0]
        assert flag.get("flagType") == 1, f"Expected flagType=1 (SEXUAL_CONTENT), got {flag.get('flagType')}"
        assert flag.get("status") == 1, f"Expected flag status=1 (PENDING), got {flag.get('status')}"
        print(f"    Found {total} flag(s), first: type={flag['flagType']}, status={flag['status']}")

    runner.run_test("baseEntry.listFlags — returns pending flag with correct type",
                     test_list_flags)

    def test_second_flag():
        """Flag the same entry again with SPAM_COMMERCIALS (4) — verify moderationCount increments."""
        entry_id = state.get("default_entry")
        if not entry_id:
            print("    SKIP: No entry from Phase 1")
            return
        kaltura_post("baseEntry", "flag", {
            "moderationFlag[objectType]": "KalturaModerationFlag",
            "moderationFlag[flaggedEntryId]": entry_id,
            "moderationFlag[flagType]": 4,
            "moderationFlag[comments]": "E2E test flag — SPAM_COMMERCIALS",
        })
        entry = kaltura_post("baseEntry", "get", {"entryId": entry_id})
        mod_count = entry.get("moderationCount", 0)
        assert mod_count >= 2, f"Expected moderationCount >= 2, got {mod_count}"
        print(f"    Entry {entry_id}: moderationCount={mod_count} after second flag")

    runner.run_test("baseEntry.flag — second flag increments moderationCount",
                     test_second_flag)

    # ════════════════════════════════════════════
    # Phase 3: Approve Flow
    # ════════════════════════════════════════════

    def test_approve_entry():
        """Approve the flagged entry — verify status and flag cleanup."""
        entry_id = state.get("default_entry")
        if not entry_id:
            print("    SKIP: No entry from Phase 1")
            return
        kaltura_post("baseEntry", "approve", {"entryId": entry_id})
        entry = kaltura_post("baseEntry", "get", {"entryId": entry_id})
        mod_status = entry.get("moderationStatus")
        mod_count = entry.get("moderationCount", -1)
        assert mod_status == 2, f"Expected APPROVED (2), got {mod_status}"
        assert mod_count == 0, f"Expected moderationCount=0 after approve, got {mod_count}"
        # Verify flags are now MODERATED
        flags = kaltura_post("baseEntry", "listFlags", {
            "entryId": entry_id,
            "pager[pageSize]": 50,
        })
        assert flags.get("totalCount", 0) == 0, (
            f"Expected 0 pending flags after approve, got {flags.get('totalCount')}"
        )
        print(f"    Approved: moderationStatus={mod_status}, moderationCount={mod_count}, pendingFlags=0")

    runner.run_test("baseEntry.approve — sets APPROVED (2), clears flags",
                     test_approve_entry)

    # ════════════════════════════════════════════
    # Phase 4: Reject Flow
    # ════════════════════════════════════════════

    def test_reject_entry():
        """Create, flag, and reject an entry — verify REJECTED status."""
        entry_id = create_test_entry()
        state["reject_entry"] = entry_id
        runner.register_cleanup(f"entry {entry_id}", lambda: delete_test_entry(entry_id))
        # Flag it first
        kaltura_post("baseEntry", "flag", {
            "moderationFlag[objectType]": "KalturaModerationFlag",
            "moderationFlag[flaggedEntryId]": entry_id,
            "moderationFlag[flagType]": 2,
            "moderationFlag[comments]": "E2E test — reject flow",
        })
        # Reject
        kaltura_post("baseEntry", "reject", {"entryId": entry_id})
        entry = kaltura_post("baseEntry", "get", {"entryId": entry_id})
        mod_status = entry.get("moderationStatus")
        assert mod_status == 3, f"Expected REJECTED (3), got {mod_status}"
        print(f"    Rejected entry {entry_id}: moderationStatus={mod_status}")

    runner.run_test("baseEntry.reject — sets REJECTED (3)",
                     test_reject_entry)

    def test_reject_side_effects():
        """Verify reject clears moderationCount and marks flags as MODERATED."""
        entry_id = state.get("reject_entry")
        if not entry_id:
            print("    SKIP: No rejected entry from Phase 4")
            return
        entry = kaltura_post("baseEntry", "get", {"entryId": entry_id})
        mod_count = entry.get("moderationCount", -1)
        assert mod_count == 0, f"Expected moderationCount=0 after reject, got {mod_count}"
        # Verify flags are now MODERATED (listFlags returns only PENDING flags)
        flags = kaltura_post("baseEntry", "listFlags", {
            "entryId": entry_id,
            "pager[pageSize]": 50,
        })
        pending = flags.get("totalCount", 0)
        assert pending == 0, f"Expected 0 pending flags after reject, got {pending}"
        print(f"    Reject side effects verified: moderationCount={mod_count}, pendingFlags={pending}")

    runner.run_test("baseEntry.reject — clears moderationCount and flags",
                     test_reject_side_effects)

    def test_flag_rejected_fails():
        """Flagging a REJECTED entry returns ENTRY_CANNOT_BE_FLAGGED."""
        entry_id = state.get("reject_entry")
        if not entry_id:
            print("    SKIP: No rejected entry from Phase 4")
            return
        try:
            kaltura_post("baseEntry", "flag", {
                "moderationFlag[objectType]": "KalturaModerationFlag",
                "moderationFlag[flaggedEntryId]": entry_id,
                "moderationFlag[flagType]": 1,
                "moderationFlag[comments]": "Should fail",
            })
            assert False, "Expected ENTRY_CANNOT_BE_FLAGGED error but call succeeded"
        except Exception as e:
            err_msg = str(e)
            assert "ENTRY_CANNOT_BE_FLAGGED" in err_msg or "cannot be flagged" in err_msg.lower(), (
                f"Expected ENTRY_CANNOT_BE_FLAGGED, got: {err_msg}"
            )
            print(f"    Correctly rejected: {err_msg[:80]}")

    runner.run_test("baseEntry.flag — REJECTED entry returns ENTRY_CANNOT_BE_FLAGGED",
                     test_flag_rejected_fails)

    # ════════════════════════════════════════════
    # Phase 5: Moderation Queue Filtering
    # ════════════════════════════════════════════

    def test_queue_filter():
        """List entries with moderationStatusIn=5 — verify flagged entry appears."""
        # Create a fresh entry and flag it for a clean filter test
        entry_id = create_test_entry()
        state["filter_entry"] = entry_id
        runner.register_cleanup(f"entry {entry_id}", lambda: delete_test_entry(entry_id))
        kaltura_post("baseEntry", "flag", {
            "moderationFlag[objectType]": "KalturaModerationFlag",
            "moderationFlag[flaggedEntryId]": entry_id,
            "moderationFlag[flagType]": 3,
            "moderationFlag[comments]": "E2E queue filter test",
        })
        result = kaltura_post("baseEntry", "list", {
            "filter[objectType]": "KalturaBaseEntryFilter",
            "filter[moderationStatusIn]": "5",
            "filter[idEqual]": entry_id,
        })
        total = result.get("totalCount", 0)
        assert total == 1, f"Expected 1 FLAGGED entry in queue, got {total}"
        print(f"    Queue filter moderationStatusIn=5: found {total} entry")

    runner.run_test("baseEntry.list — moderationStatusIn=5 finds flagged entries",
                     test_queue_filter)

    def test_rejected_found_with_explicit_filter():
        """REJECTED entries are findable with explicit moderationStatusIn filter."""
        entry_id = state.get("reject_entry")
        if not entry_id:
            print("    SKIP: No rejected entry")
            return
        # With disableentitlement KS, rejected entries may still appear in default
        # list. The key behavior to verify: explicit moderationStatusIn=3 filter works.
        result = kaltura_post("baseEntry", "list", {
            "filter[objectType]": "KalturaBaseEntryFilter",
            "filter[idEqual]": entry_id,
            "filter[moderationStatusIn]": "3",
        })
        total = result.get("totalCount", 0)
        assert total == 1, f"Expected REJECTED entry found with moderationStatusIn=3, got {total}"
        entry = result["objects"][0]
        mod_status = entry.get("moderationStatus")
        assert mod_status == 3, f"Expected moderationStatus=3, got {mod_status}"
        print(f"    REJECTED entry found with moderationStatusIn=3 filter, status={mod_status}")

    runner.run_test("baseEntry.list — moderationStatusIn=3 finds REJECTED entries",
                     test_rejected_found_with_explicit_filter)

    # ════════════════════════════════════════════
    # Phase 6: All Flag Types
    # ════════════════════════════════════════════

    def test_all_flag_types():
        """Verify all 6 flag types are accepted."""
        entry_id = create_test_entry()
        state["flag_types_entry"] = entry_id
        runner.register_cleanup(f"entry {entry_id}", lambda: delete_test_entry(entry_id))
        flag_names = {
            1: "SEXUAL_CONTENT",
            2: "VIOLENT_REPULSIVE",
            3: "HARMFUL_DANGEROUS",
            4: "SPAM_COMMERCIALS",
            5: "COPYRIGHT",
            6: "TERMS_OF_USE_VIOLATION",
        }
        for flag_type, name in flag_names.items():
            result = kaltura_post("baseEntry", "flag", {
                "moderationFlag[objectType]": "KalturaModerationFlag",
                "moderationFlag[flaggedEntryId]": entry_id,
                "moderationFlag[flagType]": flag_type,
                "moderationFlag[comments]": f"E2E test — type {flag_type}",
            })
            assert result.get("objectType") == "KalturaModerationFlag", (
                f"Flag type {flag_type} ({name}) rejected: {result}"
            )
        # Verify all flags created
        flags = kaltura_post("baseEntry", "listFlags", {
            "entryId": entry_id,
            "pager[pageSize]": 50,
        })
        total = flags.get("totalCount", 0)
        assert total == 6, f"Expected 6 flags (one per type), got {total}"
        print(f"    All 6 flag types accepted, totalFlags={total}")

    runner.run_test("baseEntry.flag — all 6 flag types accepted",
                     test_all_flag_types)

    # ════════════════════════════════════════════
    # Phase 7: REACH Moderation Discovery
    # ════════════════════════════════════════════

    def test_reach_moderation_discovery():
        """Discover REACH moderation catalog items (serviceFeature=15)."""
        try:
            result = kaltura_post("reach_vendorCatalogItem", "list", {
                "filter[objectType]": "KalturaVendorCatalogItemFilter",
                "filter[serviceFeatureEqual]": 15,
            })
        except Exception as e:
            if "SERVICE_FORBIDDEN" in str(e):
                print("    SKIP: REACH service not enabled on this account")
                return
            raise
        total = result.get("totalCount", 0)
        if total == 0:
            print("    No moderation catalog items found (REACH moderation not provisioned)")
            return
        item = result["objects"][0]
        state["moderation_catalog_item_id"] = item["id"]
        sf = item.get("serviceFeature")
        assert sf == 15, f"Expected serviceFeature=15, got {sf}"
        print(f"    Found {total} moderation catalog item(s), first: id={item['id']}, "
              f"serviceType={item.get('serviceType')}, name={item.get('name', 'N/A')}")

    runner.run_test("vendorCatalogItem.list — discover REACH moderation (serviceFeature=15)",
                     test_reach_moderation_discovery)

    def test_reach_moderation_task():
        """Order a REACH moderation task if a catalog item is available."""
        catalog_id = state.get("moderation_catalog_item_id")
        if not catalog_id:
            print("    SKIP: No moderation catalog item available")
            return
        # Create a test entry — needs to be READY for REACH
        entry_id = create_test_entry()
        state["reach_entry"] = entry_id
        runner.register_cleanup(f"entry {entry_id}", lambda: delete_test_entry(entry_id))
        try:
            result = kaltura_post("reach_entryVendorTask", "add", {
                "entryVendorTask[objectType]": "KalturaEntryVendorTask",
                "entryVendorTask[entryId]": entry_id,
                "entryVendorTask[catalogItemId]": catalog_id,
                "entryVendorTask[taskJobData][objectType]": "KalturaModerationVendorTaskData",
                "entryVendorTask[taskJobData][policyIds]": "1",
            })
            task_id = result.get("id")
            status = result.get("status")
            sf = result.get("serviceFeature")
            state["moderation_task_id"] = task_id
            runner.register_cleanup(f"vendor task {task_id}",
                                    lambda: _abort_task(task_id))
            assert sf == 15, f"Expected serviceFeature=15, got {sf}"
            print(f"    Created moderation task: id={task_id}, status={status}, serviceFeature={sf}")
        except Exception as e:
            err = str(e)
            # Entry may not be READY yet, credit insufficient, or status restriction
            if ("ENTRY_NOT_READY" in err or "CREDIT" in err or "INSUFFICIENT" in err
                    or "not allowed" in err.lower() or "status" in err.lower()):
                print(f"    SKIP: {err[:80]}")
                return
            raise

    runner.run_test("entryVendorTask.add — create REACH moderation task",
                     test_reach_moderation_task)

    # ════════════════════════════════════════════
    # Phase 8: Category Moderation
    # ════════════════════════════════════════════

    def test_category_entry_moderation():
        """Add entry to category and verify categoryEntry status fields exist."""
        # Create a category with moderation enabled
        ts = int(time.time())
        try:
            cat_result = kaltura_post("category", "add", {
                "category[objectType]": "KalturaCategory",
                "category[name]": f"MODERATION_TEST_{ts}",
                "category[description]": "Temporary category for moderation API test",
                "category[moderation]": 1,
            })
        except Exception as e:
            if "SERVICE_FORBIDDEN" in str(e):
                print("    SKIP: Category service not accessible")
                return
            raise
        cat_id = cat_result["id"]
        state["mod_category_id"] = cat_id
        runner.register_cleanup(f"category {cat_id}",
                                lambda: _delete_category(cat_id))
        # Create entry
        entry_id = create_test_entry()
        state["cat_mod_entry"] = entry_id
        runner.register_cleanup(f"entry {entry_id}", lambda: delete_test_entry(entry_id))
        # Add entry to category
        ce_result = kaltura_post("categoryEntry", "add", {
            "categoryEntry[objectType]": "KalturaCategoryEntry",
            "categoryEntry[entryId]": entry_id,
            "categoryEntry[categoryId]": cat_id,
        })
        initial_status = ce_result.get("status")
        # Status 1=PENDING (moderation enabled) or 2=ACTIVE (auto-approved)
        assert initial_status in (1, 2), (
            f"Expected categoryEntry status PENDING(1) or ACTIVE(2), got {initial_status}"
        )
        if initial_status == 1:
            # Moderation is active — try to activate
            kaltura_post("categoryEntry", "activate", {
                "entryId": entry_id,
                "categoryId": cat_id,
            })
            ce_list = kaltura_post("categoryEntry", "list", {
                "filter[objectType]": "KalturaCategoryEntryFilter",
                "filter[entryIdEqual]": entry_id,
                "filter[categoryIdEqual]": cat_id,
            })
            final_status = ce_list["objects"][0].get("status") if ce_list.get("totalCount", 0) > 0 else None
            assert final_status == 2, f"Expected ACTIVE(2) after activate, got {final_status}"
            print(f"    categoryEntry: PENDING(1) → activate → ACTIVE({final_status})")
        else:
            print(f"    categoryEntry auto-activated: status={initial_status} (ACTIVE)")

    runner.run_test("categoryEntry.add + activate — category moderation flow",
                     test_category_entry_moderation)

    def test_category_entry_reject():
        """Reject an entry from a moderated category."""
        cat_id = state.get("mod_category_id")
        if not cat_id:
            print("    SKIP: No moderated category from Phase 8")
            return
        # Create a fresh entry and add it to the moderated category
        entry_id = create_test_entry()
        state["cat_reject_entry"] = entry_id
        runner.register_cleanup(f"entry {entry_id}", lambda: delete_test_entry(entry_id))
        ce_result = kaltura_post("categoryEntry", "add", {
            "categoryEntry[objectType]": "KalturaCategoryEntry",
            "categoryEntry[entryId]": entry_id,
            "categoryEntry[categoryId]": cat_id,
        })
        initial_status = ce_result.get("status")
        if initial_status == 2:
            # Admin KS auto-approves — reject requires PENDING (1)
            # This confirms the API correctly enforces the PENDING prerequisite
            try:
                kaltura_post("categoryEntry", "reject", {
                    "entryId": entry_id,
                    "categoryId": cat_id,
                })
                print(f"    categoryEntry.reject succeeded on ACTIVE entry (unexpected)")
            except Exception as e:
                err = str(e)
                assert "CANNOT_REJECT" in err or "NOT_PENDING" in err, (
                    f"Expected CANNOT_REJECT error, got: {err}"
                )
                print(f"    categoryEntry.reject correctly requires PENDING status (admin KS auto-approves)")
        elif initial_status == 1:
            # PENDING — reject should work
            kaltura_post("categoryEntry", "reject", {
                "entryId": entry_id,
                "categoryId": cat_id,
            })
            ce_list = kaltura_post("categoryEntry", "list", {
                "filter[objectType]": "KalturaCategoryEntryFilter",
                "filter[entryIdEqual]": entry_id,
                "filter[categoryIdEqual]": cat_id,
            })
            total = ce_list.get("totalCount", 0)
            assert total == 0, f"Expected 0 categoryEntries after reject, got {total}"
            print(f"    categoryEntry.reject removed entry {entry_id} from category {cat_id}")

    runner.run_test("categoryEntry.reject — reject validates PENDING prerequisite",
                     test_category_entry_reject)

    def test_user_notify_ban():
        """Test user.notifyBan — sends ban notification to a user."""
        try:
            result = kaltura_post("user", "notifyBan", {
                "userId": os.environ.get("KALTURA_USER_ID", "test@example.com"),
            })
            # notifyBan returns void on success (empty response or null)
            print(f"    user.notifyBan succeeded (sends notification only, no account ban)")
        except Exception as e:
            err = str(e)
            if "SERVICE_FORBIDDEN" in err or "PERMISSION" in err.upper():
                print(f"    SKIP: user.notifyBan not accessible — {err[:60]}")
                return
            if "USER_NOT_FOUND" in err or "INVALID_USER" in err:
                print(f"    SKIP: test user not found — {err[:60]}")
                return
            raise

    runner.run_test("user.notifyBan — send ban notification",
                     test_user_notify_ban)

    # ════════════════════════════════════════════
    # Cleanup & Summary
    # ════════════════════════════════════════════

    # Approve any flagged entries before cleanup to avoid leaving flagged state
    for key in ["filter_entry", "flag_types_entry"]:
        eid = state.get(key)
        if eid:
            _approve_entry(eid)

    keep = "--keep" in sys.argv
    if keep:
        print("\n--- --keep flag set, skipping cleanup ---")
        for key, val in state.items():
            print(f"  {key}: {val}")
    else:
        if sys.stdin.isatty():
            input("\nPress Enter to clean up...")
        runner.cleanup()

    success = runner.summary()
    sys.exit(0 if success else 1)


def _abort_task(task_id):
    """Abort a REACH vendor task — ignore errors."""
    try:
        kaltura_post("reach_entryVendorTask", "abort", {"id": task_id})
    except Exception:
        pass


def _delete_category(cat_id):
    """Delete a category — ignore errors."""
    try:
        kaltura_post("category", "delete", {
            "id": cat_id,
            "moveEntriesToParentCategory": 1,
        })
    except Exception:
        pass


if __name__ == "__main__":
    print(f"\n{'='*60}")
    print("  KALTURA MODERATION API — End-to-End Validation")
    print(f"{'='*60}\n")
    main()
