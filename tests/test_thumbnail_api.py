#!/usr/bin/env python3
"""
End-to-end validation of the Thumbnail & Image Transformation API.

Covers: dynamic thumbnail URL (dimensions, crop types, vid_sec, vid_slices,
format, quality, sprite strips), thumbAsset CRUD (generate, add, setContent,
setAsDefault, list, delete), thumbParams.
"""

import sys
import os
import base64
import io
import requests

sys.path.insert(0, os.path.dirname(__file__))
from test_helpers import kaltura_post, TestRunner, PARTNER_ID, KS, SERVICE_URL

state = {}


def main():
    runner = TestRunner("Thumbnail & Image API Validation")

    # ════════════════════════════════════════════
    # Phase 1: Find a READY video entry
    # ════════════════════════════════════════════

    def test_find_ready_entry():
        """Find a ready video entry for thumbnail testing."""
        result = kaltura_post("media", "list", {
            "filter[statusEqual]": 2,
            "filter[mediaTypeEqual]": 1,
            "filter[orderBy]": "-plays",
            "filter[playsGreaterThanOrEqual]": 1,
            "pager[pageSize]": 1,
        })
        assert result["totalCount"] > 0, "No ready video entries found"
        entry = result["objects"][0]
        state["entry_id"] = entry["id"]
        state["partner_id"] = str(entry.get("partnerId", PARTNER_ID))
        print(f"    Entry: {entry['id']} — {entry.get('name', '?')}")

    runner.run_test("Find ready video entry", test_find_ready_entry)

    # ════════════════════════════════════════════
    # Phase 2: Dynamic Thumbnail URL API
    # ════════════════════════════════════════════

    def test_thumbnail_default():
        """Verify the default thumbnail URL returns an image."""
        pid = state["partner_id"]
        url = f"https://cdnapisec.kaltura.com/p/{pid}/thumbnail/entry_id/{state['entry_id']}"
        resp = requests.get(url, timeout=15, allow_redirects=True)
        assert resp.status_code == 200, f"Thumbnail returned {resp.status_code}"
        content_type = resp.headers.get("Content-Type", "")
        assert "image" in content_type, f"Expected image, got {content_type}"
        assert len(resp.content) > 100, "Thumbnail too small"
        print(f"    Default thumbnail: {len(resp.content)} bytes, {content_type}")

    runner.run_test("Thumbnail URL — default (120x90)", test_thumbnail_default)

    def test_thumbnail_sized():
        """Verify thumbnail with specific dimensions."""
        pid = state["partner_id"]
        url = (f"https://cdnapisec.kaltura.com/p/{pid}/thumbnail/entry_id/"
               f"{state['entry_id']}/width/640/height/360")
        resp = requests.get(url, timeout=15, allow_redirects=True)
        assert resp.status_code == 200, f"Sized thumbnail returned {resp.status_code}"
        content_type = resp.headers.get("Content-Type", "")
        assert "image" in content_type, f"Expected image, got {content_type}"
        print(f"    Sized thumbnail (640x360): {len(resp.content)} bytes")

    runner.run_test("Thumbnail URL — sized (640x360)", test_thumbnail_sized)

    def test_thumbnail_vid_sec():
        """Verify thumbnail at specific video second."""
        pid = state["partner_id"]
        url = (f"https://cdnapisec.kaltura.com/p/{pid}/thumbnail/entry_id/"
               f"{state['entry_id']}/width/320/height/180/vid_sec/5")
        resp = requests.get(url, timeout=15, allow_redirects=True)
        assert resp.status_code == 200, f"vid_sec thumbnail returned {resp.status_code}"
        assert "image" in resp.headers.get("Content-Type", "")
        print(f"    vid_sec=5 thumbnail: {len(resp.content)} bytes")

    runner.run_test("Thumbnail URL — vid_sec (frame at 5s)", test_thumbnail_vid_sec)

    def test_thumbnail_center_crop():
        """Verify type=3 center crop."""
        pid = state["partner_id"]
        url = (f"https://cdnapisec.kaltura.com/p/{pid}/thumbnail/entry_id/"
               f"{state['entry_id']}/width/400/height/400/type/3")
        resp = requests.get(url, timeout=15, allow_redirects=True)
        assert resp.status_code == 200, f"Center crop returned {resp.status_code}"
        assert "image" in resp.headers.get("Content-Type", "")
        print(f"    Center crop (400x400): {len(resp.content)} bytes")

    runner.run_test("Thumbnail URL — type=3 center crop", test_thumbnail_center_crop)

    def test_thumbnail_padded():
        """Verify type=2 resize with padding."""
        pid = state["partner_id"]
        url = (f"https://cdnapisec.kaltura.com/p/{pid}/thumbnail/entry_id/"
               f"{state['entry_id']}/width/400/height/400/type/2/bgcolor/000000")
        resp = requests.get(url, timeout=15, allow_redirects=True)
        assert resp.status_code == 200, f"Padded thumbnail returned {resp.status_code}"
        assert "image" in resp.headers.get("Content-Type", "")
        print(f"    Padded (400x400 black bg): {len(resp.content)} bytes")

    runner.run_test("Thumbnail URL — type=2 padded with bgcolor", test_thumbnail_padded)

    def test_thumbnail_png_format():
        """Verify format=png output."""
        pid = state["partner_id"]
        url = (f"https://cdnapisec.kaltura.com/p/{pid}/thumbnail/entry_id/"
               f"{state['entry_id']}/width/320/height/180/format/png")
        resp = requests.get(url, timeout=15, allow_redirects=True)
        assert resp.status_code == 200, f"PNG thumbnail returned {resp.status_code}"
        content_type = resp.headers.get("Content-Type", "")
        assert "png" in content_type.lower() or resp.content[:4] == b'\x89PNG', \
            f"Expected PNG, got {content_type}"
        print(f"    PNG thumbnail: {len(resp.content)} bytes, {content_type}")

    runner.run_test("Thumbnail URL — format=png", test_thumbnail_png_format)

    def test_thumbnail_quality():
        """Verify quality parameter affects file size."""
        pid = state["partner_id"]
        base = f"https://cdnapisec.kaltura.com/p/{pid}/thumbnail/entry_id/{state['entry_id']}/width/320/height/180"
        resp_low = requests.get(f"{base}/quality/20", timeout=15, allow_redirects=True)
        resp_high = requests.get(f"{base}/quality/95", timeout=15, allow_redirects=True)
        assert resp_low.status_code == 200 and resp_high.status_code == 200
        size_low = len(resp_low.content)
        size_high = len(resp_high.content)
        assert size_high > size_low, f"Higher quality ({size_high}B) should be larger than low ({size_low}B)"
        print(f"    Quality 20: {size_low}B, Quality 95: {size_high}B")

    runner.run_test("Thumbnail URL — quality parameter", test_thumbnail_quality)

    def test_thumbnail_sprite_strip():
        """Verify vid_slices generates a sprite strip."""
        pid = state["partner_id"]
        url = (f"https://cdnapisec.kaltura.com/p/{pid}/thumbnail/entry_id/"
               f"{state['entry_id']}/width/160/height/90/vid_slices/5")
        resp = requests.get(url, timeout=15, allow_redirects=True)
        assert resp.status_code == 200, f"Sprite strip returned {resp.status_code}"
        assert "image" in resp.headers.get("Content-Type", "")
        assert len(resp.content) > 1000, "Sprite strip too small for 5 slices"
        print(f"    Sprite strip (5 slices): {len(resp.content)} bytes")

    runner.run_test("Thumbnail URL — vid_slices sprite strip", test_thumbnail_sprite_strip)

    def test_thumbnail_single_slice():
        """Verify vid_slice extracts a single slice from a sprite."""
        pid = state["partner_id"]
        url = (f"https://cdnapisec.kaltura.com/p/{pid}/thumbnail/entry_id/"
               f"{state['entry_id']}/width/160/height/90/vid_slices/5/vid_slice/2")
        resp = requests.get(url, timeout=15, allow_redirects=True)
        assert resp.status_code == 200, f"Single slice returned {resp.status_code}"
        assert "image" in resp.headers.get("Content-Type", "")
        print(f"    Single slice (2 of 5): {len(resp.content)} bytes")

    runner.run_test("Thumbnail URL — vid_slice single frame", test_thumbnail_single_slice)

    # ════════════════════════════════════════════
    # Phase 3: thumbAsset API (Stored Thumbnails)
    # ════════════════════════════════════════════

    def test_thumb_asset_generate():
        """Capture a thumbnail from video at a specific offset."""
        entry_id = state["entry_id"]
        result = kaltura_post("thumbAsset", "generate", {
            "entryId": entry_id,
            "thumbParams[objectType]": "KalturaThumbParams",
            "thumbParams[videoOffset]": 3,
        })
        assert "id" in result, f"No thumbAsset ID returned: {result}"
        state["thumb_asset_id"] = result["id"]
        runner.register_cleanup(f"thumbAsset {result['id']}",
                                lambda: _delete_thumb_asset(result["id"]))
        print(f"    Generated thumbAsset: {result['id']}, status={result.get('status')}")

    runner.run_test("thumbAsset.generate — capture frame from video", test_thumb_asset_generate)

    def test_thumb_asset_get():
        """Retrieve a specific thumbnail asset."""
        thumb_id = state.get("thumb_asset_id")
        if not thumb_id:
            raise RuntimeError("No thumbAsset ID")
        result = kaltura_post("thumbAsset", "get", {
            "thumbAssetId": thumb_id,
        })
        assert result.get("id") == thumb_id
        assert result.get("objectType") == "KalturaThumbAsset"
        print(f"    ThumbAsset: {result['id']}, status={result.get('status')}, "
              f"width={result.get('width')}, height={result.get('height')}")

    runner.run_test("thumbAsset.get — retrieve thumbnail asset", test_thumb_asset_get)

    def test_thumb_asset_set_as_default():
        """Set a thumbnail as the entry's default."""
        thumb_id = state.get("thumb_asset_id")
        if not thumb_id:
            raise RuntimeError("No thumbAsset ID")
        kaltura_post("thumbAsset", "setAsDefault", {
            "thumbAssetId": thumb_id,
        })
        print(f"    Set thumbAsset {thumb_id} as default")

    runner.run_test("thumbAsset.setAsDefault — set default thumbnail", test_thumb_asset_set_as_default)

    def test_thumb_asset_list():
        """List all thumbnails for an entry."""
        result = kaltura_post("thumbAsset", "list", {
            "filter[entryIdEqual]": state["entry_id"],
        })
        assert "objects" in result, f"Expected objects: {result}"
        assert result.get("totalCount", 0) > 0, "Expected at least one thumbAsset"
        thumb_ids = [t["id"] for t in result["objects"]]
        print(f"    Found {result['totalCount']} thumbAssets: {', '.join(thumb_ids[:5])}")

    runner.run_test("thumbAsset.list — list thumbnails for entry", test_thumb_asset_list)

    def test_thumb_asset_add_upload():
        """Upload a custom thumbnail image via uploadToken."""
        entry_id = state["entry_id"]
        png_data = base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        )
        token = kaltura_post("uploadToken", "add", {
            "uploadToken[fileName]": "thumb_test.png",
            "uploadToken[fileSize]": len(png_data),
        })
        token_id = token["id"]
        runner.register_cleanup(f"thumb upload token {token_id}",
                                lambda: _delete_token(token_id))

        upload_url = f"{SERVICE_URL}/service/uploadToken/action/upload"
        resp = requests.post(upload_url, data={
            "ks": KS, "format": "1", "uploadTokenId": token_id, "resume": "false",
        }, files={"fileData": ("thumb_test.png", io.BytesIO(png_data), "image/png")})
        assert resp.status_code == 200

        thumb = kaltura_post("thumbAsset", "add", {
            "entryId": entry_id,
            "thumbAsset[objectType]": "KalturaThumbAsset",
            "thumbAsset[tags]": "test-uploaded",
        })
        assert "id" in thumb, f"No thumbAsset ID: {thumb}"
        state["uploaded_thumb_id"] = thumb["id"]
        runner.register_cleanup(f"uploaded thumbAsset {thumb['id']}",
                                lambda: _delete_thumb_asset(thumb["id"]))

        kaltura_post("thumbAsset", "setContent", {
            "id": thumb["id"],
            "contentResource[objectType]": "KalturaUploadedFileTokenResource",
            "contentResource[token]": token_id,
        })
        print(f"    Uploaded thumbAsset: {thumb['id']} (via token {token_id})")

    runner.run_test("thumbAsset.add + setContent — upload custom thumbnail", test_thumb_asset_add_upload)

    def test_thumb_asset_get_url():
        """Get download URL for a thumb asset."""
        thumb_id = state.get("uploaded_thumb_id")
        if not thumb_id:
            raise RuntimeError("No uploaded thumbAsset")
        result = kaltura_post("thumbAsset", "getUrl", {
            "id": thumb_id,
        })
        assert isinstance(result, str) and result.startswith("http"), \
            f"Expected URL, got: {result}"
        print(f"    ThumbAsset URL: {result[:100]}...")

    runner.run_test("thumbAsset.getUrl — get download URL", test_thumb_asset_get_url)

    def test_thumb_asset_delete():
        """Delete a thumbnail asset."""
        thumb_id = state.get("uploaded_thumb_id")
        if not thumb_id:
            raise RuntimeError("No uploaded thumbAsset to delete")
        kaltura_post("thumbAsset", "delete", {"thumbAssetId": thumb_id})
        try:
            kaltura_post("thumbAsset", "get", {"thumbAssetId": thumb_id})
            raise AssertionError(f"thumbAsset {thumb_id} still exists")
        except Exception as e:
            if "THUMB_ASSET_ID_NOT_FOUND" in str(e) or "not found" in str(e).lower():
                print(f"    Deleted thumbAsset {thumb_id} (confirmed not found)")
            else:
                raise

    runner.run_test("thumbAsset.delete — remove thumbnail asset", test_thumb_asset_delete)

    # ════════════════════════════════════════════
    # Phase 4: thumbParams API
    # ════════════════════════════════════════════

    def test_thumb_params_list():
        """List available thumb params (includes system defaults)."""
        result = kaltura_post("thumbParams", "list", {
            "pager[pageSize]": 10,
        })
        assert "objects" in result, f"Expected objects: {result}"
        print(f"    {result.get('totalCount', 0)} thumb params definitions")
        for tp in result.get("objects", [])[:3]:
            print(f"      {tp.get('id')}: {tp.get('name', '?')}, "
                  f"{tp.get('width', '?')}x{tp.get('height', '?')}")

    runner.run_test("thumbParams.list — list thumbnail templates", test_thumb_params_list)

    # ════════════════════════════════════════════
    # Cleanup & Summary
    # ════════════════════════════════════════════

    keep = "--keep" in sys.argv
    if keep:
        print("\n--- Keeping test resources (--keep flag) ---")
        for key, val in state.items():
            if "id" in key.lower():
                print(f"    {key}: {val}")
    else:
        if sys.stdin.isatty():
            input("\nPress Enter to clean up...")
        runner.cleanup()

    success = runner.summary()
    sys.exit(0 if success else 1)


def _delete_thumb_asset(thumb_id):
    try:
        kaltura_post("thumbAsset", "delete", {"thumbAssetId": thumb_id})
    except Exception:
        pass


def _delete_token(token_id):
    try:
        kaltura_post("uploadToken", "delete", {"uploadTokenId": token_id})
    except Exception:
        pass


if __name__ == "__main__":
    print(f"\n{'='*60}")
    print("  KALTURA THUMBNAIL & IMAGE — End-to-End API Validation")
    print(f"{'='*60}\n")
    main()
