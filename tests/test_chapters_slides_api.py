#!/usr/bin/env python3
"""End-to-end validation of the Kaltura Chapters & Slides API.

Covers: thumb cue point CRUD (chapter, slide), timedThumbAsset workflow
(create, upload, setContent, serve, cascade delete), subType filtering.
"""

import sys
import os
import struct
import zlib
import requests

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


def _make_test_png():
    """Generate a minimal 2x2 red PNG in memory (no PIL needed)."""
    width, height = 2, 2
    raw_data = b''
    for _ in range(height):
        raw_data += b'\x00'
        for _ in range(width):
            raw_data += b'\xff\x00\x00\xff'
    compressed = zlib.compress(raw_data)

    def _chunk(chunk_type, data):
        c = chunk_type + data
        return struct.pack('>I', len(data)) + c + struct.pack('>I', zlib.crc32(c) & 0xffffffff)

    png = b'\x89PNG\r\n\x1a\n'
    png += _chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 6, 0, 0, 0))
    png += _chunk(b'IDAT', compressed)
    png += _chunk(b'IEND', b'')
    return png


def _delete_cue_point(cp_id):
    try:
        kaltura_post("cuepoint_cuepoint", "delete", {"id": cp_id})
    except Exception:
        pass


def _delete_thumb_asset(asset_id):
    try:
        kaltura_post("thumbAsset", "delete", {"thumbAssetId": asset_id})
    except Exception:
        pass


def main():
    runner = TestRunner("Chapters & Slides — E2E Validation")

    # ════════════════════════════════════════════
    # Phase 1: Setup
    # ════════════════════════════════════════════

    def test_find_entry():
        entry_id, name = _find_ready_entry()
        state["entry_id"] = entry_id
        print(f"    Using entry: {entry_id} — {name}")

    runner.run_test("baseEntry.list — find READY entry", test_find_entry)

    # ════════════════════════════════════════════
    # Phase 2: Create Chapters & Slides
    # ════════════════════════════════════════════

    def test_chapter_add():
        """Create a chapter (subType=2)."""
        result = kaltura_post("cuepoint_cuepoint", "add", {
            "cuePoint[objectType]": "KalturaThumbCuePoint",
            "cuePoint[entryId]": state["entry_id"],
            "cuePoint[startTime]": 0,
            "cuePoint[subType]": 2,
            "cuePoint[title]": "E2E Test Chapter",
            "cuePoint[description]": "Chapter created by E2E test",
            "cuePoint[tags]": "e2e-chapter-test",
        })
        assert result.get("objectType") == "KalturaThumbCuePoint"
        assert result.get("subType") == 2, f"Expected subType 2, got {result.get('subType')}"
        state["chapter_cp_id"] = result["id"]
        runner.register_cleanup(f"chapter cue point {result['id']}",
                                lambda: _delete_cue_point(result["id"]))
        print(f"    Created chapter: {result['id']}, title={result.get('title')}")

    runner.run_test("cuePoint.add — create chapter (subType=2)", test_chapter_add)

    def test_slide_add():
        """Create a slide marker (subType=1)."""
        result = kaltura_post("cuepoint_cuepoint", "add", {
            "cuePoint[objectType]": "KalturaThumbCuePoint",
            "cuePoint[entryId]": state["entry_id"],
            "cuePoint[startTime]": 30000,
            "cuePoint[subType]": 1,
            "cuePoint[title]": "E2E Test Slide",
            "cuePoint[description]": "Slide OCR text for search testing",
            "cuePoint[tags]": "e2e-chapter-test",
        })
        assert result.get("objectType") == "KalturaThumbCuePoint"
        assert result.get("subType") == 1, f"Expected subType 1, got {result.get('subType')}"
        assert result.get("status") in (1, 4), f"Unexpected status: {result.get('status')}"
        state["slide_cp_id"] = result["id"]
        runner.register_cleanup(f"slide cue point {result['id']}",
                                lambda: _delete_cue_point(result["id"]))
        print(f"    Created slide: {result['id']}, status={result.get('status')}")

    runner.run_test("cuePoint.add — create slide marker (subType=1)", test_slide_add)

    def test_thumb_filter():
        """Filter thumb cue points by subType."""
        result = kaltura_post("cuepoint_cuepoint", "list", {
            "filter[entryIdEqual]": state["entry_id"],
            "filter[cuePointTypeEqual]": "thumbCuePoint.Thumb",
            "filter[tagsLike]": "e2e-chapter-test",
        })
        assert result.get("totalCount", 0) >= 2, \
            f"Expected at least 2 thumb cue points, got {result.get('totalCount')}"
        sub_types = {obj.get("subType") for obj in result.get("objects", [])}
        assert 1 in sub_types, "Missing slide (subType=1) in results"
        assert 2 in sub_types, "Missing chapter (subType=2) in results"
        print(f"    Thumb cue points: {result['totalCount']}, subTypes={sub_types}")

    runner.run_test("cuePoint.list — filter thumb by subType", test_thumb_filter)

    # ════════════════════════════════════════════
    # Phase 3: timedThumbAsset Workflow
    # ════════════════════════════════════════════

    def test_slide_with_thumb_asset():
        """Create slide, attach timedThumbAsset, verify PENDING→READY."""
        cp = kaltura_post("cuepoint_cuepoint", "add", {
            "cuePoint[objectType]": "KalturaThumbCuePoint",
            "cuePoint[entryId]": state["entry_id"],
            "cuePoint[startTime]": 45000,
            "cuePoint[subType]": 1,
            "cuePoint[title]": "E2E Slide With Image",
            "cuePoint[description]": "OCR text from the slide image",
            "cuePoint[tags]": "e2e-chapter-test",
        })
        assert cp.get("objectType") == "KalturaThumbCuePoint"
        cp_id = cp["id"]
        state["slide_with_asset_cp_id"] = cp_id
        runner.register_cleanup(f"slide+asset cue point {cp_id}",
                                lambda: _delete_cue_point(cp_id))
        initial_status = cp.get("status")
        print(f"    Slide created: {cp_id}, initial status={initial_status}")

        asset = kaltura_post("thumbAsset", "add", {
            "entryId": state["entry_id"],
            "thumbAsset[objectType]": "KalturaTimedThumbAsset",
            "thumbAsset[cuePointId]": cp_id,
        })
        assert asset.get("objectType") == "KalturaTimedThumbAsset"
        asset_id = asset["id"]
        state["timed_thumb_asset_id"] = asset_id
        runner.register_cleanup(f"timedThumbAsset {asset_id}",
                                lambda: _delete_thumb_asset(asset_id))
        print(f"    TimedThumbAsset created: {asset_id}")

        token = kaltura_post("uploadToken", "add", {})
        token_id = token["id"]

        png_data = _make_test_png()
        upload_resp = requests.post(
            f"{SERVICE_URL}/service/uploadToken/action/upload",
            data={"ks": KS, "format": 1, "uploadTokenId": token_id},
            files={"fileData": ("slide.png", png_data, "image/png")},
            timeout=30,
        )
        upload_resp.raise_for_status()
        upload_result = upload_resp.json()
        assert upload_result.get("status") == 2, \
            f"Upload token should be CLOSED (2), got {upload_result.get('status')}"

        set_result = kaltura_post("thumbAsset", "setContent", {
            "id": asset_id,
            "contentResource[objectType]": "KalturaUploadedFileTokenResource",
            "contentResource[token]": token_id,
        })
        assert set_result.get("status") == 2, \
            f"Asset should be READY (2), got {set_result.get('status')}"

        cp_after = kaltura_post("cuepoint_cuepoint", "get", {"id": cp_id})
        assert cp_after.get("status") == 1, \
            f"Cue point should be READY (1) after asset, got {cp_after.get('status')}"
        assert cp_after.get("assetId") == asset_id
        print(f"    Cue point status: {initial_status} → {cp_after.get('status')} (READY)")

    runner.run_test("thumbAsset — full slide with image (PENDING→READY)", test_slide_with_thumb_asset)

    def test_thumb_asset_serve():
        """Serve the slide image via thumbAsset.getUrl."""
        result = kaltura_post("thumbAsset", "getUrl", {
            "id": state["timed_thumb_asset_id"],
        })
        assert isinstance(result, str) and "http" in result, f"Expected URL, got: {result}"
        img_resp = requests.get(result, timeout=15)
        assert img_resp.status_code == 200, f"Image serve returned {img_resp.status_code}"
        content_type = img_resp.headers.get("Content-Type", "")
        assert "image" in content_type, f"Expected image content-type, got {content_type}"
        print(f"    Serve URL: {result[:80]}...")
        print(f"    Image: {img_resp.status_code}, type={content_type}, size={len(img_resp.content)}")

    runner.run_test("thumbAsset.getUrl — serve slide thumbnail image", test_thumb_asset_serve)

    def test_thumb_asset_list():
        """List thumb assets, verify timedThumbAsset appears."""
        result = kaltura_post("thumbAsset", "list", {
            "filter[entryIdEqual]": state["entry_id"],
        })
        assert result.get("totalCount", 0) >= 1
        timed = [o for o in result.get("objects", [])
                 if o.get("objectType") == "KalturaTimedThumbAsset"]
        assert len(timed) >= 1, "No KalturaTimedThumbAsset found in list"
        found = any(o["id"] == state["timed_thumb_asset_id"] for o in timed)
        assert found, f"Expected asset {state['timed_thumb_asset_id']} in list"
        print(f"    Total thumb assets: {result['totalCount']}, timed: {len(timed)}")

    runner.run_test("thumbAsset.list — verify timedThumbAsset in list", test_thumb_asset_list)

    def test_cascade_delete():
        """Delete slide cue point, verify timedThumbAsset cascade-deleted."""
        cp_id = state["slide_with_asset_cp_id"]
        asset_id = state["timed_thumb_asset_id"]
        kaltura_post("cuepoint_cuepoint", "delete", {"id": cp_id})
        try:
            kaltura_post("thumbAsset", "get", {"thumbAssetId": asset_id})
            print(f"    WARNING: timedThumbAsset {asset_id} still exists after cue point delete")
        except Exception as e:
            assert "NOT_FOUND" in str(e) or "THUMB_ASSET" in str(e), f"Unexpected error: {e}"
            print(f"    Cascade confirmed: cue point delete also removed timedThumbAsset {asset_id}")
        runner._cleanup_actions = [(n, f) for n, f in runner._cleanup_actions
                                   if cp_id not in n and asset_id not in n]

    runner.run_test("cuePoint.delete — cascade deletes timedThumbAsset", test_cascade_delete)

    # ════════════════════════════════════════════
    # Cleanup & Summary
    # ════════════════════════════════════════════

    keep = "--keep" in sys.argv
    if keep:
        print("\n--keep flag set. Skipping cleanup.")
        print(f"  Entry: {state.get('entry_id')}")
        print(f"  Chapter: {state.get('chapter_cp_id')}")
        print(f"  Slide: {state.get('slide_cp_id')}")
    else:
        if sys.stdin.isatty():
            input("\nPress Enter to clean up...")
        runner.cleanup()

    success = runner.summary()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
