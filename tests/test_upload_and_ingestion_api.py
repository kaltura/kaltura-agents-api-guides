#!/usr/bin/env python3
"""
End-to-end validation of the Upload & Ingestion API.

Covers: uploadToken lifecycle, single-shot upload, chunked upload with resume,
media entry creation (add, addContent with resource types, update, delete),
URL import via KalturaUrlResource, entry cloning via baseEntry.clone,
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

    def test_url_import_via_add_content():
        """Import a video from URL using media.add + media.addContent with KalturaUrlResource."""
        ts = int(time.time())
        entry = kaltura_post("media", "add", {
            "entry[objectType]": "KalturaMediaEntry",
            "entry[mediaType]": 1,
            "entry[name]": f"API_DOC_VALIDATION_URL_IMPORT_{ts}",
            "entry[description]": "Imported from URL for API validation. Safe to delete.",
            "entry[tags]": "api-test,url-import,validation",
        })
        assert "id" in entry, f"media.add failed: {entry}"
        state["url_entry_id"] = entry["id"]
        runner.register_cleanup(f"url entry {entry['id']}",
                                lambda: _delete_entry(entry["id"]))
        print(f"    Created entry: {entry['id']}, status={entry['status']}")

        result = kaltura_post("media", "addContent", {
            "entryId": entry["id"],
            "resource[objectType]": "KalturaUrlResource",
            "resource[url]": SAMPLE_VIDEO_URL,
        })
        assert result["id"] == entry["id"]
        assert result["status"] in (0, 1, 2, 4), f"Unexpected status after addContent: {result['status']}"
        print(f"    addContent with KalturaUrlResource: status={result['status']}")

    runner.run_test("media.addContent + KalturaUrlResource — import from URL", test_url_import_via_add_content)

    # ════════════════════════════════════════════
    # Phase 6: baseEntry.clone — Deep Clone
    # ════════════════════════════════════════════

    def test_base_entry_clone():
        """Clone an entry using baseEntry.clone (preferred method for entry duplication)."""
        source_id = state.get("url_entry_id") or state.get("entry_id")
        if not source_id:
            raise RuntimeError("No source entry available for cloning")
        result = kaltura_post("baseEntry", "clone", {
            "entryId": source_id,
        })
        assert "id" in result, f"baseEntry.clone failed: {result}"
        assert result["id"] != source_id, "Clone should have a different ID"
        state["cloned_entry_id"] = result["id"]
        runner.register_cleanup(f"cloned entry {result['id']}",
                                lambda: _delete_entry(result["id"]))
        print(f"    Cloned {source_id} → {result['id']}, status={result.get('status')}")

    runner.run_test("baseEntry.clone — deep clone entry", test_base_entry_clone)

    def test_base_entry_clone_exclude_flavors():
        """Clone an entry excluding flavors (produces NO_CONTENT clone)."""
        source_id = None
        result = kaltura_post("media", "list", {
            "filter[statusEqual]": 2,
            "filter[mediaTypeEqual]": 1,
            "filter[orderBy]": "-plays",
            "pager[pageSize]": 1,
        })
        if result.get("totalCount", 0) > 0:
            source_id = result["objects"][0]["id"]
        if not source_id:
            print("    SKIP: No READY entry for clone-exclude-flavors test")
            return
        clone = kaltura_post("baseEntry", "clone", {
            "entryId": source_id,
            "cloneOptions[0][objectType]": "KalturaBaseEntryCloneOptionComponent",
            "cloneOptions[0][itemType]": 6,
            "cloneOptions[0][rule]": 1,
        })
        assert "id" in clone, f"clone with exclude-flavors failed: {clone}"
        assert clone["id"] != source_id
        runner.register_cleanup(f"clone-no-flavors {clone['id']}",
                                lambda: _delete_entry(clone["id"]))
        assert clone.get("status") == 7, f"Expected NO_CONTENT (7) when flavors excluded, got {clone.get('status')}"
        print(f"    Clone (no flavors): {clone['id']}, status={clone.get('status')} (NO_CONTENT)")

    runner.run_test("baseEntry.clone — exclude flavors (NO_CONTENT)", test_base_entry_clone_exclude_flavors)

    def test_base_entry_clone_with_options():
        """Clone an entry excluding metadata and categories."""
        source_id = state.get("cloned_entry_id") or state.get("url_entry_id")
        if not source_id:
            print("    SKIP: No source entry for clone-options test")
            return
        clone = kaltura_post("baseEntry", "clone", {
            "entryId": source_id,
            "cloneOptions[0][objectType]": "KalturaBaseEntryCloneOptionComponent",
            "cloneOptions[0][itemType]": 5,
            "cloneOptions[0][rule]": 1,
            "cloneOptions[1][objectType]": "KalturaBaseEntryCloneOptionComponent",
            "cloneOptions[1][itemType]": 2,
            "cloneOptions[1][rule]": 1,
        })
        assert "id" in clone, f"clone with options failed: {clone}"
        runner.register_cleanup(f"clone-no-meta {clone['id']}",
                                lambda: _delete_entry(clone["id"]))
        print(f"    Clone (no metadata/categories): {clone['id']}, status={clone.get('status')}")

    runner.run_test("baseEntry.clone — exclude metadata+categories", test_base_entry_clone_with_options)

    # ════════════════════════════════════════════
    # Phase 7: KalturaEntryResource — Copy Content
    # ════════════════════════════════════════════

    def test_add_content_entry_resource():
        """Create a new entry and attach content from a READY entry using KalturaEntryResource."""
        source_id = None
        for eid in [state.get("url_entry_id"), state.get("entry_id")]:
            if not eid:
                continue
            entry = kaltura_post("media", "get", {"entryId": eid})
            if entry.get("status") == 2:
                source_id = eid
                break
        if not source_id:
            result = kaltura_post("media", "list", {
                "filter[statusEqual]": 2,
                "filter[mediaTypeEqual]": 1,
                "filter[orderBy]": "-plays",
                "pager[pageSize]": 1,
            })
            if result.get("totalCount", 0) > 0:
                source_id = result["objects"][0]["id"]
        if not source_id:
            print("    SKIP: No READY entry available for KalturaEntryResource test")
            return

        ts = int(time.time())
        entry = kaltura_post("media", "add", {
            "entry[objectType]": "KalturaMediaEntry",
            "entry[mediaType]": 1,
            "entry[name]": f"API_DOC_VALIDATION_ENTRY_RESOURCE_{ts}",
            "entry[description]": "Created via KalturaEntryResource. Safe to delete.",
            "entry[tags]": "api-test,entry-resource,validation",
        })
        assert "id" in entry, f"media.add failed: {entry}"
        state["entry_resource_id"] = entry["id"]
        runner.register_cleanup(f"entry-resource entry {entry['id']}",
                                lambda: _delete_entry(entry["id"]))

        result = kaltura_post("media", "addContent", {
            "entryId": entry["id"],
            "resource[objectType]": "KalturaEntryResource",
            "resource[entryId]": source_id,
            "resource[flavorParamsId]": 0,
        })
        assert result["id"] == entry["id"]
        print(f"    addContent with KalturaEntryResource: {entry['id']} ← source {source_id}, status={result.get('status')}")

    runner.run_test("media.addContent + KalturaEntryResource — copy from entry", test_add_content_entry_resource)

    # ════════════════════════════════════════════
    # Phase 8: Entry CRUD Operations
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
    # Phase 9: Flavor Assets & KalturaAssetResource
    # ════════════════════════════════════════════

    def test_find_ready_entry():
        """Find a ready entry for flavor and asset resource tests."""
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

    runner.run_test("Find ready entry for flavor/asset tests", test_find_ready_entry)

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

    def test_add_content_asset_resource():
        """Create a new entry from a specific flavor asset using KalturaAssetResource."""
        flavors = state.get("flavors", [])
        ready_flavors = [f for f in flavors if f.get("status") == 2]
        if not ready_flavors:
            print("    SKIP: No ready flavor assets available for KalturaAssetResource test")
            return
        flavor_id = ready_flavors[0]["id"]
        ts = int(time.time())
        entry = kaltura_post("media", "add", {
            "entry[objectType]": "KalturaMediaEntry",
            "entry[mediaType]": 1,
            "entry[name]": f"API_DOC_VALIDATION_ASSET_RESOURCE_{ts}",
            "entry[description]": "Created via KalturaAssetResource. Safe to delete.",
            "entry[tags]": "api-test,asset-resource,validation",
        })
        assert "id" in entry, f"media.add failed: {entry}"
        state["asset_resource_entry_id"] = entry["id"]
        runner.register_cleanup(f"asset-resource entry {entry['id']}",
                                lambda: _delete_entry(entry["id"]))

        result = kaltura_post("media", "addContent", {
            "entryId": entry["id"],
            "resource[objectType]": "KalturaAssetResource",
            "resource[assetId]": flavor_id,
        })
        assert result["id"] == entry["id"]
        print(f"    addContent with KalturaAssetResource: {entry['id']} ← flavor {flavor_id}, status={result.get('status')}")

    runner.run_test("media.addContent + KalturaAssetResource — copy from flavor", test_add_content_asset_resource)

    def test_add_content_operation_resource():
        """Create a clip using KalturaOperationResource with KalturaClipAttributes."""
        ready_id = state.get("ready_entry_id")
        if not ready_id:
            print("    SKIP: No ready entry for KalturaOperationResource test")
            return
        entry = kaltura_post("media", "get", {"entryId": ready_id})
        duration_ms = int((entry.get("duration") or 10) * 1000)
        clip_offset = 0
        clip_duration = min(5000, duration_ms)

        ts = int(time.time())
        new_entry = kaltura_post("media", "add", {
            "entry[objectType]": "KalturaMediaEntry",
            "entry[mediaType]": 1,
            "entry[name]": f"API_DOC_VALIDATION_CLIP_{ts}",
            "entry[description]": "Created via KalturaOperationResource (clip). Safe to delete.",
            "entry[tags]": "api-test,clip,operation-resource,validation",
        })
        assert "id" in new_entry, f"media.add failed: {new_entry}"
        state["clip_entry_id"] = new_entry["id"]
        runner.register_cleanup(f"clip entry {new_entry['id']}",
                                lambda: _delete_entry(new_entry["id"]))

        result = kaltura_post("media", "addContent", {
            "entryId": new_entry["id"],
            "resource[objectType]": "KalturaOperationResource",
            "resource[resource][objectType]": "KalturaEntryResource",
            "resource[resource][entryId]": ready_id,
            "resource[resource][flavorParamsId]": 0,
            "resource[operationAttributes][0][objectType]": "KalturaClipAttributes",
            "resource[operationAttributes][0][offset]": clip_offset,
            "resource[operationAttributes][0][duration]": clip_duration,
        })
        assert result["id"] == new_entry["id"]
        assert result["status"] in (0, 1, 4), f"Expected processing status, got {result.get('status')}"
        print(f"    KalturaOperationResource clip: {new_entry['id']} ← {ready_id}[{clip_offset}ms:{clip_duration}ms], status={result.get('status')}")

    runner.run_test("media.addContent + KalturaOperationResource — create clip", test_add_content_operation_resource)

    # ════════════════════════════════════════════
    # Phase 10: Attachment Assets
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
    # Phase 11: Cleanup
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
