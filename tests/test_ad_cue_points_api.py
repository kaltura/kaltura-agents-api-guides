#!/usr/bin/env python3
"""End-to-end validation of the Kaltura Ad Cue Points API.

Covers: ad cue point CRUD, VAST/VPAID protocols, mid-roll and overlay ads,
protocol immutability constraint.
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
        "filter[orderBy]": "-plays",
        "filter[playsGreaterThanOrEqual]": 1,
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
    runner = TestRunner("Ad Cue Points — E2E Validation")

    # ════════════════════════════════════════════
    # Phase 1: Setup
    # ════════════════════════════════════════════

    def test_find_entry():
        entry_id, name = _find_ready_entry()
        state["entry_id"] = entry_id
        print(f"    Using entry: {entry_id} — {name}")

    runner.run_test("baseEntry.list — find READY entry", test_find_entry)

    # ════════════════════════════════════════════
    # Phase 2: Ad Cue Points
    # ════════════════════════════════════════════

    def test_ad_add():
        """Create a mid-roll ad with VAST 2.0."""
        result = kaltura_post("cuepoint_cuepoint", "add", {
            "cuePoint[objectType]": "KalturaAdCuePoint",
            "cuePoint[entryId]": state["entry_id"],
            "cuePoint[startTime]": 60000,
            "cuePoint[protocolType]": 2,
            "cuePoint[sourceUrl]": "https://example.com/vast/test-midroll.xml",
            "cuePoint[adType]": 1,
            "cuePoint[title]": "E2E Test Mid-Roll Ad",
            "cuePoint[tags]": "e2e-ad-test",
        })
        assert result.get("objectType") == "KalturaAdCuePoint"
        assert result.get("protocolType") == 2, f"Expected VAST_2_0 (2), got {result.get('protocolType')}"
        assert result.get("adType") == 1, f"Expected VIDEO (1), got {result.get('adType')}"
        state["ad_cp_id"] = result["id"]
        runner.register_cleanup(f"ad cue point {result['id']}",
                                lambda: _delete_cue_point(result["id"]))
        print(f"    Created: {result['id']}, protocol={result.get('protocolType')}, adType={result.get('adType')}")

    runner.run_test("cuePoint.add — create VAST 2.0 mid-roll ad", test_ad_add)

    def test_ad_protocol_immutable():
        """Verify protocolType cannot be changed after creation."""
        try:
            kaltura_post("cuepoint_cuepoint", "update", {
                "id": state["ad_cp_id"],
                "cuePoint[objectType]": "KalturaAdCuePoint",
                "cuePoint[protocolType]": 1,
            })
            result = kaltura_post("cuepoint_cuepoint", "get", {"id": state["ad_cp_id"]})
            assert result.get("protocolType") == 2, \
                f"protocolType should remain 2, got {result.get('protocolType')}"
            print("    protocolType update silently ignored (remains VAST_2_0)")
        except Exception as e:
            err = str(e)
            assert "NOT_UPDATABLE" in err or "PROPERTY" in err, f"Unexpected error: {err}"
            print(f"    Correctly rejected: {err[:80]}")

    runner.run_test("cuePoint.update — ad protocolType is immutable", test_ad_protocol_immutable)

    def test_overlay_ad():
        """Create an overlay ad (adType=2, non-linear)."""
        result = kaltura_post("cuepoint_cuepoint", "add", {
            "cuePoint[objectType]": "KalturaAdCuePoint",
            "cuePoint[entryId]": state["entry_id"],
            "cuePoint[startTime]": 30000,
            "cuePoint[endTime]": 45000,
            "cuePoint[protocolType]": 1,
            "cuePoint[sourceUrl]": "https://example.com/vast/overlay.xml",
            "cuePoint[adType]": 2,
            "cuePoint[title]": "E2E Overlay Ad",
            "cuePoint[tags]": "e2e-ad-test",
        })
        assert result.get("adType") == 2, f"Expected OVERLAY (2), got {result.get('adType')}"
        assert result.get("endTime") == 45000
        state["overlay_ad_id"] = result["id"]
        runner.register_cleanup(f"overlay ad {result['id']}",
                                lambda: _delete_cue_point(result["id"]))
        print(f"    Created overlay: {result['id']}, adType={result.get('adType')}")

    runner.run_test("cuePoint.add — overlay ad (adType=2, non-linear)", test_overlay_ad)

    def test_pre_roll_ad():
        """Create a pre-roll ad (startTime=0)."""
        result = kaltura_post("cuepoint_cuepoint", "add", {
            "cuePoint[objectType]": "KalturaAdCuePoint",
            "cuePoint[entryId]": state["entry_id"],
            "cuePoint[startTime]": 0,
            "cuePoint[protocolType]": 2,
            "cuePoint[sourceUrl]": "https://example.com/vast/preroll.xml",
            "cuePoint[adType]": 1,
            "cuePoint[title]": "E2E Pre-Roll Ad",
            "cuePoint[tags]": "e2e-ad-test",
        })
        assert result.get("startTime") == 0, f"Expected startTime=0, got {result.get('startTime')}"
        assert result.get("adType") == 1
        state["preroll_ad_id"] = result["id"]
        runner.register_cleanup(f"pre-roll ad {result['id']}",
                                lambda: _delete_cue_point(result["id"]))
        print(f"    Created pre-roll: {result['id']}, startTime={result.get('startTime')}")

    runner.run_test("cuePoint.add — pre-roll ad (startTime=0)", test_pre_roll_ad)

    def test_ad_list():
        """List ad cue points filtered by type and tags."""
        result = kaltura_post("cuepoint_cuepoint", "list", {
            "filter[entryIdEqual]": state["entry_id"],
            "filter[cuePointTypeEqual]": "adCuePoint.Ad",
            "filter[tagsLike]": "e2e-ad-test",
        })
        assert result.get("totalCount", 0) >= 3, \
            f"Expected at least 3 ad cue points, got {result.get('totalCount')}"
        print(f"    Ad cue points: {result.get('totalCount')}")

    runner.run_test("cuePoint.list — filter ad cue points by type", test_ad_list)

    # ════════════════════════════════════════════
    # Cleanup & Summary
    # ════════════════════════════════════════════

    keep = "--keep" in sys.argv
    if keep:
        print("\n--keep flag set. Skipping cleanup.")
        print(f"  Entry: {state.get('entry_id')}")
        print(f"  Mid-roll: {state.get('ad_cp_id')}")
        print(f"  Overlay: {state.get('overlay_ad_id')}")
        print(f"  Pre-roll: {state.get('preroll_ad_id')}")
    else:
        if sys.stdin.isatty():
            input("\nPress Enter to clean up...")
        runner.cleanup()

    success = runner.summary()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
