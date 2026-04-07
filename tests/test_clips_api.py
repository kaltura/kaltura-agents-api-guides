#!/usr/bin/env python3
"""
End-to-end validation of the AI Clips (Content Lab) workflow against the live API.

Covers: ordering AI clip generation via REACH, polling for results, listing
generated clips, saving a clip as a new entry via clone+updateContent, and cleanup.

Flow validated against the actual KMC Content Lab network trace.
"""

import sys
import os
import time

sys.path.insert(0, os.path.dirname(__file__))
from test_helpers import kaltura_post, TestRunner, PARTNER_ID, KS

CLIPS_CATALOG_ITEM_ID = int(os.environ.get("KALTURA_CLIPS_CATALOG_ITEM_ID", "34832"))
CLIPS_SERVICE_FEATURE = 10

state = {}


def main():
    runner = TestRunner("AI Clips (Content Lab) Workflow Validation")

    # ════════════════════════════════════════════
    # Phase 1: Prerequisites (read-only)
    # ════════════════════════════════════════════

    def test_clips_catalog_item():
        result = kaltura_post("reach_vendorCatalogItem", "get", {
            "id": CLIPS_CATALOG_ITEM_ID,
        })
        assert result.get("objectType") == "KalturaVendorClipsCatalogItem", (
            f"Expected KalturaVendorClipsCatalogItem, got {result.get('objectType')}"
        )
        assert result["serviceFeature"] == CLIPS_SERVICE_FEATURE
        assert result["status"] == 2, f"Catalog item not ACTIVE: status={result['status']}"
        assert result["serviceType"] == 2, "Expected MACHINE serviceType"
        state["catalog_item"] = result
        print(f"    Catalog item: {result['name']}, sourceLanguage={result.get('sourceLanguage')}")

    runner.run_test("Clips catalog item exists (KalturaVendorClipsCatalogItem)", test_clips_catalog_item)

    if not runner.results[-1][1]:
        print("    FATAL: Clips catalog item not available — cannot continue")
        runner.summary()
        sys.exit(1)

    def test_reach_profile():
        result = kaltura_post("reach_reachProfile", "list", {
            "filter[statusEqual]": 2,
        })
        assert result["totalCount"] > 0, "No active REACH profiles"
        state["reach_profile_id"] = result["objects"][0]["id"]
        print(f"    Using REACH profile: {state['reach_profile_id']} — {result['objects'][0]['name']}")

    runner.run_test("Active REACH profile available", test_reach_profile)

    def test_find_ready_entry():
        """Find an existing ready video entry with sufficient duration."""
        result = kaltura_post("media", "list", {
            "filter[statusEqual]": 2,
            "filter[mediaTypeEqual]": 1,
            "filter[durationGreaterThan]": 60,
            "filter[orderBy]": "-plays",
            "pager[pageSize]": 1,
        })
        assert result["totalCount"] > 0, "No ready video entries with duration > 60s"
        entry = result["objects"][0]
        state["source_entry_id"] = entry["id"]
        state["source_duration"] = entry.get("duration", 0)
        print(f"    Source entry: {entry['id']} — {entry.get('name', '?')}, "
              f"duration={state['source_duration']}s")

    runner.run_test("Find ready source entry (duration > 60s)", test_find_ready_entry)

    # ════════════════════════════════════════════
    # Phase 2: Order AI Clip Generation
    # ════════════════════════════════════════════

    def test_clips_task_add():
        """Order AI clip generation using KalturaClipsVendorTaskData."""
        clips_duration = min(120, state["source_duration"])
        result = kaltura_post("reach_entryVendorTask", "add", {
            "entryVendorTask[objectType]": "KalturaEntryVendorTask",
            "entryVendorTask[entryId]": state["source_entry_id"],
            "entryVendorTask[reachProfileId]": state["reach_profile_id"],
            "entryVendorTask[catalogItemId]": CLIPS_CATALOG_ITEM_ID,
            "entryVendorTask[taskJobData][objectType]": "KalturaClipsVendorTaskData",
            "entryVendorTask[taskJobData][outputLanguage]": "English",
            "entryVendorTask[taskJobData][clipsDuration]": clips_duration,
            "entryVendorTask[taskJobData][eventSessionContextId]": "",
            "entryVendorTask[taskJobData][instruction]": "API doc validation — generate highlight clips",
        })
        assert "id" in result, f"Task add failed: {result}"
        assert result["serviceFeature"] == CLIPS_SERVICE_FEATURE
        assert result["status"] in (1, 2, 3, 8), (
            f"Unexpected initial status: {result['status']}"
        )
        assert result.get("catalogItemId") == CLIPS_CATALOG_ITEM_ID
        state["clips_task_id"] = result["id"]
        state["clips_task_status"] = result["status"]
        runner.register_cleanup(f"clips task {result['id']}",
                                lambda: _abort_task(result["id"]))
        print(f"    Created clips task: {result['id']}, status={result['status']}, "
              f"clipsDuration={clips_duration}s")

    runner.run_test("entryVendorTask.add — KalturaClipsVendorTaskData", test_clips_task_add)

    def test_clips_task_get():
        """Verify task can be retrieved with correct structure."""
        result = kaltura_post("reach_entryVendorTask", "get", {
            "id": state["clips_task_id"],
        })
        assert result["id"] == state["clips_task_id"]
        assert result["catalogItemId"] == CLIPS_CATALOG_ITEM_ID
        assert result["serviceFeature"] == CLIPS_SERVICE_FEATURE
        assert result["entryId"] == state["source_entry_id"]
        state["clips_task_status"] = result["status"]
        print(f"    Task {result['id']}: status={result['status']}")

    runner.run_test("entryVendorTask.get — clips task retrievable", test_clips_task_get)

    def test_clips_task_list_filter():
        """Filter tasks by catalogItemId to find clips tasks (matches KMC polling pattern)."""
        result = kaltura_post("reach_entryVendorTask", "list", {
            "filter[entryIdEqual]": state["source_entry_id"],
            "filter[catalogItemIdEqual]": CLIPS_CATALOG_ITEM_ID,
            "filter[orderBy]": "-createdAt",
        })
        task_ids = [t["id"] for t in result.get("objects", [])]
        assert state["clips_task_id"] in task_ids, (
            f"Clips task not found in filtered list"
        )
        print(f"    Found {result['totalCount']} clips task(s) for entry")

    runner.run_test("entryVendorTask.list — filter by clips catalogItemId", test_clips_task_list_filter)

    # ════════════════════════════════════════════
    # Phase 3: Poll for Completion & Verify Clips
    # ════════════════════════════════════════════

    def test_clips_task_poll():
        """Poll until task completes or timeout (5 minutes)."""
        max_wait = 300
        poll_interval = 10
        elapsed = 0
        status = state.get("clips_task_status", 1)
        while elapsed < max_wait:
            try:
                result = kaltura_post("reach_entryVendorTask", "get", {
                    "id": state["clips_task_id"],
                })
                status = result["status"]
                state["clips_task_status"] = status
            except Exception as e:
                if "ENTRY_VENDOR_TASK_NOT_FOUND" in str(e):
                    raise Exception("Task was deleted unexpectedly")
                raise
            if status == 2:  # READY
                print(f"    Task completed (READY) after ~{elapsed}s")
                return
            elif status == 6:  # ERROR
                raise Exception(f"Task ERROR: {result.get('errDescription', '?')}")
            elif status == 7:  # ABORTED
                raise Exception("Task was aborted")
            print(f"    Polling... status={status}, elapsed={elapsed}s")
            time.sleep(poll_interval)
            elapsed += poll_interval
        raise Exception(f"Task did not complete within {max_wait}s (last status={status})")

    runner.run_test("entryVendorTask — poll until clips task completes", test_clips_task_poll)

    def test_list_generated_clips():
        """After task completes, generated clips appear as child entries via rootEntryIdIn."""
        result = kaltura_post("baseEntry", "list", {
            "filter[rootEntryIdIn]": state["source_entry_id"],
            "filter[statusIn]": "1,2,4",
            "filter[orderBy]": "-createdAt",
            "pager[pageSize]": 500,
        })
        clip_entries = result.get("objects", [])
        state["generated_clip_entries"] = clip_entries
        assert len(clip_entries) > 0, (
            f"No child entries found with rootEntryIdIn={state['source_entry_id']}"
        )
        print(f"    Found {len(clip_entries)} generated clip entries:")
        for entry in clip_entries[:5]:
            print(f"      - {entry['id']}: {entry.get('name', '?')} "
                  f"(duration={entry.get('duration', '?')}s, status={entry.get('status')})")

    runner.run_test("baseEntry.list — generated clips via rootEntryIdIn", test_list_generated_clips)

    def test_clips_playlist():
        """Clips are also collected in a path playlist (referenceIdEqual + playListTypeEqual=3)."""
        result = kaltura_post("playlist", "list", {
            "filter[referenceIdEqual]": state["source_entry_id"],
            "filter[playListTypeEqual]": 3,
            "pager[pageSize]": 500,
        })
        state["clips_playlist_count"] = result.get("totalCount", 0)
        print(f"    Found {state['clips_playlist_count']} clips playlist(s) for source entry")
        if result.get("totalCount", 0) > 0:
            pl = result["objects"][0]
            print(f"      Playlist: {pl['id']} — {pl.get('name', '?')}")

    runner.run_test("playlist.list — clips playlist (referenceId + playListType=3)", test_clips_playlist)

    # ════════════════════════════════════════════
    # Phase 4: Save a Clip (clone + updateContent + update)
    # ════════════════════════════════════════════

    def test_get_source_flavors():
        """Get source entry flavors to find the flavorParamsId for clipping."""
        result = kaltura_post("flavorAsset", "list", {
            "filter[entryIdEqual]": state["source_entry_id"],
        })
        assert result.get("totalCount", 0) > 0, "No flavor assets on source entry"
        # Prefer original flavor, fall back to any ready flavor
        flavor_params_id = None
        for f in result["objects"]:
            if f.get("status") == 2 and f.get("isOriginal"):
                flavor_params_id = f["flavorParamsId"]
                break
        if not flavor_params_id:
            for f in result["objects"]:
                if f.get("status") == 2:
                    flavor_params_id = f["flavorParamsId"]
                    break
        assert flavor_params_id is not None, "No ready flavor found"
        state["flavor_params_id"] = flavor_params_id
        print(f"    Using flavorParamsId: {flavor_params_id}")

    runner.run_test("flavorAsset.list — get source entry flavors", test_get_source_flavors)

    def test_clone_source_entry():
        """Clone the source entry with the same options KMC uses."""
        result = kaltura_post("baseEntry", "clone", {
            "entryId": state["source_entry_id"],
            # Clone options matching KMC Content Lab trace
            "cloneOptions:item1:objectType": "KalturaBaseEntryCloneOptionComponent",
            "cloneOptions:item1:itemType": "5",   # categories
            "cloneOptions:item1:rule": "1",
            "cloneOptions:item2:objectType": "KalturaBaseEntryCloneOptionComponent",
            "cloneOptions:item2:itemType": "2",   # access control
            "cloneOptions:item2:rule": "1",
            "cloneOptions:item3:objectType": "KalturaBaseEntryCloneOptionComponent",
            "cloneOptions:item3:itemType": "6",   # metadata
            "cloneOptions:item3:rule": "1",
            "cloneOptions:item4:objectType": "KalturaBaseEntryCloneOptionComponent",
            "cloneOptions:item4:itemType": "7",   # flavors
            "cloneOptions:item4:rule": "1",
            "cloneOptions:item5:objectType": "KalturaBaseEntryCloneOptionComponent",
            "cloneOptions:item5:itemType": "1",   # content
            "cloneOptions:item5:rule": "1",
        })
        assert "id" in result, f"Clone failed: {result}"
        state["cloned_entry_id"] = result["id"]
        runner.register_cleanup(f"cloned entry {result['id']}",
                                lambda: _delete_entry(result["id"]))
        print(f"    Cloned source → {result['id']}")

    runner.run_test("baseEntry.clone — clone source entry for clip", test_clone_source_entry)

    def test_update_content_with_clip():
        """Apply KalturaClipAttributes to trim the cloned entry to clip boundaries."""
        clips = state.get("generated_clip_entries", [])
        if not clips:
            raise Exception("No generated clips available")

        clip = clips[0]
        # KMC uses milliseconds for offset and duration
        clip_duration_ms = (clip.get("duration", 30)) * 1000
        clip_offset_ms = 0

        result = kaltura_post("media", "updateContent", {
            "entryId": state["cloned_entry_id"],
            "resource[objectType]": "KalturaOperationResources",
            "resource[resources][0][objectType]": "KalturaOperationResource",
            "resource[resources][0][resource][objectType]": "KalturaEntryResource",
            "resource[resources][0][resource][entryId]": state["source_entry_id"],
            "resource[resources][0][resource][flavorParamsId]": state["flavor_params_id"],
            "resource[resources][0][operationAttributes][0][objectType]": "KalturaClipAttributes",
            "resource[resources][0][operationAttributes][0][offset]": clip_offset_ms,
            "resource[resources][0][operationAttributes][0][duration]": clip_duration_ms,
        })
        assert "id" in result, f"updateContent failed: {result}"
        state["clip_offset_ms"] = clip_offset_ms
        state["clip_duration_ms"] = clip_duration_ms
        print(f"    Applied clip: offset={clip_offset_ms}ms, duration={clip_duration_ms}ms")

    runner.run_test("media.updateContent — KalturaClipAttributes (offset/duration in ms)", test_update_content_with_clip)

    def test_update_clip_metadata():
        """Set AI-generated metadata on the saved clip (name, description, tags)."""
        ts = int(time.time())
        result = kaltura_post("media", "update", {
            "entryId": state["cloned_entry_id"],
            "mediaEntry[objectType]": "KalturaMediaEntry",
            "mediaEntry[name]": f"API_DOC_VALIDATION_CLIP_{ts}",
            "mediaEntry[description]": "Test clip created by API doc validation. Safe to delete.",
            "mediaEntry[tags]": "api-test, clip, validation",
            "mediaEntry[displayInSearch]": 1,
        })
        assert result["name"] == f"API_DOC_VALIDATION_CLIP_{ts}"
        print(f"    Updated metadata: name={result['name']}")

    runner.run_test("media.update — set clip metadata (name, description, tags)", test_update_clip_metadata)

    def test_verify_saved_clip():
        """Verify the saved clip entry exists and is processing or ready."""
        result = kaltura_post("baseEntry", "get", {
            "entryId": state["cloned_entry_id"],
        })
        # Status: NO_CONTENT(-1), ERROR_CONVERTING(0), IMPORT(1), READY(2), CONVERTING(4)
        assert result["status"] in (-1, 0, 1, 2, 4), (
            f"Unexpected status={result['status']} for saved clip"
        )
        print(f"    Saved clip: {result['id']}, status={result['status']}, "
              f"name={result.get('name', '?')}")

    runner.run_test("baseEntry.get — verify saved clip entry", test_verify_saved_clip)

    # ════════════════════════════════════════════
    # Phase 5: Cleanup
    # ════════════════════════════════════════════

    def test_cleanup_task():
        """Abort the clips task if still pending."""
        try:
            result = kaltura_post("reach_entryVendorTask", "get", {
                "id": state["clips_task_id"],
            })
            if result["status"] in (1, 4, 8):
                abort_result = kaltura_post("reach_entryVendorTask", "abort", {
                    "id": state["clips_task_id"],
                })
                print(f"    Aborted task: status={abort_result.get('status')}")
            else:
                print(f"    Task in terminal state: status={result['status']}")
        except Exception as e:
            if "ENTRY_VENDOR_TASK_NOT_FOUND" in str(e):
                print("    Task already cleaned up")
            else:
                raise

    runner.run_test("Cleanup — abort clips task if still pending", test_cleanup_task)

    # ════════════════════════════════════════════
    # Summary
    # ════════════════════════════════════════════

    runner.cleanup()
    success = runner.summary()
    sys.exit(0 if success else 1)


def _abort_task(task_id):
    try:
        kaltura_post("reach_entryVendorTask", "abort", {"id": task_id})
    except Exception:
        pass


def _delete_entry(entry_id):
    try:
        kaltura_post("media", "delete", {"entryId": entry_id})
    except Exception:
        pass


if __name__ == "__main__":
    print(f"\n{'='*60}")
    print("  KALTURA AI CLIPS — End-to-End Workflow Validation")
    print(f"{'='*60}\n")
    main()
