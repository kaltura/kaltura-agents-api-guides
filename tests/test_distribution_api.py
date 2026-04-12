#!/usr/bin/env python3
"""End-to-end validation of the Content Distribution API.
Covers: distributionProvider.list, distributionProfile CRUD,
entryDistribution lifecycle (add, validate, get, list, update, submitAdd, serveSentData,
serveReturnedData, delete), error handling."""

import sys
import os
import time
import requests

sys.path.insert(0, os.path.dirname(__file__))
from test_helpers import kaltura_post, create_test_entry, delete_test_entry, TestRunner, PARTNER_ID, KS, SERVICE_URL

state = {}

EXISTING_YOUTUBE_PROFILE_ID = 413741  # Pre-configured YouTube API profile on test account


def main():
    runner = TestRunner("Content Distribution API — E2E Validation")

    # ════════════════════════════════════════════
    # Phase 1: Distribution Provider Discovery
    # ════════════════════════════════════════════

    def test_provider_list():
        """List available distribution provider types."""
        result = kaltura_post("contentDistribution_distributionProvider", "list", {})
        assert "objects" in result, f"Expected objects in response: {result}"
        assert "totalCount" in result, f"Expected totalCount in response: {result}"
        assert result["totalCount"] > 0, f"Expected at least 1 provider, got {result['totalCount']}"
        state["provider_count"] = result["totalCount"]
        print(f"    Providers available: {result['totalCount']}")

    runner.run_test("distributionProvider.list — available providers", test_provider_list)

    def test_provider_types():
        """Verify expected provider types exist (generic, syndication, YouTube API)."""
        result = kaltura_post("contentDistribution_distributionProvider", "list", {})
        objects = result.get("objects", [])
        types_found = set()
        for obj in objects:
            ptype = obj.get("type")
            if ptype:
                types_found.add(str(ptype))
        assert "1" in types_found, f"Generic provider (type=1) not found in {types_found}"
        assert "2" in types_found, f"Syndication provider (type=2) not found in {types_found}"
        assert "youtubeApiDistribution.YOUTUBE_API" in types_found, \
            f"YouTube API provider not found in {types_found}"
        print(f"    Found generic, syndication, YouTube API providers")

    runner.run_test("distributionProvider.list — verify key provider types", test_provider_types)

    # ════════════════════════════════════════════
    # Phase 2: Distribution Profile Management
    # ════════════════════════════════════════════

    def test_profile_list():
        """List distribution profiles on the account."""
        result = kaltura_post("contentDistribution_distributionProfile", "list", {})
        assert "objects" in result, f"Expected objects: {result}"
        assert "totalCount" in result, f"Expected totalCount: {result}"
        state["profile_count"] = result["totalCount"]
        print(f"    Profiles: {result['totalCount']}")

    runner.run_test("distributionProfile.list — list profiles", test_profile_list)

    def test_profile_get():
        """Retrieve the YouTube distribution profile by ID."""
        result = kaltura_post("contentDistribution_distributionProfile", "get", {
            "id": EXISTING_YOUTUBE_PROFILE_ID,
        })
        assert result.get("id") == EXISTING_YOUTUBE_PROFILE_ID, \
            f"Expected id={EXISTING_YOUTUBE_PROFILE_ID}, got {result.get('id')}"
        assert "providerType" in result, f"Expected providerType in response: {result}"
        assert "name" in result, f"Expected name in response: {result}"
        assert "status" in result, f"Expected status in response: {result}"
        state["profile_name"] = result["name"]
        state["profile_provider"] = result["providerType"]
        state["profile_status"] = result["status"]
        print(f"    Profile: {result['name']}, provider={result['providerType']}, status={result['status']}")

    runner.run_test("distributionProfile.get — YouTube profile details", test_profile_get)

    def test_profile_list_filter_status():
        """List distribution profiles filtered by status."""
        result = kaltura_post("contentDistribution_distributionProfile", "list", {
            "filter[objectType]": "KalturaDistributionProfileFilter",
            "filter[statusEqual]": 2,
        })
        assert "objects" in result, f"Expected objects: {result}"
        for obj in result.get("objects", []):
            assert obj.get("status") == 2, f"Expected status=2, got {obj.get('status')}"
        print(f"    Enabled profiles: {result['totalCount']}")

    runner.run_test("distributionProfile.list — filter by status=ENABLED", test_profile_list_filter_status)

    def test_profile_get_fields():
        """Verify YouTube profile returns provider-specific fields."""
        result = kaltura_post("contentDistribution_distributionProfile", "get", {
            "id": EXISTING_YOUTUBE_PROFILE_ID,
        })
        assert result.get("objectType") == "KalturaYoutubeApiDistributionProfile", \
            f"Expected KalturaYoutubeApiDistributionProfile, got {result.get('objectType')}"
        assert "defaultCategory" in result, f"Expected defaultCategory: {list(result.keys())}"
        assert "allowComments" in result, f"Expected allowComments: {list(result.keys())}"
        assert "allowEmbedding" in result, f"Expected allowEmbedding: {list(result.keys())}"
        assert "submitEnabled" in result, f"Expected submitEnabled: {list(result.keys())}"
        assert "distributeTrigger" in result, f"Expected distributeTrigger: {list(result.keys())}"
        print(f"    YouTube fields: category={result.get('defaultCategory')}, "
              f"comments={result.get('allowComments')}, embed={result.get('allowEmbedding')}")

    runner.run_test("distributionProfile.get — YouTube-specific fields", test_profile_get_fields)

    # ════════════════════════════════════════════
    # Phase 3: Entry Distribution Lifecycle
    # ════════════════════════════════════════════

    def test_create_test_entry():
        """Create a test media entry for distribution testing."""
        entry_id = create_test_entry()
        state["test_entry_id"] = entry_id
        runner.register_cleanup(f"test entry {entry_id}",
                                lambda: delete_test_entry(entry_id))
        print(f"    Entry: {entry_id}")

    runner.run_test("media.add — create test entry", test_create_test_entry)

    def test_entry_distribution_add():
        """Bind test entry to YouTube distribution profile."""
        result = kaltura_post("contentDistribution_entryDistribution", "add", {
            "entryDistribution[objectType]": "KalturaEntryDistribution",
            "entryDistribution[entryId]": state["test_entry_id"],
            "entryDistribution[distributionProfileId]": EXISTING_YOUTUBE_PROFILE_ID,
        })
        assert "id" in result, f"Expected id in response: {result}"
        assert result.get("entryId") == state["test_entry_id"], \
            f"Expected entryId={state['test_entry_id']}, got {result.get('entryId')}"
        assert result.get("status") == 0, f"Expected PENDING status=0, got {result.get('status')}"
        state["entry_dist_id"] = result["id"]
        runner.register_cleanup(f"entry distribution {result['id']}",
                                lambda: _delete_entry_distribution(result["id"]))
        print(f"    EntryDistribution: id={result['id']}, status={result['status']} (PENDING)")

    runner.run_test("entryDistribution.add — bind entry to profile", test_entry_distribution_add)

    def test_entry_distribution_validate():
        """Validate entry against distribution profile requirements."""
        result = kaltura_post("contentDistribution_entryDistribution", "validate", {
            "id": state["entry_dist_id"],
        })
        assert "validationErrors" in result, f"Expected validationErrors: {result}"
        errors = result["validationErrors"]
        has_flavor_error = any(
            e.get("objectType") == "KalturaDistributionValidationErrorMissingFlavor"
            for e in errors
        )
        assert has_flavor_error, f"Expected missing flavor error, got: {errors}"
        state["validation_error_count"] = len(errors)
        print(f"    Validation errors: {len(errors)} (missing flavor expected for empty entry)")

    runner.run_test("entryDistribution.validate — check requirements", test_entry_distribution_validate)

    def test_entry_distribution_get():
        """Retrieve entry distribution by ID."""
        result = kaltura_post("contentDistribution_entryDistribution", "get", {
            "id": state["entry_dist_id"],
        })
        assert result.get("id") == state["entry_dist_id"], \
            f"Expected id={state['entry_dist_id']}, got {result.get('id')}"
        assert "entryId" in result, f"Expected entryId: {result}"
        assert "distributionProfileId" in result, f"Expected distributionProfileId: {result}"
        assert "status" in result, f"Expected status: {result}"
        print(f"    Got: id={result['id']}, entry={result['entryId']}, status={result['status']}")

    runner.run_test("entryDistribution.get — retrieve by ID", test_entry_distribution_get)

    def test_entry_distribution_list_by_entry():
        """List entry distributions filtered by entry ID."""
        result = kaltura_post("contentDistribution_entryDistribution", "list", {
            "filter[objectType]": "KalturaEntryDistributionFilter",
            "filter[entryIdEqual]": state["test_entry_id"],
        })
        assert result.get("totalCount", 0) >= 1, \
            f"Expected at least 1 distribution for entry, got {result.get('totalCount')}"
        found = any(obj.get("id") == state["entry_dist_id"] for obj in result.get("objects", []))
        assert found, f"Expected entry_dist_id={state['entry_dist_id']} in results"
        print(f"    Found {result['totalCount']} distributions for entry {state['test_entry_id']}")

    runner.run_test("entryDistribution.list — filter by entryId", test_entry_distribution_list_by_entry)

    def test_entry_distribution_list_by_profile():
        """List entry distributions filtered by distribution profile ID."""
        result = kaltura_post("contentDistribution_entryDistribution", "list", {
            "filter[objectType]": "KalturaEntryDistributionFilter",
            "filter[distributionProfileIdEqual]": EXISTING_YOUTUBE_PROFILE_ID,
        })
        assert result.get("totalCount", 0) >= 1, \
            f"Expected at least 1 distribution for profile, got {result.get('totalCount')}"
        print(f"    Found {result['totalCount']} distributions for profile {EXISTING_YOUTUBE_PROFILE_ID}")

    runner.run_test("entryDistribution.list — filter by profileId", test_entry_distribution_list_by_profile)

    def test_entry_distribution_list_by_status():
        """List entry distributions filtered by status."""
        result = kaltura_post("contentDistribution_entryDistribution", "list", {
            "filter[objectType]": "KalturaEntryDistributionFilter",
            "filter[statusEqual]": 0,
        })
        assert "totalCount" in result, f"Expected totalCount: {result}"
        assert result["totalCount"] >= 1, \
            f"Expected at least 1 PENDING distribution, got {result['totalCount']}"
        print(f"    PENDING distributions: {result['totalCount']}")

    runner.run_test("entryDistribution.list — filter by status=PENDING", test_entry_distribution_list_by_status)

    def test_entry_distribution_update():
        """Update entry distribution sunrise/sunset timestamps."""
        future_sunrise = int(time.time()) + 86400
        future_sunset = int(time.time()) + 172800
        result = kaltura_post("contentDistribution_entryDistribution", "update", {
            "id": state["entry_dist_id"],
            "entryDistribution[objectType]": "KalturaEntryDistribution",
            "entryDistribution[sunrise]": future_sunrise,
            "entryDistribution[sunset]": future_sunset,
        })
        assert result.get("sunrise") == future_sunrise, \
            f"Expected sunrise={future_sunrise}, got {result.get('sunrise')}"
        assert result.get("sunset") == future_sunset, \
            f"Expected sunset={future_sunset}, got {result.get('sunset')}"
        print(f"    Updated: sunrise={result['sunrise']}, sunset={result['sunset']}")

    runner.run_test("entryDistribution.update — set sunrise/sunset", test_entry_distribution_update)

    def test_entry_distribution_submit_add():
        """Submit entry distribution to remote platform (queues for processing)."""
        result = kaltura_post("contentDistribution_entryDistribution", "submitAdd", {
            "id": state["entry_dist_id"],
            "submitWhenReady": "true",
        })
        assert result.get("id") == state["entry_dist_id"], \
            f"Expected id={state['entry_dist_id']}, got {result.get('id')}"
        assert result.get("status") in [1, 4], \
            f"Expected status QUEUED(1) or SUBMITTING(4), got {result.get('status')}"
        state["post_submit_status"] = result["status"]
        print(f"    Submitted: status={result['status']} ({'QUEUED' if result['status'] == 1 else 'SUBMITTING'})")

    runner.run_test("entryDistribution.submitAdd — submit to remote", test_entry_distribution_submit_add)

    # ════════════════════════════════════════════
    # Phase 4: Distribution Debugging
    # ════════════════════════════════════════════

    def test_serve_sent_data():
        """Retrieve raw XML sent to remote platform (empty for pending)."""
        url = f"{SERVICE_URL}/service/contentDistribution_entryDistribution/action/serveSentData"
        resp = requests.post(url, data={
            "ks": KS, "format": 1,
            "id": state["entry_dist_id"],
            "actionType": 1,
        }, timeout=30)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        print(f"    serveSentData: status={resp.status_code}, body_len={len(resp.content)}")

    runner.run_test("entryDistribution.serveSentData — debug XML (SUBMIT)", test_serve_sent_data)

    def test_serve_returned_data():
        """Retrieve raw XML returned from remote platform (empty for pending)."""
        url = f"{SERVICE_URL}/service/contentDistribution_entryDistribution/action/serveReturnedData"
        resp = requests.post(url, data={
            "ks": KS, "format": 1,
            "id": state["entry_dist_id"],
            "actionType": 1,
        }, timeout=30)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        print(f"    serveReturnedData: status={resp.status_code}, body_len={len(resp.content)}")

    runner.run_test("entryDistribution.serveReturnedData — debug XML (SUBMIT)", test_serve_returned_data)

    # ════════════════════════════════════════════
    # Phase 5: Existing Distribution Inspection
    # ════════════════════════════════════════════

    def test_list_all_distributions():
        """List all entry distributions on the account."""
        result = kaltura_post("contentDistribution_entryDistribution", "list", {})
        assert "totalCount" in result, f"Expected totalCount: {result}"
        assert result["totalCount"] >= 1, f"Expected at least 1 distribution, got {result['totalCount']}"
        state["total_distributions"] = result["totalCount"]
        for obj in result.get("objects", [])[:5]:
            status_name = {0: "PENDING", 1: "QUEUED", 2: "READY", 3: "DELETED",
                           7: "ERROR_SUBMITTING"}.get(obj.get("status"), str(obj.get("status")))
            remote = f", remoteId={obj['remoteId']}" if obj.get("remoteId") else ""
            print(f"    id={obj['id']}, entry={obj['entryId']}, status={status_name}{remote}")

    runner.run_test("entryDistribution.list — all distributions", test_list_all_distributions)

    def test_ready_distribution():
        """Verify a READY distribution has a remoteId (external platform ID)."""
        result = kaltura_post("contentDistribution_entryDistribution", "list", {
            "filter[objectType]": "KalturaEntryDistributionFilter",
            "filter[statusEqual]": 2,
        })
        ready_dists = result.get("objects", [])
        if not ready_dists:
            print("    No READY distributions on account — skipping remoteId check")
            return
        dist = ready_dists[0]
        assert dist.get("remoteId"), f"Expected remoteId on READY distribution: {dist}"
        state["ready_dist_id"] = dist["id"]
        print(f"    READY: id={dist['id']}, remoteId={dist['remoteId']}")

    runner.run_test("entryDistribution.list — READY distribution has remoteId", test_ready_distribution)

    # ════════════════════════════════════════════
    # Phase 6: Error Handling
    # ════════════════════════════════════════════

    def test_entry_dist_not_found():
        """Verify error for non-existent entry distribution ID."""
        try:
            kaltura_post("contentDistribution_entryDistribution", "get", {"id": 999999999})
            assert False, "Expected error for non-existent ID"
        except Exception as e:
            assert "ENTRY_DISTRIBUTION_NOT_FOUND" in str(e), f"Expected ENTRY_DISTRIBUTION_NOT_FOUND: {e}"
            print(f"    Correct error: {e}")

    runner.run_test("entryDistribution.get — NOT_FOUND error", test_entry_dist_not_found)

    def test_retry_not_found():
        """Verify error for retrySubmit on non-existent entry distribution."""
        try:
            kaltura_post("contentDistribution_entryDistribution", "retrySubmit", {"id": 999999999})
            assert False, "Expected error for non-existent ID"
        except Exception as e:
            assert "ENTRY_DISTRIBUTION_NOT_FOUND" in str(e), f"Expected ENTRY_DISTRIBUTION_NOT_FOUND: {e}"
            print(f"    Correct error: {e}")

    runner.run_test("entryDistribution.retrySubmit — NOT_FOUND error", test_retry_not_found)

    def test_profile_not_found():
        """Verify error for non-existent distribution profile ID."""
        try:
            kaltura_post("contentDistribution_distributionProfile", "get", {"id": 999999999})
            assert False, "Expected error for non-existent ID"
        except Exception as e:
            assert "NOT_FOUND" in str(e) or "not found" in str(e).lower(), \
                f"Expected NOT_FOUND error: {e}"
            print(f"    Correct error: {e}")

    runner.run_test("distributionProfile.get — NOT_FOUND error", test_profile_not_found)

    def test_entry_dist_invalid_entry():
        """Verify error for binding non-existent entry to distribution."""
        try:
            kaltura_post("contentDistribution_entryDistribution", "add", {
                "entryDistribution[objectType]": "KalturaEntryDistribution",
                "entryDistribution[entryId]": "0_nonexistent",
                "entryDistribution[distributionProfileId]": EXISTING_YOUTUBE_PROFILE_ID,
            })
            assert False, "Expected error for non-existent entry"
        except Exception as e:
            assert "ENTRY_NOT_FOUND" in str(e) or "not found" in str(e).lower(), \
                f"Expected ENTRY_NOT_FOUND error: {e}"
            print(f"    Correct error: {e}")

    runner.run_test("entryDistribution.add — ENTRY_NOT_FOUND error", test_entry_dist_invalid_entry)

    # ════════════════════════════════════════════
    # Phase 7: Entry Distribution Delete Verification
    # ════════════════════════════════════════════

    def test_entry_dist_delete_and_verify():
        """Delete an entry distribution and verify it is removed."""
        entry_id = create_test_entry()
        runner.register_cleanup(f"delete-test entry {entry_id}",
                                lambda: delete_test_entry(entry_id))
        result = kaltura_post("contentDistribution_entryDistribution", "add", {
            "entryDistribution[objectType]": "KalturaEntryDistribution",
            "entryDistribution[entryId]": entry_id,
            "entryDistribution[distributionProfileId]": EXISTING_YOUTUBE_PROFILE_ID,
        })
        dist_id = result["id"]
        print(f"    Created entry distribution to delete: {dist_id}")

        kaltura_post("contentDistribution_entryDistribution", "delete", {"id": dist_id})
        print(f"    Deleted entry distribution: {dist_id}")

        # Hard delete — returns NOT_FOUND
        try:
            kaltura_post("contentDistribution_entryDistribution", "get", {"id": dist_id})
            assert False, "Expected NOT_FOUND error after delete"
        except Exception as e:
            assert "ENTRY_DISTRIBUTION_NOT_FOUND" in str(e), \
                f"Expected ENTRY_DISTRIBUTION_NOT_FOUND: {e}"
            print(f"    Verified deleted: {e}")

    runner.run_test("entryDistribution.delete — delete and verify", test_entry_dist_delete_and_verify)

    # ════════════════════════════════════════════
    # Cleanup & Summary
    # ════════════════════════════════════════════
    keep = "--keep" in sys.argv
    if keep:
        print("\n--- Keeping resources (--keep flag) ---")
        if state.get("test_entry_id"):
            print(f"  Test entry: {state['test_entry_id']}")
        if state.get("entry_dist_id"):
            print(f"  Entry distribution: {state['entry_dist_id']}")
        print("  Run without --keep to clean up, or delete manually.")
    else:
        if sys.stdin.isatty():
            input("\nPress Enter to clean up test resources...")
        runner.cleanup()

    success = runner.summary()
    sys.exit(0 if success else 1)


def _delete_entry_distribution(dist_id):
    """Delete an entry distribution (with error handling)."""
    try:
        kaltura_post("contentDistribution_entryDistribution", "delete", {"id": dist_id})
    except Exception as e:
        print(f"  [WARN] Failed to delete entry distribution {dist_id}: {e}")


if __name__ == "__main__":
    main()
