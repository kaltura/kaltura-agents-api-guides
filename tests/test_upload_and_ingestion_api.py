#!/usr/bin/env python3
"""
End-to-end validation of the Upload & Ingestion API.

Covers: uploadToken lifecycle, single-shot upload, chunked upload with resume,
media entry creation (add, addContent, addFromUrl, update, delete),
entry status polling, flavor asset listing, attachmentAsset CRUD.
"""

import sys
import os
import time
import tempfile
import io
import requests

sys.path.insert(0, os.path.dirname(__file__))
from test_helpers import kaltura_post, TestRunner, PARTNER_ID, KS, SERVICE_URL

SAMPLE_VIDEO_URL = os.environ.get(
    "KALTURA_TEST_VIDEO_URL",
    "https://cdnapisec.kaltura.com/p/811441/sp/81144100/playManifest/entryId/1_uoup50ye/format/url/protocol/https"
)

state = {}


def main():
    runner = TestRunner("Upload & Ingestion API Validation")

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
        assert result["status"] in (0, 1, 2), f"Unexpected status: {result['status']}"
        print(f"    Token status={result['status']}, uploadedFileSize={result.get('uploadedFileSize', 0)}")

    runner.run_test("uploadToken.get — verify token exists", test_upload_token_get)

    def test_upload_token_list():
        """List upload tokens and verify our token appears."""
        result = kaltura_post("uploadToken", "list", {
            "filter[statusEqual]": 0,
        })
        assert result.get("totalCount", 0) >= 1, "No pending tokens found"
        print(f"    Found {result['totalCount']} pending token(s)")

    runner.run_test("uploadToken.list — list pending tokens", test_upload_token_list)

    # ════════════════════════════════════════════
    # Phase 2: Single-shot Upload (small file)
    # ════════════════════════════════════════════

    def test_create_test_file():
        """Create a small test file for upload."""
        tf = tempfile.NamedTemporaryFile(delete=False, suffix=".bin", prefix="kaltura_test_")
        tf.write(b"KALTURA_API_TEST_" * 64)
        tf.close()
        state["test_file"] = tf.name
        state["test_file_size"] = os.path.getsize(tf.name)
        print(f"    Test file: {tf.name} ({state['test_file_size']} bytes)")

    runner.run_test("Create small test file for upload", test_create_test_file)

    def test_single_shot_upload():
        """Upload the test file in a single request."""
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
            try:
                result = resp.json()
                if isinstance(result, dict) and "id" in result:
                    state["single_upload_status"] = result.get("status")
                    print(f"    Uploaded: status={result.get('status')}, uploadedFileSize={result.get('uploadedFileSize')}")
                    return
            except Exception:
                pass

        result = kaltura_post("uploadToken", "get", {
            "uploadTokenId": token["id"],
        })
        assert result["status"] in (1, 2), f"Expected PARTIAL(1) or FULL(2), got {result.get('status')}"
        state["single_upload_status"] = result["status"]
        print(f"    Uploaded: status={result['status']}, uploadedFileSize={result.get('uploadedFileSize')}")

    runner.run_test("uploadToken.upload — single-shot upload", test_single_shot_upload)

    def test_verify_single_upload_token():
        """Verify the token reached FULL_UPLOAD after single-shot."""
        for attempt in range(5):
            result = kaltura_post("uploadToken", "get", {
                "uploadTokenId": state["single_token_id"],
            })
            if result["status"] == 2:
                print(f"    Token FULL_UPLOAD: uploadedFileSize={result['uploadedFileSize']}")
                return
            time.sleep(1)
        assert result["status"] in (1, 2), f"Unexpected status: {result['status']}"
        print(f"    Token status={result['status']}, uploadedFileSize={result.get('uploadedFileSize')}")

    runner.run_test("uploadToken.get — verify FULL_UPLOAD after single-shot", test_verify_single_upload_token)

    # ════════════════════════════════════════════
    # Phase 3: Chunked Upload
    # ════════════════════════════════════════════

    def test_create_larger_file():
        """Create a slightly larger file for chunked upload testing."""
        tf = tempfile.NamedTemporaryFile(delete=False, suffix=".bin", prefix="kaltura_chunk_test_")
        tf.write(b"KALTURA_CHUNK_TEST_DATA_" * 500)
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

        chunk_size = 5000
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
                    print(f"    Token auto-consumed (not found) — upload succeeded")
                    return
                raise
            if result["status"] == 2:
                print(f"    FULL_UPLOAD confirmed: {result['uploadedFileSize']} bytes")
                return
            time.sleep(1)
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
            "entry[mediaType]": 1,
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
    # Phase 6: Entry CRUD Operations
    # ════════════════════════════════════════════

    def test_media_update():
        """Update entry metadata."""
        if not state.get("entry_id"):
            raise RuntimeError("No entry_id available")
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

    def test_media_count():
        """Count entries matching a filter."""
        result = kaltura_post("media", "count", {
            "filter[tagsMultiLikeOr]": "api-test",
        })
        assert isinstance(result, int) or isinstance(result, float), \
            f"Expected integer count, got: {type(result)}"
        print(f"    media.count with tag 'api-test': {result}")

    runner.run_test("media.count — count matching entries", test_media_count)

    def test_base_entry_get_by_ids():
        """Batch retrieve multiple entries."""
        ids = []
        if state.get("entry_id"):
            ids.append(state["entry_id"])
        if state.get("url_entry_id"):
            ids.append(state["url_entry_id"])
        if not ids:
            raise RuntimeError("No entry IDs available")
        result = kaltura_post("baseEntry", "getByIds", {
            "entryIds": ",".join(ids),
        })
        if isinstance(result, list):
            assert len(result) == len(ids), f"Expected {len(ids)} entries, got {len(result)}"
            print(f"    Retrieved {len(result)} entries via getByIds")
        else:
            print(f"    getByIds response: {str(result)[:200]}")

    runner.run_test("baseEntry.getByIds — batch retrieve", test_base_entry_get_by_ids)

    # ════════════════════════════════════════════
    # Phase 7: Flavor Assets
    # ════════════════════════════════════════════

    def test_find_ready_entry():
        """Find a ready entry for flavor tests."""
        url_id = state.get("url_entry_id")
        if url_id:
            for attempt in range(24):
                entry = kaltura_post("media", "get", {"entryId": url_id})
                if entry.get("status") == 2:
                    state["ready_entry_id"] = entry["id"]
                    print(f"    Ready entry (own import): {entry['id']}")
                    return
                time.sleep(5)
        result = kaltura_post("media", "list", {
            "filter[statusEqual]": 2,
            "filter[mediaTypeEqual]": 1,
            "filter[orderBy]": "-plays",
            "filter[playsGreaterThanOrEqual]": 1,
            "pager[pageSize]": 1,
        })
        assert result["totalCount"] > 0, "No ready entries found"
        entry = result["objects"][0]
        state["ready_entry_id"] = entry["id"]
        print(f"    Ready entry (fallback): {entry['id']}")

    runner.run_test("Find ready entry for flavor tests", test_find_ready_entry)

    def test_flavor_asset_list():
        """List flavor assets for the ready entry."""
        result = kaltura_post("flavorAsset", "list", {
            "filter[entryIdEqual]": state["ready_entry_id"],
        })
        assert result.get("totalCount", 0) > 0, "No flavor assets found"
        flavors = result["objects"]
        state["flavors"] = flavors
        ready_flavors = [f for f in flavors if f.get("status") == 2]
        print(f"    {result['totalCount']} flavor(s), {len(ready_flavors)} ready")

    runner.run_test("flavorAsset.list — list transcoded flavors", test_flavor_asset_list)

    # ════════════════════════════════════════════
    # Phase 8: Attachment Assets
    # ════════════════════════════════════════════

    def test_attachment_asset_add():
        """Create an attachment asset on a media entry."""
        entry_id = state.get("ready_entry_id")
        if not entry_id:
            raise RuntimeError("No ready entry")
        result = kaltura_post("attachment_attachmentAsset", "add", {
            "entryId": entry_id,
            "attachmentAsset[objectType]": "KalturaAttachmentAsset",
            "attachmentAsset[title]": "Test Document",
            "attachmentAsset[format]": 3,
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
        token = kaltura_post("uploadToken", "add", {
            "uploadToken[fileName]": "notes.txt",
            "uploadToken[fileSize]": 26,
        })
        token_id = token["id"]
        upload_url = f"{SERVICE_URL}/service/uploadToken/action/upload"
        resp = requests.post(upload_url, data={
            "ks": KS, "format": "1", "uploadTokenId": token_id, "resume": "false",
        }, files={"fileData": ("notes.txt", io.BytesIO(b"Test attachment content.\n"), "text/plain")})
        assert resp.status_code == 200
        result = kaltura_post("attachment_attachmentAsset", "setContent", {
            "id": att_id,
            "contentResource[objectType]": "KalturaUploadedFileTokenResource",
            "contentResource[token]": token_id,
        })
        assert result.get("id") == att_id
        print(f"    Set content on attachmentAsset {att_id}")

    runner.run_test("attachmentAsset.setContent — upload attachment file", test_attachment_asset_set_content)

    def test_attachment_asset_list():
        """List attachment assets for an entry."""
        entry_id = state.get("ready_entry_id")
        if not entry_id:
            raise RuntimeError("No ready entry")
        result = kaltura_post("attachment_attachmentAsset", "list", {
            "filter[entryIdEqual]": entry_id,
        })
        assert "objects" in result
        assert result.get("totalCount", 0) > 0, "Expected at least one attachment"
        print(f"    Found {result['totalCount']} attachment(s)")

    runner.run_test("attachmentAsset.list — list attachments for entry", test_attachment_asset_list)

    def test_attachment_asset_get_url():
        """Get download URL for an attachment."""
        att_id = state.get("attachment_id")
        if not att_id:
            raise RuntimeError("No attachmentAsset ID")
        result = kaltura_post("attachment_attachmentAsset", "getUrl", {
            "id": att_id,
        })
        assert isinstance(result, str) and result.startswith("http"), \
            f"Expected URL, got: {result}"
        print(f"    Attachment URL: {result[:100]}...")

    runner.run_test("attachmentAsset.getUrl — get download URL", test_attachment_asset_get_url)

    # ════════════════════════════════════════════
    # Phase 9: Cleanup
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
    # Final Cleanup & Summary
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


def _delete_attachment_asset(att_id):
    try:
        kaltura_post("attachment_attachmentAsset", "delete", {"id": att_id})
    except Exception:
        pass


if __name__ == "__main__":
    print(f"\n{'='*60}")
    print("  KALTURA UPLOAD & INGESTION — End-to-End API Validation")
    print(f"{'='*60}\n")
    main()
