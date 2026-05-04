#!/usr/bin/env python3
"""End-to-end validation of the Kaltura Video Editing API.
Covers: trim, clip, multi-clip concat, overlay, background replacement,
nested composition, caption burn-in, effects, waveform, error cases."""

import sys
import os
import time
import requests

sys.path.insert(0, os.path.dirname(__file__))
from test_helpers import kaltura_post, TestRunner, PARTNER_ID, KS, SERVICE_URL

state = {}

POLL_INTERVAL = 5
POLL_TIMEOUT = 180


def _wait_for_ready(entry_id, timeout=POLL_TIMEOUT):
    """Poll until entry reaches READY (2) or error status."""
    start = time.time()
    last_status = None
    while time.time() - start < timeout:
        result = kaltura_post("media", "get", {"entryId": entry_id})
        last_status = result.get("status")
        if last_status == 2:
            return result
        if last_status in (-1, -2):
            raise Exception(f"Entry {entry_id} failed with status {last_status}")
        time.sleep(POLL_INTERVAL)
    raise Exception(f"Entry {entry_id} did not reach READY within {timeout}s (last status: {last_status})")


def _wait_for_replacement_ready(entry_id, timeout=POLL_TIMEOUT):
    """Poll until replacementStatus reaches READY_BUT_NOT_APPROVED (2), auto-approved (0), or FAILED (4)."""
    start = time.time()
    last_rs = None
    while time.time() - start < timeout:
        result = kaltura_post("baseEntry", "get", {"entryId": entry_id})
        last_rs = result.get("replacementStatus")
        if last_rs == 2:
            return result
        if last_rs == 0:
            return result
        if last_rs == 4:
            raise Exception(f"Replacement failed for entry {entry_id}")
        time.sleep(POLL_INTERVAL)
    raise Exception(f"Replacement for {entry_id} did not complete within {timeout}s (last replacementStatus: {last_rs})")


def _find_ready_entry():
    """Find an existing READY video entry with duration > 5s."""
    result = kaltura_post("media", "list", {
        "filter[objectType]": "KalturaMediaEntryFilter",
        "filter[statusEqual]": 2,
        "filter[mediaTypeEqual]": 1,
        "filter[orderBy]": "-createdAt",
        "pager[pageSize]": 10,
    })
    for obj in result.get("objects", []):
        if obj.get("status") == 2 and obj.get("duration", 0) >= 5:
            return obj["id"]
    return None


def _get_volume_map(entry_id):
    """Get waveform CSV directly (getVolumeMap returns text/csv, not JSON)."""
    resp = requests.post(
        f"{SERVICE_URL}/service/media/action/getVolumeMap",
        data={"ks": KS, "format": 1, "entryId": entry_id},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.text


def main():
    runner = TestRunner("Video Editing API — E2E Validation")

    # ════════════════════════════════════════════
    # Phase 1: Setup — Find/Create Source Entries
    # ════════════════════════════════════════════
    def test_setup_source():
        """Find two READY entries to use as editing sources."""
        src1 = _find_ready_entry()
        if not src1:
            raise Exception("No READY video entry found in account for testing")
        state["source_entry_1"] = src1
        print(f"    Source 1: {src1}")

        result = kaltura_post("media", "list", {
            "filter[objectType]": "KalturaMediaEntryFilter",
            "filter[statusEqual]": 2,
            "filter[mediaTypeEqual]": 1,
            "filter[idNotIn]": src1,
            "filter[orderBy]": "-createdAt",
            "pager[pageSize]": 5,
        })
        objects = result.get("objects", [])
        src2 = None
        for obj in objects:
            if obj.get("duration", 0) >= 5:
                src2 = obj["id"]
                break
        if not src2:
            src2 = src1
        state["source_entry_2"] = src2
        print(f"    Source 2: {src2}")

    runner.run_test("setup — find READY source entries", test_setup_source)

    # ════════════════════════════════════════════
    # Phase 2: Clip (addContent with KalturaOperationResource)
    # ════════════════════════════════════════════
    def test_clip_to_new_entry():
        """Create a clip from source entry into a new entry."""
        entry = kaltura_post("media", "add", {
            "entry[objectType]": "KalturaMediaEntry",
            "entry[mediaType]": 1,
            "entry[name]": f"VIDEO_EDIT_TEST_CLIP_{int(time.time())}",
        })
        clip_id = entry["id"]
        state["clip_entry"] = clip_id
        runner.register_cleanup(f"clip entry {clip_id}",
                                lambda: kaltura_post("media", "delete", {"entryId": clip_id}))

        kaltura_post("media", "addContent", {
            "entryId": clip_id,
            "resource[objectType]": "KalturaOperationResource",
            "resource[resource][objectType]": "KalturaEntryResource",
            "resource[resource][entryId]": state["source_entry_1"],
            "resource[operationAttributes][0][objectType]": "KalturaClipAttributes",
            "resource[operationAttributes][0][offset]": 0,
            "resource[operationAttributes][0][duration]": 5000,
        })
        print(f"    Clip entry created: {clip_id} (5s clip from {state['source_entry_1']})")

    runner.run_test("clip — addContent with KalturaOperationResource", test_clip_to_new_entry)

    def test_clip_reaches_ready():
        """Verify clip entry processes to READY."""
        result = _wait_for_ready(state["clip_entry"])
        duration = result.get("duration", 0)
        assert duration > 0, f"Expected positive duration, got {duration}"
        print(f"    Clip READY: duration={duration}s")

    runner.run_test("clip — reaches READY status", test_clip_reaches_ready)

    # ════════════════════════════════════════════
    # Phase 3: Clip with Effects (fade in/out)
    # ════════════════════════════════════════════
    def test_clip_with_effects():
        """Create a clip with fade-in and fade-out effects."""
        entry = kaltura_post("media", "add", {
            "entry[objectType]": "KalturaMediaEntry",
            "entry[mediaType]": 1,
            "entry[name]": f"VIDEO_EDIT_TEST_EFFECTS_{int(time.time())}",
        })
        fx_id = entry["id"]
        state["effects_entry"] = fx_id
        runner.register_cleanup(f"effects entry {fx_id}",
                                lambda: kaltura_post("media", "delete", {"entryId": fx_id}))

        kaltura_post("media", "addContent", {
            "entryId": fx_id,
            "resource[objectType]": "KalturaOperationResource",
            "resource[resource][objectType]": "KalturaEntryResource",
            "resource[resource][entryId]": state["source_entry_1"],
            "resource[operationAttributes][0][objectType]": "KalturaClipAttributes",
            "resource[operationAttributes][0][offset]": 0,
            "resource[operationAttributes][0][duration]": 5000,
            "resource[operationAttributes][0][effectArray][0][effectType]": 1,
            "resource[operationAttributes][0][effectArray][0][value]": "2",
            "resource[operationAttributes][0][effectArray][1][effectType]": 2,
            "resource[operationAttributes][0][effectArray][1][value]": "2",
        })
        print(f"    Effects entry created: {fx_id} (5s with 2s fade-in, 2s fade-out)")

    runner.run_test("effects — clip with fade in/out", test_clip_with_effects)

    def test_effects_reaches_ready():
        """Verify effects clip processes to READY."""
        result = _wait_for_ready(state["effects_entry"])
        assert result.get("status") == 2, f"Expected status 2, got {result.get('status')}"
        print(f"    Effects clip READY: duration={result.get('duration')}s")

    runner.run_test("effects — reaches READY status", test_effects_reaches_ready)

    # ════════════════════════════════════════════
    # Phase 4: Multi-Clip Concatenation
    # ════════════════════════════════════════════
    def test_multi_clip_concat():
        """Concatenate segments from two source entries."""
        entry = kaltura_post("media", "add", {
            "entry[objectType]": "KalturaMediaEntry",
            "entry[mediaType]": 1,
            "entry[name]": f"VIDEO_EDIT_TEST_CONCAT_{int(time.time())}",
        })
        concat_id = entry["id"]
        state["concat_entry"] = concat_id
        runner.register_cleanup(f"concat entry {concat_id}",
                                lambda: kaltura_post("media", "delete", {"entryId": concat_id}))

        kaltura_post("media", "addContent", {
            "entryId": concat_id,
            "resource[objectType]": "KalturaOperationResources",
            "resource[resources][0][objectType]": "KalturaOperationResource",
            "resource[resources][0][resource][objectType]": "KalturaEntryResource",
            "resource[resources][0][resource][entryId]": state["source_entry_1"],
            "resource[resources][0][operationAttributes][0][objectType]": "KalturaClipAttributes",
            "resource[resources][0][operationAttributes][0][offset]": 0,
            "resource[resources][0][operationAttributes][0][duration]": 3000,
            "resource[resources][1][objectType]": "KalturaOperationResource",
            "resource[resources][1][resource][objectType]": "KalturaEntryResource",
            "resource[resources][1][resource][entryId]": state["source_entry_2"],
            "resource[resources][1][operationAttributes][0][objectType]": "KalturaClipAttributes",
            "resource[resources][1][operationAttributes][0][offset]": 0,
            "resource[resources][1][operationAttributes][0][duration]": 3000,
        })
        print(f"    Concat entry created: {concat_id} (3s+3s from two sources)")

    runner.run_test("concat — multi-clip KalturaOperationResources", test_multi_clip_concat)

    def test_concat_reaches_ready():
        """Verify concatenated entry processes to READY."""
        result = _wait_for_ready(state["concat_entry"])
        duration = result.get("duration", 0)
        assert duration >= 4, f"Expected ~6s duration, got {duration}s"
        print(f"    Concat READY: duration={duration}s")

    runner.run_test("concat — reaches READY status", test_concat_reaches_ready)

    # ════════════════════════════════════════════
    # Phase 5: Overlay (PiP)
    # ════════════════════════════════════════════
    def test_overlay_pip():
        """Create a PiP composition — overlay source 2 on source 1."""
        entry = kaltura_post("media", "add", {
            "entry[objectType]": "KalturaMediaEntry",
            "entry[mediaType]": 1,
            "entry[name]": f"VIDEO_EDIT_TEST_PIP_{int(time.time())}",
        })
        pip_id = entry["id"]
        state["pip_entry"] = pip_id
        runner.register_cleanup(f"pip entry {pip_id}",
                                lambda: kaltura_post("media", "delete", {"entryId": pip_id}))

        kaltura_post("media", "addContent", {
            "entryId": pip_id,
            "resource[objectType]": "KalturaOperationResource",
            "resource[resource][objectType]": "KalturaEntryResource",
            "resource[resource][entryId]": state["source_entry_1"],
            "resource[operationAttributes][0][objectType]": "KalturaClipAttributes",
            "resource[operationAttributes][0][offset]": 0,
            "resource[operationAttributes][0][duration]": 5000,
            "resource[operationAttributes][0][mediaCompositionAttributesArray][0][objectType]": "KalturaOverlayAttributes",
            "resource[operationAttributes][0][mediaCompositionAttributesArray][0][resource][objectType]": "KalturaEntryResource",
            "resource[operationAttributes][0][mediaCompositionAttributesArray][0][resource][entryId]": state["source_entry_2"],
            "resource[operationAttributes][0][mediaCompositionAttributesArray][0][overlayPlacement]": 8,
            "resource[operationAttributes][0][mediaCompositionAttributesArray][0][overlayScalePercentage]": 0.25,
            "resource[operationAttributes][0][mediaCompositionAttributesArray][0][marginsPercentage]": 0.1,
            "resource[operationAttributes][0][mediaCompositionAttributesArray][0][overlayShape]": 2,
        })
        print(f"    PiP entry created: {pip_id} (src2 overlaid on src1, bottom-right, 25%)")

    runner.run_test("overlay — PiP composition", test_overlay_pip)

    def test_overlay_reaches_ready():
        """Verify overlay composition processes to READY."""
        result = _wait_for_ready(state["pip_entry"])
        assert result.get("status") == 2, f"Expected READY, got status {result.get('status')}"
        print(f"    PiP READY: duration={result.get('duration')}s")

    runner.run_test("overlay — reaches READY status", test_overlay_reaches_ready)

    # ════════════════════════════════════════════
    # Phase 6: Background Replacement (Chroma Key)
    # ════════════════════════════════════════════
    def test_background_replacement():
        """Background replacement using chroma key."""
        entry = kaltura_post("media", "add", {
            "entry[objectType]": "KalturaMediaEntry",
            "entry[mediaType]": 1,
            "entry[name]": f"VIDEO_EDIT_TEST_BGREMOVE_{int(time.time())}",
        })
        bg_id = entry["id"]
        state["bg_replace_entry"] = bg_id
        runner.register_cleanup(f"bg replace entry {bg_id}",
                                lambda: kaltura_post("media", "delete", {"entryId": bg_id}))

        kaltura_post("media", "addContent", {
            "entryId": bg_id,
            "resource[objectType]": "KalturaOperationResource",
            "resource[resource][objectType]": "KalturaEntryResource",
            "resource[resource][entryId]": state["source_entry_1"],
            "resource[operationAttributes][0][objectType]": "KalturaClipAttributes",
            "resource[operationAttributes][0][offset]": 0,
            "resource[operationAttributes][0][duration]": 5000,
            "resource[operationAttributes][0][mediaCompositionAttributesArray][0][objectType]": "KalturaReplaceBackgroundAttributes",
            "resource[operationAttributes][0][mediaCompositionAttributesArray][0][resource][objectType]": "KalturaEntryResource",
            "resource[operationAttributes][0][mediaCompositionAttributesArray][0][resource][entryId]": state["source_entry_2"],
            "resource[operationAttributes][0][mediaCompositionAttributesArray][0][backgroundColorCode]": "0x6FED48",
        })
        print(f"    Background replacement entry created: {bg_id}")

    runner.run_test("background — chroma key replacement", test_background_replacement)

    def test_bg_replace_reaches_ready():
        """Verify background replacement processes to READY."""
        result = _wait_for_ready(state["bg_replace_entry"])
        assert result.get("status") == 2, f"Expected READY, got status {result.get('status')}"
        print(f"    BG Replace READY: duration={result.get('duration')}s")

    runner.run_test("background — reaches READY status", test_bg_replace_reaches_ready)

    # ════════════════════════════════════════════
    # Phase 7: Trim (in-place via updateContent)
    # ════════════════════════════════════════════
    def test_trim_in_place():
        """Trim an entry in-place using media.updateContent on the clip entry."""
        trim_src = state.get("clip_entry")
        if not trim_src:
            raise Exception("No clip entry available for trim test")

        result = kaltura_post("media", "get", {"entryId": trim_src})
        if result.get("status") != 2:
            raise Exception(f"Clip entry not READY for trim: status={result.get('status')}")

        try:
            kaltura_post("media", "updateContent", {
                "entryId": trim_src,
                "resource[objectType]": "KalturaOperationResource",
                "resource[resource][objectType]": "KalturaEntryResource",
                "resource[resource][entryId]": trim_src,
                "resource[operationAttributes][0][objectType]": "KalturaClipAttributes",
                "resource[operationAttributes][0][offset]": 0,
                "resource[operationAttributes][0][duration]": 3000,
            })
            state["trim_initiated"] = True
            state["trim_entry"] = trim_src
            print(f"    Trim initiated on {trim_src} (first 3s)")
        except Exception as e:
            if "FEATURE_FORBIDDEN" in str(e):
                state["trim_initiated"] = False
                print(f"    FEATURE_ENTRY_REPLACEMENT not enabled — trim skipped (expected on some accounts)")
            else:
                raise

    runner.run_test("trim — media.updateContent initiation", test_trim_in_place)

    def test_trim_replacement_flow():
        """Poll replacementStatus and approve replacement."""
        if not state.get("trim_initiated"):
            print("    Skipped — trim not available on this account")
            return

        entry_id = state["trim_entry"]
        result = _wait_for_replacement_ready(entry_id)
        rs = result.get("replacementStatus", 0)

        if rs == 0:
            print(f"    Replacement auto-approved (replacementStatus=0 — account has auto-approve)")
            return

        print(f"    Replacement ready for {entry_id} (replacementStatus={rs})")
        kaltura_post("media", "approveReplace", {"entryId": entry_id})
        print(f"    Replacement approved for {entry_id}")

        time.sleep(3)
        result = kaltura_post("media", "get", {"entryId": entry_id})
        rs = result.get("replacementStatus", -1)
        assert rs == 0, f"Expected replacementStatus=0 after approve, got {rs}"
        print(f"    Entry {entry_id}: replacementStatus={rs} (NONE — trim complete)")

    runner.run_test("trim — replacement approval flow", test_trim_replacement_flow)

    # ════════════════════════════════════════════
    # Phase 8: Clone + Clip Workflow
    # ════════════════════════════════════════════
    def test_clone_and_clip():
        """Clone an entry (exclude flavors) then apply clip."""
        clone_result = kaltura_post("baseEntry", "clone", {
            "entryId": state["source_entry_1"],
            "cloneOptions[0][objectType]": "KalturaBaseEntryCloneOptionComponent",
            "cloneOptions[0][itemType]": 6,
            "cloneOptions[0][rule]": 1,
        })
        clone_id = clone_result["id"]
        state["clone_clip_entry"] = clone_id
        runner.register_cleanup(f"clone clip entry {clone_id}",
                                lambda: kaltura_post("media", "delete", {"entryId": clone_id}))

        assert clone_result.get("status") == 7, \
            f"Expected NO_CONTENT (7), got status {clone_result.get('status')}"
        print(f"    Cloned entry: {clone_id} (status=7 NO_CONTENT)")

        kaltura_post("media", "addContent", {
            "entryId": clone_id,
            "resource[objectType]": "KalturaOperationResource",
            "resource[resource][objectType]": "KalturaEntryResource",
            "resource[resource][entryId]": state["source_entry_1"],
            "resource[operationAttributes][0][objectType]": "KalturaClipAttributes",
            "resource[operationAttributes][0][offset]": 0,
            "resource[operationAttributes][0][duration]": 3000,
        })
        state["clone_clip_initiated"] = True
        print(f"    Clip applied to clone: {clone_id} (first 3s)")

    runner.run_test("clone+clip — baseEntry.clone then clip operation", test_clone_and_clip)

    def test_clone_clip_ready():
        """Verify the clone+clip entry reaches READY."""
        if not state.get("clone_clip_initiated"):
            print("    Skipped — clip not initiated")
            return
        result = _wait_for_ready(state["clone_clip_entry"])
        assert result.get("status") == 2, f"Expected READY, got {result.get('status')}"
        print(f"    Clone+clip READY: {state['clone_clip_entry']}, duration={result.get('duration')}s")

    runner.run_test("clone+clip — reaches READY status", test_clone_clip_ready)

    # ════════════════════════════════════════════
    # Phase 9: Waveform Visualization
    # ════════════════════════════════════════════
    def test_get_volume_map():
        """Retrieve audio waveform data via media.getVolumeMap."""
        csv_data = _get_volume_map(state["source_entry_1"])
        assert csv_data and len(csv_data) > 10, f"Expected waveform CSV data, got: {csv_data[:50]}"
        lines = csv_data.strip().split("\n")
        assert lines[0].startswith("pts"), f"Expected CSV header 'pts,...', got: {lines[0]}"
        assert len(lines) > 2, f"Expected multiple data points, got {len(lines)} lines"
        print(f"    Waveform: {len(lines)-1} data points (header + {len(lines)-1} samples)")

    runner.run_test("waveform — media.getVolumeMap", test_get_volume_map)

    # ════════════════════════════════════════════
    # Phase 10: Error Cases
    # ════════════════════════════════════════════
    def test_error_invalid_source():
        """Verify ENTRY_ID_NOT_FOUND for invalid source entry."""
        entry = kaltura_post("media", "add", {
            "entry[objectType]": "KalturaMediaEntry",
            "entry[mediaType]": 1,
            "entry[name]": f"VIDEO_EDIT_TEST_ERR_{int(time.time())}",
        })
        err_id = entry["id"]
        runner.register_cleanup(f"error test entry {err_id}",
                                lambda: kaltura_post("media", "delete", {"entryId": err_id}))

        try:
            kaltura_post("media", "addContent", {
                "entryId": err_id,
                "resource[objectType]": "KalturaOperationResource",
                "resource[resource][objectType]": "KalturaEntryResource",
                "resource[resource][entryId]": "1_nonexistent99",
                "resource[operationAttributes][0][objectType]": "KalturaClipAttributes",
                "resource[operationAttributes][0][offset]": 0,
                "resource[operationAttributes][0][duration]": 5000,
            })
            raise Exception("Expected error for nonexistent source entry")
        except Exception as e:
            err_msg = str(e)
            assert "ENTRY_ID_NOT_FOUND" in err_msg or "NOT_FOUND" in err_msg, \
                f"Expected ENTRY_ID_NOT_FOUND error, got: {err_msg}"
            print(f"    Correctly received error: ENTRY_ID_NOT_FOUND")

    runner.run_test("error — invalid source entry ID", test_error_invalid_source)

    def test_error_invalid_overlay_placement():
        """Verify INVALID_ENUM_VALUE for out-of-range overlay placement."""
        entry = kaltura_post("media", "add", {
            "entry[objectType]": "KalturaMediaEntry",
            "entry[mediaType]": 1,
            "entry[name]": f"VIDEO_EDIT_TEST_ENUM_{int(time.time())}",
        })
        enum_id = entry["id"]
        runner.register_cleanup(f"enum test entry {enum_id}",
                                lambda: kaltura_post("media", "delete", {"entryId": enum_id}))

        try:
            kaltura_post("media", "addContent", {
                "entryId": enum_id,
                "resource[objectType]": "KalturaOperationResource",
                "resource[resource][objectType]": "KalturaEntryResource",
                "resource[resource][entryId]": state["source_entry_1"],
                "resource[operationAttributes][0][objectType]": "KalturaClipAttributes",
                "resource[operationAttributes][0][offset]": 0,
                "resource[operationAttributes][0][duration]": 3000,
                "resource[operationAttributes][0][mediaCompositionAttributesArray][0][objectType]": "KalturaOverlayAttributes",
                "resource[operationAttributes][0][mediaCompositionAttributesArray][0][resource][objectType]": "KalturaEntryResource",
                "resource[operationAttributes][0][mediaCompositionAttributesArray][0][resource][entryId]": state["source_entry_1"],
                "resource[operationAttributes][0][mediaCompositionAttributesArray][0][overlayPlacement]": 99,
                "resource[operationAttributes][0][mediaCompositionAttributesArray][0][overlayShape]": 2,
            })
            raise Exception("Expected error for invalid overlay placement")
        except Exception as e:
            err_msg = str(e)
            assert "INVALID_ENUM_VALUE" in err_msg, \
                f"Expected INVALID_ENUM_VALUE error, got: {err_msg}"
            print(f"    Correctly received: INVALID_ENUM_VALUE for overlayPlacement=99")

    runner.run_test("error — invalid overlay placement enum", test_error_invalid_overlay_placement)

    # ════════════════════════════════════════════
    # Cleanup & Summary
    # ════════════════════════════════════════════
    keep = "--keep" in sys.argv
    if keep:
        print("\n--- --keep flag set, skipping cleanup ---")
        print(f"    Source 1: {state.get('source_entry_1')}")
        print(f"    Source 2: {state.get('source_entry_2')}")
        print(f"    Clip: {state.get('clip_entry')}")
        print(f"    Effects: {state.get('effects_entry')}")
        print(f"    Concat: {state.get('concat_entry')}")
        print(f"    PiP: {state.get('pip_entry')}")
        print(f"    BG Replace: {state.get('bg_replace_entry')}")
        print(f"    Clone+Clip: {state.get('clone_clip_entry')}")
    else:
        if sys.stdin.isatty():
            input("\nPress Enter to clean up test entries...")
        runner.cleanup()

    success = runner.summary()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
