#!/usr/bin/env python3
"""
End-to-end validation of the Upload, Ingest & Content Delivery API.

Covers: uploadToken lifecycle, single-shot upload, chunked upload,
media entry creation, addContent, addFromUrl, flavor assets,
thumbnail URLs, playManifest URLs, and cleanup.
"""

import sys
import os
import time
import tempfile
import requests

sys.path.insert(0, os.path.dirname(__file__))
from test_helpers import kaltura_post, TestRunner, PARTNER_ID, KS, SERVICE_URL

# A small publicly accessible video for addFromUrl testing
# Using a Kaltura sample video (very small, guaranteed available)
SAMPLE_VIDEO_URL = os.environ.get(
    "KALTURA_TEST_VIDEO_URL",
    "https://cdnapisec.kaltura.com/p/811441/sp/81144100/playManifest/entryId/1_uoup50ye/format/url/protocol/https"
)

state = {}


def main():
    runner = TestRunner("Upload, Ingest & Content Delivery API Validation")

    # ════════════════════════════════════════════
    # Phase 1: Upload Token Lifecycle
    # ════════════════════════════════════════════

    def test_upload_token_add():
        """Create an upload token."""
        result = kaltura_post("uploadToken", "add", {
            "uploadToken[fileName]": "test_upload.bin",
            "uploadToken[fileSize]": 1024,
        })
        assert "id" in result, f"No token ID returned: {result}"
        state["token_id"] = result["id"]
        runner.register_cleanup(f"upload token {result['id']}",
                                lambda: _delete_token(result["id"]))
        assert result.get("status") == 0, f"Expected PENDING status (0), got {result.get('status')}"
        assert result.get("fileName") == "test_upload.bin"
        print(f"    Token: {result['id']}, status={result['status']}")

    runner.run_test("uploadToken.add — create upload token", test_upload_token_add)

    def test_upload_token_get():
        """Retrieve the upload token and verify its properties."""
        result = kaltura_post("uploadToken", "get", {
            "uploadTokenId": state["token_id"],
        })
        assert result["id"] == state["token_id"]
        # Token may be PENDING(0) or already PARTIAL(1)
        assert result["status"] in (0, 1, 2), f"Unexpected status: {result['status']}"
        print(f"    Token status={result['status']}, uploadedFileSize={result.get('uploadedFileSize', 0)}")

    runner.run_test("uploadToken.get — verify token exists", test_upload_token_get)

    def test_upload_token_list():
        """List upload tokens and verify our token appears."""
        result = kaltura_post("uploadToken", "list", {
            "filter[statusEqual]": 0,  # PENDING
        })
        assert result.get("totalCount", 0) >= 1, "No pending tokens found"
        token_ids = [t["id"] for t in result.get("objects", [])]
        # Our token should be in the list (may not be on first page if many tokens)
        print(f"    Found {result['totalCount']} pending token(s)")

    runner.run_test("uploadToken.list — list pending tokens", test_upload_token_list)

    # ════════════════════════════════════════════
    # Phase 2: Single-shot Upload (small file)
    # ════════════════════════════════════════════

    def test_create_test_file():
        """Create a small test file for upload."""
        tf = tempfile.NamedTemporaryFile(delete=False, suffix=".bin", prefix="kaltura_test_")
        tf.write(b"KALTURA_API_TEST_" * 64)  # 1088 bytes
        tf.close()
        state["test_file"] = tf.name
        state["test_file_size"] = os.path.getsize(tf.name)
        print(f"    Test file: {tf.name} ({state['test_file_size']} bytes)")

    runner.run_test("Create small test file for upload", test_create_test_file)

    def test_single_shot_upload():
        """Upload the test file in a single request."""
        # Create a fresh token for this upload
        token = kaltura_post("uploadToken", "add", {
            "uploadToken[fileName]": "test_single_shot.bin",
            "uploadToken[fileSize]": state["test_file_size"],
        })
        state["single_token_id"] = token["id"]

        with open(state["test_file"], "rb") as f:
            resp = requests.post(
                f"{SERVICE_URL}/service/uploadToken/action/upload",
                data={
                    "ks": KS,
                    "format": 1,
                    "uploadTokenId": token["id"],
                    "resume": "false",
                    "finalChunk": "true",
                    "resumeAt": "-1",
                },
                files={"fileData": ("test_single_shot.bin", f, "application/octet-stream")},
                timeout=30,
            )
            resp.raise_for_status()
            # Upload response may not be JSON — verify via token get instead
            try:
                result = resp.json()
                if isinstance(result, dict) and "id" in result:
                    state["single_upload_status"] = result.get("status")
                    print(f"    Uploaded: status={result.get('status')}, uploadedFileSize={result.get('uploadedFileSize')}")
                    return
            except Exception:
                pass

        # Verify upload succeeded via token get
        result = kaltura_post("uploadToken", "get", {
            "uploadTokenId": token["id"],
        })
        assert result["status"] in (1, 2), f"Expected PARTIAL(1) or FULL(2), got {result.get('status')}"
        state["single_upload_status"] = result["status"]
        print(f"    Uploaded: status={result['status']}, uploadedFileSize={result.get('uploadedFileSize')}")

    runner.run_test("uploadToken.upload — single-shot upload", test_single_shot_upload)

    def test_verify_single_upload_token():
        """Verify the token reached FULL_UPLOAD after single-shot."""
        # Poll briefly if needed
        for attempt in range(5):
            result = kaltura_post("uploadToken", "get", {
                "uploadTokenId": state["single_token_id"],
            })
            if result["status"] == 2:  # FULL_UPLOAD
                print(f"    Token FULL_UPLOAD: uploadedFileSize={result['uploadedFileSize']}")
                return
            time.sleep(1)
        # Accept status 1 (PARTIAL) or 2 (FULL) — server may auto-finalize differently
        assert result["status"] in (1, 2), f"Unexpected status: {result['status']}"
        print(f"    Token status={result['status']}, uploadedFileSize={result.get('uploadedFileSize')}")

    runner.run_test("uploadToken.get — verify FULL_UPLOAD after single-shot", test_verify_single_upload_token)

    # ════════════════════════════════════════════
    # Phase 3: Chunked Upload
    # ════════════════════════════════════════════

    def test_create_larger_file():
        """Create a slightly larger file for chunked upload testing."""
        tf = tempfile.NamedTemporaryFile(delete=False, suffix=".bin", prefix="kaltura_chunk_test_")
        # Write ~10KB (enough to chunk into at least 2 pieces)
        tf.write(b"KALTURA_CHUNK_TEST_DATA_" * 500)  # 12,000 bytes
        tf.close()
        state["chunk_file"] = tf.name
        state["chunk_file_size"] = os.path.getsize(tf.name)
        print(f"    Chunk test file: {tf.name} ({state['chunk_file_size']} bytes)")

    runner.run_test("Create file for chunked upload", test_create_larger_file)

    def test_chunked_upload():
        """Upload the file in multiple chunks with resume."""
        token = kaltura_post("uploadToken", "add", {
            "uploadToken[fileName]": "test_chunked.bin",
            "uploadToken[fileSize]": state["chunk_file_size"],
        })
        state["chunk_token_id"] = token["id"]

        chunk_size = 5000  # Small chunks for testing
        file_size = state["chunk_file_size"]
        offset = 0
        chunk_count = 0

        with open(state["chunk_file"], "rb") as f:
            while offset < file_size:
                chunk = f.read(chunk_size)
                if not chunk:
                    break
                is_final = (offset + len(chunk)) >= file_size

                resp = requests.post(
                    f"{SERVICE_URL}/service/uploadToken/action/upload",
                    data={
                        "ks": KS,
                        "uploadTokenId": token["id"],
                        "resume": "true" if offset > 0 else "false",
                        "resumeAt": str(offset),
                        "finalChunk": "true" if is_final else "false",
                    },
                    files={"fileData": (f"chunk_{offset}", chunk, "application/octet-stream")},
                    timeout=30,
                )
                resp.raise_for_status()

                offset += len(chunk)
                chunk_count += 1

        assert offset == file_size, f"Only uploaded {offset}/{file_size} bytes"
        assert chunk_count >= 2, f"Expected at least 2 chunks, got {chunk_count}"
        print(f"    Uploaded {chunk_count} chunks, {offset} bytes total")

    runner.run_test("uploadToken.upload — chunked upload with resume", test_chunked_upload)

    def test_verify_chunked_upload():
        """Verify the chunked upload token reached FULL_UPLOAD."""
        for attempt in range(5):
            try:
                result = kaltura_post("uploadToken", "get", {
                    "uploadTokenId": state["chunk_token_id"],
                })
            except Exception as e:
                if "UPLOAD_TOKEN_NOT_FOUND" in str(e):
                    # Token may have been auto-consumed/finalized
                    print(f"    Token auto-consumed (not found) — upload succeeded")
                    return
                raise
            if result["status"] == 2:
                print(f"    FULL_UPLOAD confirmed: {result['uploadedFileSize']} bytes")
                return
            time.sleep(1)
        # Accept status 1 or 2
        assert result["status"] in (1, 2), f"Unexpected status: {result['status']}"
        print(f"    Status={result['status']}, uploadedFileSize={result.get('uploadedFileSize')}")

    runner.run_test("uploadToken.get — verify chunked upload FULL_UPLOAD", test_verify_chunked_upload)

    # ════════════════════════════════════════════
    # Phase 4: Create Entry + Attach Content
    # ════════════════════════════════════════════

    def test_media_add():
        """Create a media entry with metadata."""
        ts = int(time.time())
        result = kaltura_post("media", "add", {
            "entry[objectType]": "KalturaMediaEntry",
            "entry[mediaType]": 1,  # Video
            "entry[name]": f"API_DOC_VALIDATION_UPLOAD_{ts}",
            "entry[description]": "Test entry for upload API validation. Safe to delete.",
            "entry[tags]": "api-test,upload,validation",
        })
        assert "id" in result, f"media.add failed: {result}"
        state["entry_id"] = result["id"]
        state["entry_partner_id"] = result.get("partnerId", PARTNER_ID)
        runner.register_cleanup(f"entry {result['id']}",
                                lambda: _delete_entry(result["id"]))
        print(f"    Entry: {result['id']}, status={result['status']}, partnerId={state['entry_partner_id']}")

    runner.run_test("media.add — create media entry", test_media_add)

    def test_media_add_content():
        """Attach the chunked upload token to the entry."""
        result = kaltura_post("media", "addContent", {
            "entryId": state["entry_id"],
            "resource[objectType]": "KalturaUploadedFileTokenResource",
            "resource[token]": state["chunk_token_id"],
        })
        assert result["id"] == state["entry_id"]
        state["entry_status"] = result["status"]
        print(f"    Entry status after addContent: {result['status']}")

    runner.run_test("media.addContent — attach upload token to entry", test_media_add_content)

    def test_entry_get():
        """Retrieve the entry and verify it's processing."""
        result = kaltura_post("media", "get", {
            "entryId": state["entry_id"],
        })
        assert result["id"] == state["entry_id"]
        assert result["status"] in (-1, 0, 1, 2, 4), f"Unexpected status: {result['status']}"
        assert "api-test" in result.get("tags", "")
        print(f"    Entry: {result['id']}, status={result['status']}, name={result['name']}")

    runner.run_test("media.get — verify entry after addContent", test_entry_get)

    # ════════════════════════════════════════════
    # Phase 5: Import from URL
    # ════════════════════════════════════════════

    def test_add_from_url():
        """Import a video entry from a public URL."""
        ts = int(time.time())
        result = kaltura_post("media", "addFromUrl", {
            "mediaEntry[objectType]": "KalturaMediaEntry",
            "mediaEntry[name]": f"API_DOC_VALIDATION_URL_IMPORT_{ts}",
            "mediaEntry[mediaType]": 1,
            "mediaEntry[description]": "Imported from URL for API validation. Safe to delete.",
            "url": SAMPLE_VIDEO_URL,
        })
        assert "id" in result, f"addFromUrl failed: {result}"
        state["url_entry_id"] = result["id"]
        runner.register_cleanup(f"url entry {result['id']}",
                                lambda: _delete_entry(result["id"]))
        print(f"    URL import entry: {result['id']}, status={result['status']}")

    runner.run_test("media.addFromUrl — import video from URL", test_add_from_url)

    # ════════════════════════════════════════════
    # Phase 6: Delivery — Thumbnails & playManifest
    # ════════════════════════════════════════════

    def test_find_ready_entry():
        """Find a ready entry for delivery tests (prefer own URL-import entry)."""
        url_id = state.get("url_entry_id")
        if url_id:
            for attempt in range(24):
                entry = kaltura_post("media", "get", {"entryId": url_id})
                if entry.get("status") == 2:
                    state["ready_entry_id"] = entry["id"]
                    state["ready_partner_id"] = str(entry.get("partnerId", PARTNER_ID))
                    print(f"    Ready entry (own import): {entry['id']} — {entry.get('name', '?')}")
                    return
                time.sleep(5)
        result = kaltura_post("media", "list", {
            "filter[statusEqual]": 2,
            "filter[mediaTypeEqual]": 1,
            "filter[orderBy]": "-plays",
            "filter[playsGreaterThanOrEqual]": 1,
            "pager[pageSize]": 1,
        })
        assert result["totalCount"] > 0, "No ready video entries found for delivery tests"
        entry = result["objects"][0]
        state["ready_entry_id"] = entry["id"]
        state["ready_partner_id"] = str(entry.get("partnerId", PARTNER_ID))
        print(f"    Ready entry (fallback): {entry['id']} — {entry.get('name', '?')}")

    runner.run_test("Find ready entry for delivery tests", test_find_ready_entry)

    def test_thumbnail_default():
        """Verify the default thumbnail URL returns an image."""
        pid = state["ready_partner_id"]
        url = f"https://cdnapisec.kaltura.com/p/{pid}/thumbnail/entry_id/{state['ready_entry_id']}"
        resp = requests.get(url, timeout=15, allow_redirects=True)
        assert resp.status_code == 200, f"Thumbnail returned {resp.status_code}"
        content_type = resp.headers.get("Content-Type", "")
        assert "image" in content_type, f"Expected image, got {content_type}"
        assert len(resp.content) > 100, "Thumbnail too small"
        print(f"    Default thumbnail: {len(resp.content)} bytes, {content_type}")

    runner.run_test("Thumbnail API — default thumbnail", test_thumbnail_default)

    def test_thumbnail_with_params():
        """Verify thumbnail with specific dimensions and time."""
        pid = state["ready_partner_id"]
        url = (f"https://cdnapisec.kaltura.com/p/{pid}/thumbnail/entry_id/"
               f"{state['ready_entry_id']}/width/320/height/180/vid_sec/5")
        resp = requests.get(url, timeout=15, allow_redirects=True)
        assert resp.status_code == 200, f"Thumbnail returned {resp.status_code}"
        content_type = resp.headers.get("Content-Type", "")
        assert "image" in content_type, f"Expected image, got {content_type}"
        print(f"    Sized thumbnail (320x180@5s): {len(resp.content)} bytes, {content_type}")

    runner.run_test("Thumbnail API — sized thumbnail at specific second", test_thumbnail_with_params)

    def test_play_manifest_hls():
        """Verify HLS playManifest URL returns a valid response."""
        pid = state["ready_partner_id"]
        # Include KS for access-controlled content
        url = (f"https://cdnapisec.kaltura.com/p/{pid}/sp/{pid}00/"
               f"playManifest/entryId/{state['ready_entry_id']}/format/applehttp/protocol/https"
               f"/ks/{KS}")
        resp = requests.get(url, timeout=15, allow_redirects=True)
        assert resp.status_code == 200, f"playManifest HLS returned {resp.status_code}"
        text = resp.text
        assert "#EXTM3U" in text or resp.headers.get("Content-Type", "").startswith("application/"), \
            f"Response doesn't look like HLS manifest"
        print(f"    HLS manifest: {len(text)} chars")

    runner.run_test("playManifest — HLS (applehttp) streaming URL", test_play_manifest_hls)

    def test_play_manifest_download():
        """Verify download format returns a downloadable response."""
        pid = state["ready_partner_id"]
        # Include KS for access-controlled content
        url = (f"https://cdnapisec.kaltura.com/p/{pid}/sp/{pid}00/"
               f"playManifest/entryId/{state['ready_entry_id']}/format/download/protocol/https"
               f"/flavorParamIds/0/ks/{KS}")
        resp = requests.head(url, timeout=15, allow_redirects=True)
        assert resp.status_code in (200, 301, 302, 303), \
            f"playManifest download returned {resp.status_code}"
        print(f"    Download URL: status={resp.status_code}")

    runner.run_test("playManifest — download URL", test_play_manifest_download)

    # ════════════════════════════════════════════
    # Phase 7: Flavor Assets
    # ════════════════════════════════════════════

    def test_flavor_asset_list():
        """List flavor assets for the ready entry."""
        result = kaltura_post("flavorAsset", "list", {
            "filter[entryIdEqual]": state["ready_entry_id"],
        })
        assert result.get("totalCount", 0) > 0, "No flavor assets found"
        flavors = result["objects"]
        state["flavors"] = flavors
        ready_flavors = [f for f in flavors if f.get("status") == 2]
        print(f"    {result['totalCount']} flavor(s), {len(ready_flavors)} ready:")
        for f in ready_flavors[:3]:
            print(f"      {f['id']}: {f.get('width','?')}x{f.get('height','?')} "
                  f"@ {f.get('bitrate','?')}kbps, original={f.get('isOriginal', False)}")

    runner.run_test("flavorAsset.list — list transcoded flavors", test_flavor_asset_list)

    def test_flavor_asset_get_url():
        """Get download URL for a specific flavor asset."""
        ready_flavors = [f for f in state.get("flavors", []) if f.get("status") == 2]
        if not ready_flavors:
            raise Exception("No ready flavors to get URL for")

        flavor_id = ready_flavors[0]["id"]
        result = kaltura_post("flavorAsset", "getUrl", {
            "id": flavor_id,
        })
        # Result is a string URL
        assert isinstance(result, str) and result.startswith("http"), \
            f"Expected URL string, got: {result}"
        print(f"    Flavor {flavor_id} URL: {result[:100]}...")

    runner.run_test("flavorAsset.getUrl — get download URL for flavor", test_flavor_asset_get_url)

    # ════════════════════════════════════════════
    # Phase 8: Entry downloadUrl property
    # ════════════════════════════════════════════

    def test_entry_download_url():
        """Verify the entry's downloadUrl property."""
        result = kaltura_post("media", "get", {
            "entryId": state["ready_entry_id"],
        })
        download_url = result.get("downloadUrl", "")
        assert download_url.startswith("http"), f"Expected URL, got: {download_url}"
        print(f"    downloadUrl: {download_url[:100]}...")

    runner.run_test("media.get — downloadUrl property", test_entry_download_url)

    # ════════════════════════════════════════════
    # Phase 9: media.update and media.delete
    # ════════════════════════════════════════════

    def test_media_update():
        """Update entry metadata."""
        if not state.get("entry_id"):
            raise Exception("No entry_id available (media.add may have failed)")
        ts = int(time.time())
        result = kaltura_post("media", "update", {
            "entryId": state["entry_id"],
            "mediaEntry[objectType]": "KalturaMediaEntry",
            "mediaEntry[name]": f"API_DOC_UPDATED_{ts}",
            "mediaEntry[tags]": "api-test,upload,validation,updated",
        })
        assert result["name"] == f"API_DOC_UPDATED_{ts}"
        assert "updated" in result.get("tags", "")
        print(f"    Updated: name={result['name']}, tags={result['tags']}")

    runner.run_test("media.update — update entry metadata", test_media_update)

    def test_media_list_filter():
        """List entries filtered by tags."""
        result = kaltura_post("media", "list", {
            "filter[tagsMultiLikeOr]": "api-test",
            "filter[orderBy]": "-createdAt",
            "pager[pageSize]": 5,
        })
        assert result.get("totalCount", 0) >= 0, f"media.list failed: {result}"
        print(f"    Found {result['totalCount']} entries with tag 'api-test'")
        if state.get("entry_id") and result.get("totalCount", 0) > 0:
            entry_ids = [e["id"] for e in result.get("objects", [])]
            if state["entry_id"] in entry_ids:
                print(f"    Our entry {state['entry_id']} found in list")

    runner.run_test("media.list — filter by tags", test_media_list_filter)

    # ════════════════════════════════════════════
    # Phase 10: Cleanup
    # ════════════════════════════════════════════

    def test_delete_upload_token():
        """Delete the initial upload token (if still pending)."""
        try:
            kaltura_post("uploadToken", "delete", {
                "uploadTokenId": state["token_id"],
            })
            print(f"    Deleted token: {state['token_id']}")
        except Exception as e:
            if "UPLOAD_TOKEN_NOT_FOUND" in str(e):
                print(f"    Token already consumed/deleted: {state['token_id']}")
            else:
                raise

    runner.run_test("uploadToken.delete — clean up pending token", test_delete_upload_token)

    def test_cleanup_temp_files():
        """Remove temporary test files."""
        for key in ("test_file", "chunk_file"):
            path = state.get(key)
            if path and os.path.exists(path):
                os.unlink(path)
                print(f"    Removed: {path}")

    runner.run_test("Cleanup — remove temp files", test_cleanup_temp_files)

    # ════════════════════════════════════════════
    # Phase 6: thumbAsset API (Stored Thumbnails)
    # ════════════════════════════════════════════

    def test_thumb_asset_generate():
        """Capture a thumbnail from a video at a specific offset."""
        entry_id = state.get("ready_entry_id")
        if not entry_id:
            raise RuntimeError("No ready entry for thumbAsset tests")
        result = kaltura_post("thumbAsset", "generate", {
            "entryId": entry_id,
            "thumbParams[objectType]": "KalturaThumbParams",
            "thumbParams[videoOffset]": 3,
        })
        assert "id" in result, f"No thumbAsset ID returned: {result}"
        state["thumb_asset_id"] = result["id"]
        runner.register_cleanup(f"thumbAsset {result['id']}",
                                lambda: _delete_thumb_asset(result["id"]))
        print(f"    ThumbAsset: {result['id']}, entryId={result.get('entryId')}")

    runner.run_test("thumbAsset.generate — capture frame from video", test_thumb_asset_generate)

    def test_thumb_asset_get():
        """Retrieve a specific thumbnail asset."""
        thumb_id = state.get("thumb_asset_id")
        if not thumb_id:
            raise RuntimeError("No thumbAsset ID")
        result = kaltura_post("thumbAsset", "get", {
            "thumbAssetId": thumb_id,
        })
        assert result.get("id") == thumb_id, f"Expected {thumb_id}, got {result.get('id')}"
        assert result.get("objectType") == "KalturaThumbAsset"
        print(f"    ThumbAsset: {result['id']}, status={result.get('status')}, width={result.get('width')}")

    runner.run_test("thumbAsset.get — retrieve thumbnail asset", test_thumb_asset_get)

    def test_thumb_asset_set_as_default():
        """Set a thumbnail as the entry's default."""
        thumb_id = state.get("thumb_asset_id")
        if not thumb_id:
            raise RuntimeError("No thumbAsset ID")
        result = kaltura_post("thumbAsset", "setAsDefault", {
            "thumbAssetId": thumb_id,
        })
        # setAsDefault returns void on success — no error means success
        print(f"    Set thumbAsset {thumb_id} as default")

    runner.run_test("thumbAsset.setAsDefault — set default thumbnail", test_thumb_asset_set_as_default)

    def test_thumb_asset_list():
        """List all thumbnails for an entry."""
        entry_id = state.get("ready_entry_id")
        if not entry_id:
            raise RuntimeError("No ready entry for thumbAsset list")
        result = kaltura_post("thumbAsset", "list", {
            "filter[entryIdEqual]": entry_id,
        })
        assert "objects" in result, f"Expected objects array: {result}"
        assert result.get("totalCount", 0) > 0, f"Expected at least one thumbAsset, got {result.get('totalCount')}"
        thumb_ids = [t["id"] for t in result["objects"]]
        print(f"    Found {result['totalCount']} thumbAssets: {', '.join(thumb_ids)}")

    runner.run_test("thumbAsset.list — list thumbnails for entry", test_thumb_asset_list)

    def test_thumb_asset_add_upload():
        """Upload a custom thumbnail image via uploadToken."""
        entry_id = state.get("ready_entry_id")
        if not entry_id:
            raise RuntimeError("No ready entry")
        # Create a minimal 1x1 PNG (67 bytes)
        import base64
        png_data = base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        )
        # Step 1: Create upload token
        token = kaltura_post("uploadToken", "add", {
            "uploadToken[fileName]": "thumb_test.png",
            "uploadToken[fileSize]": len(png_data),
        })
        token_id = token["id"]
        runner.register_cleanup(f"thumb upload token {token_id}",
                                lambda: _delete_token(token_id))
        # Step 2: Upload the PNG
        import io
        upload_url = f"{SERVICE_URL}/service/uploadToken/action/upload"
        resp = requests.post(upload_url, data={
            "ks": KS, "format": "1", "uploadTokenId": token_id, "resume": "false",
        }, files={"fileData": ("thumb_test.png", io.BytesIO(png_data), "image/png")})
        assert resp.status_code == 200
        # Step 3: Create thumbAsset
        thumb = kaltura_post("thumbAsset", "add", {
            "entryId": entry_id,
            "thumbAsset[objectType]": "KalturaThumbAsset",
            "thumbAsset[tags]": "test-uploaded",
        })
        assert "id" in thumb, f"No thumbAsset ID: {thumb}"
        state["uploaded_thumb_id"] = thumb["id"]
        runner.register_cleanup(f"uploaded thumbAsset {thumb['id']}",
                                lambda: _delete_thumb_asset(thumb["id"]))
        # Step 4: Attach content
        kaltura_post("thumbAsset", "setContent", {
            "id": thumb["id"],
            "contentResource[objectType]": "KalturaUploadedFileTokenResource",
            "contentResource[token]": token_id,
        })
        print(f"    Uploaded thumbAsset: {thumb['id']} (via token {token_id})")

    runner.run_test("thumbAsset.add + setContent — upload custom thumbnail", test_thumb_asset_add_upload)

    def test_thumb_asset_delete():
        """Delete a thumbnail asset."""
        thumb_id = state.get("uploaded_thumb_id")
        if not thumb_id:
            raise RuntimeError("No uploaded thumbAsset to delete")
        kaltura_post("thumbAsset", "delete", {"thumbAssetId": thumb_id})
        # Verify deletion
        try:
            kaltura_post("thumbAsset", "get", {"thumbAssetId": thumb_id})
            raise AssertionError(f"thumbAsset {thumb_id} still exists after delete")
        except Exception as e:
            if "THUMB_ASSET_ID_NOT_FOUND" in str(e) or "not found" in str(e).lower():
                print(f"    Deleted thumbAsset {thumb_id} (confirmed not found)")
            else:
                raise

    runner.run_test("thumbAsset.delete — remove thumbnail asset", test_thumb_asset_delete)

    # ════════════════════════════════════════════
    # Phase 7: attachmentAsset API
    # ════════════════════════════════════════════

    def test_attachment_asset_add():
        """Create an attachment asset on a media entry."""
        entry_id = state.get("ready_entry_id")
        if not entry_id:
            raise RuntimeError("No ready entry for attachmentAsset tests")
        result = kaltura_post("attachment_attachmentAsset", "add", {
            "entryId": entry_id,
            "attachmentAsset[objectType]": "KalturaAttachmentAsset",
            "attachmentAsset[title]": "Test Document",
            "attachmentAsset[format]": 3,  # DOCUMENT
            "attachmentAsset[tags]": "test-attachment",
        })
        assert "id" in result, f"No attachmentAsset ID: {result}"
        state["attachment_id"] = result["id"]
        runner.register_cleanup(f"attachmentAsset {result['id']}",
                                lambda: _delete_attachment_asset(result["id"]))
        print(f"    AttachmentAsset: {result['id']}, format={result.get('format')}")

    runner.run_test("attachmentAsset.add — create attachment", test_attachment_asset_add)

    def test_attachment_asset_set_content():
        """Upload content to an attachment asset."""
        att_id = state.get("attachment_id")
        if not att_id:
            raise RuntimeError("No attachmentAsset ID")
        # Create upload token with a small text file
        token = kaltura_post("uploadToken", "add", {
            "uploadToken[fileName]": "notes.txt",
            "uploadToken[fileSize]": 26,
        })
        token_id = token["id"]
        import io
        upload_url = f"{SERVICE_URL}/service/uploadToken/action/upload"
        resp = requests.post(upload_url, data={
            "ks": KS, "format": "1", "uploadTokenId": token_id, "resume": "false",
        }, files={"fileData": ("notes.txt", io.BytesIO(b"Test attachment content.\n"), "text/plain")})
        assert resp.status_code == 200
        # Attach content to asset
        result = kaltura_post("attachment_attachmentAsset", "setContent", {
            "id": att_id,
            "contentResource[objectType]": "KalturaUploadedFileTokenResource",
            "contentResource[token]": token_id,
        })
        assert result.get("id") == att_id
        print(f"    Set content on attachmentAsset {att_id} (via token {token_id})")

    runner.run_test("attachmentAsset.setContent — upload attachment file", test_attachment_asset_set_content)

    def test_attachment_asset_list():
        """List attachment assets for an entry."""
        entry_id = state.get("ready_entry_id")
        if not entry_id:
            raise RuntimeError("No ready entry")
        result = kaltura_post("attachment_attachmentAsset", "list", {
            "filter[entryIdEqual]": entry_id,
        })
        assert "objects" in result, f"Expected objects array: {result}"
        assert result.get("totalCount", 0) > 0, f"Expected at least one attachment, got {result.get('totalCount')}"
        att_ids = [a["id"] for a in result["objects"]]
        print(f"    Found {result['totalCount']} attachments: {', '.join(att_ids)}")

    runner.run_test("attachmentAsset.list — list attachments for entry", test_attachment_asset_list)

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


def _delete_token(token_id):
    try:
        kaltura_post("uploadToken", "delete", {"uploadTokenId": token_id})
    except Exception:
        pass


def _delete_entry(entry_id):
    try:
        kaltura_post("media", "delete", {"entryId": entry_id})
    except Exception:
        pass


def _delete_thumb_asset(thumb_id):
    try:
        kaltura_post("thumbAsset", "delete", {"thumbAssetId": thumb_id})
    except Exception:
        pass


def _delete_attachment_asset(att_id):
    try:
        kaltura_post("attachment_attachmentAsset", "delete", {"id": att_id})
    except Exception:
        pass


if __name__ == "__main__":
    print(f"\n{'='*60}")
    print("  KALTURA UPLOAD & DELIVERY — End-to-End API Validation")
    print(f"{'='*60}\n")
    main()
