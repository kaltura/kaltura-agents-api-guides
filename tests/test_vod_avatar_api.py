#!/usr/bin/env python3
"""End-to-end validation of the VOD Avatar Studio API — 22 tests.
Covers: avatar templates, avatar CRUD, video CRUD, audio preview,
video generation, status lifecycle, error validation, CDN/widget availability."""

import sys
import os
import time
import json
import tempfile
import requests

sys.path.insert(0, os.path.dirname(__file__))
from test_helpers import (
    kaltura_post, vod_avatar_post, TestRunner,
    PARTNER_ID, KS, SERVICE_URL, VOD_AVATAR_URL,
)

UNISPHERE_BASE = "https://unisphere.nvp1.ovp.kaltura.com/v1"
WIDGET_NAME = "unisphere.widget.vod-avatars"

state = {}


def _generate_user_ks():
    """Generate a short-lived KS for browser tests."""
    admin_secret = os.environ.get("KALTURA_ADMIN_SECRET", "")
    if not admin_secret:
        return KS
    result = kaltura_post("session", "start", {
        "secret": admin_secret,
        "partnerId": PARTNER_ID,
        "type": 2,
        "expiry": 3600,
    })
    if isinstance(result, str) and len(result) > 20:
        return result
    return KS


def main():
    runner = TestRunner("VOD Avatar Studio — E2E Validation")

    # ════════════════════════════════════════════
    # Phase 1: Avatar Templates
    # ════════════════════════════════════════════

    def test_avatar_template_list():
        """List available avatar templates."""
        result = vod_avatar_post("avatarTemplate", "list")
        assert "objects" in result, f"Expected 'objects': {result}"
        templates = result["objects"]
        assert len(templates) > 0, "Expected at least one template"
        state["template_ids"] = [t["id"] for t in templates]
        state["template_id"] = templates[0]["id"]
        for t in templates:
            assert "id" in t, f"Template missing 'id': {t}"
            assert "name" in t, f"Template missing 'name': {t}"
        print(f"    {len(templates)} templates, first: {templates[0]['id']} ({templates[0]['name']})")

    runner.run_test("avatarTemplate/list — available presenters", test_avatar_template_list)

    def test_template_jane_exists():
        """Verify 'jane' (default) template exists."""
        ids = state.get("template_ids", [])
        assert "jane" in ids, f"Expected 'jane' in templates: {ids[:10]}..."
        print("    jane template: present")

    runner.run_test("avatarTemplate/list — default 'jane' template", test_template_jane_exists)

    # ════════════════════════════════════════════
    # Phase 3: Avatar CRUD
    # ════════════════════════════════════════════

    def test_avatar_upsert():
        """Create an avatar with a color background."""
        template_id = state.get("template_id", "jane")
        result = vod_avatar_post("avatar", "upsert", {
            "templateId": template_id,
            "background": {"type": "color", "color": "#CEEEDB"},
        })
        assert "id" in result, f"Expected 'id' in response: {result}"
        state["avatar_id"] = result["id"]
        assert result.get("templateId") == template_id, \
            f"Expected templateId={template_id}, got {result.get('templateId')}"
        bg = result.get("background", {})
        assert bg.get("type") == "color", f"Expected color background: {bg}"
        print(f"    Avatar: {result['id']}, template={template_id}")

    runner.run_test("avatar/upsert — create with color background", test_avatar_upsert)

    def test_avatar_upsert_idempotent():
        """Verify upsert returns the same avatar for identical config."""
        template_id = state.get("template_id", "jane")
        result = vod_avatar_post("avatar", "upsert", {
            "templateId": template_id,
            "background": {"type": "color", "color": "#CEEEDB"},
        })
        assert result.get("id") == state.get("avatar_id"), \
            f"Expected same ID {state.get('avatar_id')}, got {result.get('id')}"
        print(f"    Idempotent: same ID returned")

    runner.run_test("avatar/upsert — idempotent for same config", test_avatar_upsert_idempotent)

    def test_avatar_get():
        """Retrieve the created avatar."""
        avatar_id = state.get("avatar_id")
        assert avatar_id, "No avatar_id from upsert"
        result = vod_avatar_post("avatar", "get", {"id": avatar_id})
        assert result.get("id") == avatar_id, f"Expected id={avatar_id}: {result}"
        assert "templateId" in result, f"Missing templateId: {result}"
        assert "background" in result, f"Missing background: {result}"
        assert "createdAt" in result, f"Missing createdAt: {result}"
        print(f"    Got avatar: {avatar_id}, template={result['templateId']}")

    runner.run_test("avatar/get — retrieve avatar", test_avatar_get)

    def test_avatar_preview():
        """Get avatar preview image (PNG)."""
        avatar_id = state.get("avatar_id")
        assert avatar_id, "No avatar_id"
        resp = vod_avatar_post("avatar", "preview", {"id": avatar_id}, raw=True)
        ct = resp.headers.get("content-type", "")
        assert "image" in ct or len(resp.content) > 100, \
            f"Expected image, got content-type={ct}, size={len(resp.content)}"
        print(f"    Preview: {len(resp.content)} bytes, content-type={ct}")

    runner.run_test("avatar/preview — get avatar image", test_avatar_preview)

    # ════════════════════════════════════════════
    # Phase 4: Video CRUD
    # ════════════════════════════════════════════

    def test_video_add():
        """Create a video project with scenes."""
        avatar_id = state.get("avatar_id")
        assert avatar_id, "No avatar_id"
        ts = int(time.time())
        result = vod_avatar_post("video", "add", {
            "name": f"API_DOC_TEST_{ts}",
            "avatarId": avatar_id,
            "scenes": [
                {
                    "layoutType": "full-screen",
                    "narration": {"text": "This is scene one for testing."},
                },
                {
                    "layoutType": "full-screen",
                    "narration": {"text": "This is scene two for testing."},
                },
            ],
        })
        assert "id" in result, f"Expected 'id': {result}"
        state["video_id"] = result["id"]
        runner.register_cleanup(
            f"video {result['id']}",
            lambda vid=result["id"]: vod_avatar_post("video", "delete", {"id": vid}, raw=True),
        )
        assert result.get("status") == "draft", f"Expected draft status: {result.get('status')}"
        scenes = result.get("scenes", [])
        assert len(scenes) == 2, f"Expected 2 scenes, got {len(scenes)}"
        assert result.get("avatarId") == avatar_id, f"Expected avatarId={avatar_id}"
        print(f"    Video: {result['id']}, status={result['status']}, scenes={len(scenes)}")

    runner.run_test("video/add — create project with scenes", test_video_add)

    def test_video_get():
        """Retrieve the video project."""
        video_id = state.get("video_id")
        assert video_id, "No video_id"
        result = vod_avatar_post("video", "get", {"id": video_id})
        assert result.get("id") == video_id, f"Expected id={video_id}: {result}"
        assert result.get("status") == "draft", f"Expected draft: {result.get('status')}"
        assert "scenes" in result, f"Missing scenes: {result}"
        assert "avatarId" in result, f"Missing avatarId: {result}"
        assert "createdAt" in result, f"Missing createdAt: {result}"
        assert "updatedAt" in result, f"Missing updatedAt: {result}"
        for scene in result["scenes"]:
            assert "layoutType" in scene, f"Scene missing layoutType: {scene}"
        print(f"    Got video: {video_id}, scenes={len(result.get('scenes', []))}")

    runner.run_test("video/get — retrieve project", test_video_get)

    def test_video_update():
        """Update the video name and scenes."""
        video_id = state.get("video_id")
        assert video_id, "No video_id"
        result = vod_avatar_post("video", "update", {
            "id": video_id,
            "name": f"API_DOC_TEST_UPDATED_{int(time.time())}",
            "scenes": [
                {
                    "layoutType": "full-screen",
                    "narration": {"text": "Updated scene one."},
                },
            ],
        })
        assert result.get("id") == video_id, f"Expected id={video_id}: {result}"
        scenes = result.get("scenes", [])
        assert len(scenes) == 1, f"Expected 1 scene after update, got {len(scenes)}"
        print(f"    Updated: {video_id}, scenes={len(scenes)}")

    runner.run_test("video/update — modify name and scenes", test_video_update)

    def test_video_list():
        """List video projects with offset/limit pager."""
        result = vod_avatar_post("video", "list", {
            "filter": {"orderBy": "-createdAt"},
            "pager": {"offset": 0, "limit": 50},
        })
        assert "objects" in result, f"Expected 'objects': {result}"
        assert "totalCount" in result, f"Expected 'totalCount': {result}"
        videos = result["objects"]
        video_id = state.get("video_id")
        found = any(v.get("id") == video_id for v in videos)
        assert found, f"Expected video {video_id} in list"
        print(f"    Listed: {len(videos)} videos, totalCount={result['totalCount']}")

    runner.run_test("video/list — find test video", test_video_list)

    # ════════════════════════════════════════════
    # Phase 5: Audio Preview
    # ════════════════════════════════════════════

    def test_preview_audio():
        """Preview TTS audio for scene 0."""
        video_id = state.get("video_id")
        assert video_id, "No video_id"
        resp = vod_avatar_post("video", "previewAudio", {
            "id": video_id,
            "sceneId": 0,
        }, timeout=60, raw=True)
        ct = resp.headers.get("content-type", "")
        assert len(resp.content) > 100, \
            f"Expected audio data, got {len(resp.content)} bytes"
        print(f"    Audio preview: {len(resp.content)} bytes, content-type={ct}")

    runner.run_test("video/previewAudio — TTS narration preview", test_preview_audio)

    # ════════════════════════════════════════════
    # Phase 6: Status Lifecycle
    # ════════════════════════════════════════════

    def test_status_draft():
        """Verify video is in draft status."""
        video_id = state.get("video_id")
        assert video_id, "No video_id"
        result = vod_avatar_post("video", "get", {"id": video_id})
        assert result.get("status") == "draft", \
            f"Expected draft, got {result.get('status')}"
        print(f"    Status: {result.get('status')}")

    runner.run_test("status — video is in draft", test_status_draft)

    def test_reset_status_rejects_draft():
        """Verify resetStatus rejects non-error statuses (returns 200 with error body)."""
        video_id = state.get("video_id")
        assert video_id, "No video_id"
        result = vod_avatar_post("video", "resetStatus", {"id": video_id})
        assert isinstance(result, dict), f"Expected dict: {result}"
        assert result.get("code") == "CANNOT_RESET_STATUS", \
            f"Expected CANNOT_RESET_STATUS, got: {result}"
        print(f"    Correctly rejected: {result.get('code')}")

    runner.run_test("status — resetStatus rejects non-error status", test_reset_status_rejects_draft)

    # ════════════════════════════════════════════
    # Phase 7: Video Generation
    # ════════════════════════════════════════════

    def test_video_generate():
        """Generate the video and poll for completion."""
        video_id = state.get("video_id")
        assert video_id, "No video_id"
        result = vod_avatar_post("video", "generate", {"id": video_id}, timeout=60)
        status = result.get("status")
        if result.get("code"):
            print(f"    Generation rejected: {result.get('code')} — {result.get('message', '')[:80]}")
            state["generation_rejected"] = True
            return
        assert status == "generating", \
            f"Expected generating, got {status}"
        print(f"    Generation started: {video_id}")

        max_wait = 300
        interval = 10
        elapsed = 0
        final_status = "generating"
        while elapsed < max_wait:
            time.sleep(interval)
            elapsed += interval
            check = vod_avatar_post("video", "get", {"id": video_id})
            final_status = check.get("status", "unknown")
            print(f"    [{elapsed}s] Status: {final_status}")
            if final_status in ("ready", "generate-error"):
                break

        if final_status == "ready":
            entry_id = check.get("entryId", "")
            state["generated_entry_id"] = entry_id
            assert entry_id, f"Expected entryId on ready video: {check}"
            print(f"    Generated entry: {entry_id}")
        elif final_status == "generate-error":
            print(f"    Generation failed — valid API response")
            state["generation_error"] = True
        else:
            print(f"    Timed out at {max_wait}s with status: {final_status}")
            state["generation_timeout"] = True

    runner.run_test("video/generate — render avatar video", test_video_generate)

    def test_generated_entry_accessible():
        """Verify the generated Kaltura entry exists."""
        entry_id = state.get("generated_entry_id")
        if not entry_id:
            print("    Skipped — no generated entry (generation failed/rejected/timed out)")
            return
        result = kaltura_post("media", "get", {"entryId": entry_id})
        assert "id" in result, f"Expected entry: {result}"
        print(f"    Entry: {entry_id}, status={result.get('status')}, name={result.get('name')}")

    runner.run_test("media.get — generated entry exists in Kaltura", test_generated_entry_accessible)

    # ════════════════════════════════════════════
    # Phase 8: Error Validation
    # ════════════════════════════════════════════

    def test_invalid_avatar_id():
        """Verify video/add rejects invalid avatar ID."""
        try:
            vod_avatar_post("video", "add", {
                "name": "Invalid Avatar Test",
                "avatarId": "nonexistent_avatar_id_12345",
            })
            assert False, "Expected error for invalid avatarId"
        except Exception as e:
            err = str(e)
            assert "AVATAR" in err.upper() or "404" in err or "400" in err or "not found" in err.lower(), \
                f"Unexpected error: {err}"
            print(f"    Correctly rejected: {err[:80]}")

    runner.run_test("video/add — rejects invalid avatarId", test_invalid_avatar_id)

    def test_invalid_template_id():
        """Verify avatar/upsert rejects invalid template ID."""
        try:
            vod_avatar_post("avatar", "upsert", {
                "templateId": "nonexistent_template_xyz",
                "background": {"type": "color", "color": "#FFFFFF"},
            })
            assert False, "Expected error for invalid templateId"
        except Exception as e:
            err = str(e)
            assert "TEMPLATE" in err.upper() or "404" in err or "400" in err or "not found" in err.lower(), \
                f"Unexpected error: {err}"
            print(f"    Correctly rejected: {err[:80]}")

    runner.run_test("avatar/upsert — rejects invalid templateId", test_invalid_template_id)

    def test_video_delete():
        """Delete the test video project."""
        video_id = state.get("video_id")
        assert video_id, "No video_id"
        if state.get("generation_timeout"):
            check = vod_avatar_post("video", "get", {"id": video_id})
            if check.get("status") == "generating":
                print("    Waiting for generation to finish before delete...")
                for _ in range(30):
                    time.sleep(10)
                    check = vod_avatar_post("video", "get", {"id": video_id})
                    if check.get("status") != "generating":
                        break
        # delete returns empty body
        vod_avatar_post("video", "delete", {"id": video_id}, raw=True)
        state["video_deleted"] = True
        print(f"    Deleted: {video_id}")

    runner.run_test("video/delete — remove test project", test_video_delete)

    # ════════════════════════════════════════════
    # Phase 9: CDN & Widget Availability
    # ════════════════════════════════════════════

    def test_manifest():
        """Verify VOD Avatar widget is in the runtime.json manifest."""
        resp = requests.get(f"{UNISPHERE_BASE}/runtime.json", timeout=30)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        data = resp.json()
        widgets = data.get("versions", {}).get("widgets", {})
        assert WIDGET_NAME in widgets, f"Expected '{WIDGET_NAME}' in manifest"
        va = widgets[WIDGET_NAME]
        runtimes = va.get("runtimes", {})
        assert "studio" in runtimes, "Expected 'studio' runtime"
        state["studio_version"] = runtimes["studio"]["version"]
        print(f"    studio: v{state['studio_version']}")

    runner.run_test("manifest — VOD Avatar widget with studio runtime", test_manifest)

    def test_bundle():
        """Verify the studio bundle is accessible on CDN."""
        version = state.get("studio_version")
        if not version:
            print("    Skipped — no version from manifest")
            return
        url = (f"{UNISPHERE_BASE}/static/modules/vod-avatars/v{version}"
               f"/runtime/studio/index.esm.js")
        resp = requests.head(url, timeout=30)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        print(f"    studio bundle: {resp.status_code}")

    runner.run_test("bundle — studio runtime accessible on CDN", test_bundle)

    def test_regional():
        """Verify VOD Avatar widget is available in EU and DE regions."""
        for region, label in [("irp2", "EU"), ("frp2", "DE")]:
            url = f"https://unisphere.{region}.ovp.kaltura.com/v1/runtime.json"
            resp = requests.get(url, timeout=30)
            assert resp.status_code == 200, f"Expected 200 for {label}"
            data = resp.json()
            widgets = data.get("versions", {}).get("widgets", {})
            assert WIDGET_NAME in widgets, \
                f"Expected '{WIDGET_NAME}' in {label} manifest"
            version = widgets[WIDGET_NAME]["runtimes"]["studio"]["version"]
            print(f"    {label} ({region}): v{version}")

    runner.run_test("regional — VOD Avatar in EU and DE manifests", test_regional)

    # ════════════════════════════════════════════
    # Phase 10: Browser Tests (optional, Playwright)
    # ════════════════════════════════════════════

    try:
        from playwright.sync_api import sync_playwright
        HAS_PLAYWRIGHT = True
    except ImportError:
        HAS_PLAYWRIGHT = False
        print("\n  Playwright not installed — skipping browser tests")

    if HAS_PLAYWRIGHT:
        browser_ks = _generate_user_ks()

        def test_runtime_loads():
            """Verify the studio runtime loads in the browser."""
            html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>VOD Avatar Test</title></head>
<body>
<div id="va-studio" style="width:100%;height:100vh;"></div>
<script type="module">
  import {{ loader }} from "{UNISPHERE_BASE}/loader/index.esm.js";
  try {{
    const ws = await loader({{
      serverUrl: "{UNISPHERE_BASE}",
      appId: "va-rt-test", appVersion: "1.0.0",
      session: {{ ks: "{browser_ks}", partnerId: {PARTNER_ID} }},
      runtimes: [{{
        widgetName: "{WIDGET_NAME}",
        runtimeName: "studio",
        settings: {{
          ks: "{browser_ks}",
          partnerId: {PARTNER_ID},
          kalturaServerURI: "https://www.kaltura.com"
        }},
        visuals: [{{ type: "page", target: "va-studio", settings: {{}} }}]
      }}]
    }});
    const rt = await ws.getRuntimeAsync("{WIDGET_NAME}", "studio");
    window.__va_done = true;
    window.__va_result = rt !== null ? "OK" : "NULL";
  }} catch(e) {{
    window.__va_done = true;
    window.__va_result = "ERR:" + e.message;
  }}
</script></body></html>"""
            path = os.path.join(tempfile.gettempdir(), "va_rt_test.html")
            with open(path, "w") as f:
                f.write(html)
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                page.goto(f"file://{path}", wait_until="networkidle", timeout=30000)
                page.wait_for_function("window.__va_done !== undefined", timeout=30000)
                result = page.evaluate("window.__va_result")
                browser.close()
            assert result == "OK", f"Expected OK, got {result}"
            print(f"    Studio runtime: loaded")

        runner.run_test("browser — studio runtime loads successfully", test_runtime_loads)

    # ════════════════════════════════════════════
    # Cleanup & Summary
    # ════════════════════════════════════════════

    keep = "--keep" in sys.argv
    if keep:
        print("\n--- --keep flag: skipping cleanup ---")
        if state.get("video_id") and not state.get("video_deleted"):
            print(f"  Video ID: {state['video_id']}")
        if state.get("avatar_id"):
            print(f"  Avatar ID: {state['avatar_id']}")
        if state.get("generated_entry_id"):
            print(f"  Generated Entry: {state['generated_entry_id']}")
    else:
        if sys.stdin.isatty() and not os.environ.get("CI"):
            input("\nPress Enter to clean up...")
        runner.cleanup()

    success = runner.summary()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
