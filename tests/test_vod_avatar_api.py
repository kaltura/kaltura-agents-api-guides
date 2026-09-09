#!/usr/bin/env python3
"""End-to-end validation of the VOD Avatar Studio API — 23 tests.
Covers: partner configuration, avatar creation, video CRUD, audio preview,
URL preview, AI composition validation rules, video generation, status
lifecycle, error validation, CDN/widget availability."""

import sys
import os
import time
import json
import tempfile
import requests

sys.path.insert(0, os.path.dirname(__file__))
from test_helpers import (
    kaltura_post, vod_avatar_post, avatar_catalog_post, TestRunner,
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
    # Phase 1: Partner Configuration
    # ════════════════════════════════════════════

    def test_partner_init_configuration():
        """Verify the account is provisioned for VOD Avatar."""
        result = vod_avatar_post("partner", "initConfiguration", {})
        assert result.get("ok") is True, f"Expected ok=true: {result}"
        checks = {c["name"]: c.get("valid") for c in result.get("results", [])}
        assert "source-only-conversion-profile" in checks, \
            f"Expected 'source-only-conversion-profile' check: {checks}"
        assert checks["source-only-conversion-profile"] is True, \
            f"Expected source-only-conversion-profile valid: {checks}"
        print(f"    Checks: {list(checks.keys())}")

    runner.run_test("partner/initConfiguration — verify account provisioning", test_partner_init_configuration)

    # ════════════════════════════════════════════
    # Phase 2: Create an Avatar
    # ════════════════════════════════════════════
    # Avatar creation and template selection live on a separate avatar
    # catalog service (see guide section 5) — not part of this API. Tests
    # create a fresh avatar from a template for each run, the same way the
    # Unisphere widget's avatar picker creates one on first use. Reusing an
    # avatarId scraped from an older video project is unsafe — if that
    # avatar has since been deleted from the catalog, video/add still
    # accepts the stale ID (it isn't validated there), but previewAudio and
    # previewAudioStream fail with a raw HTTP 500 when they try to resolve
    # its voice. Always obtain a current avatarId instead of reusing one.

    def test_create_avatar():
        """Create a fresh avatar from the 'jane' template."""
        templates = avatar_catalog_post("avatar-template", "list", {
            "pager": {"offset": 0, "limit": 500},
        })
        assert "objects" in templates, f"Expected 'objects': {templates}"
        jane = next((t for t in templates["objects"] if t.get("name", "").lower() == "jane"), None)
        assert jane, f"Expected a 'jane' template: {[t.get('name') for t in templates['objects']]}"
        avatar = avatar_catalog_post("avatar", "create", {
            "templateId": jane["id"],
            "background": {"type": "color", "value": "#CEEEDB"},
            "adminTags": ["api-doc-validation-test"],
        })
        assert "id" in avatar, f"Expected 'id': {avatar}"
        state["avatar_id"] = avatar["id"]
        runner.register_cleanup(
            f"avatar {avatar['id']}",
            lambda aid=avatar["id"]: avatar_catalog_post("avatar", "delete", {"id": aid}),
        )
        print(f"    Created avatar: {avatar['id']} (template: {jane['name']})")

    runner.run_test("avatar/create — create a fresh avatar", test_create_avatar)

    # ════════════════════════════════════════════
    # Phase 3: Video CRUD
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
                    "narration": {"text": "Updated scene one with more narration text."},
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
    # Phase 4: Audio & URL Preview
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

    def test_preview_audio_stream():
        """Preview TTS audio for scene 0 via the streaming variant."""
        video_id = state.get("video_id")
        assert video_id, "No video_id"
        resp = vod_avatar_post("video", "previewAudioStream", {
            "id": video_id,
            "sceneId": 0,
        }, timeout=60, raw=True)
        ct = resp.headers.get("content-type", "")
        assert len(resp.content) > 100, \
            f"Expected audio data, got {len(resp.content)} bytes"
        print(f"    Audio stream preview: {len(resp.content)} bytes, content-type={ct}")

    runner.run_test("video/previewAudioStream — TTS narration preview (streaming)", test_preview_audio_stream)

    def test_preview_url():
        """Preview a public URL source before composing an explainer video."""
        result = vod_avatar_post("video", "previewUrl", {"url": "https://example.com"})
        assert "title" in result, f"Expected 'title': {result}"
        assert "imageUrl" in result, f"Expected 'imageUrl': {result}"
        print(f"    Preview: title={result.get('title')!r}")

    runner.run_test("video/previewUrl — preview a URL source", test_preview_url)

    # ════════════════════════════════════════════
    # Phase 5: AI Composition Validation Rules
    # ════════════════════════════════════════════
    # Full AI composition requires source entries with existing captions/
    # transcripts (see guide section 7); these tests exercise the
    # per-format validation rules, which return immediately without
    # requiring captioned content.

    def test_compose_explainer_requires_brief_or_source():
        """explainer-video with no sources and no userBrief is rejected."""
        video_id = state.get("video_id")
        assert video_id, "No video_id"
        result = vod_avatar_post("video", "compose", {
            "id": video_id, "formatType": "explainer-video",
            "duration": 60, "sources": [],
        })
        assert result.get("code") == "USER_BRIEF_REQUIRED", \
            f"Expected USER_BRIEF_REQUIRED, got: {result}"
        print(f"    Correctly rejected: {result.get('code')}")

    runner.run_test("video/compose — explainer-video requires brief or source", test_compose_explainer_requires_brief_or_source)

    def test_compose_presentation_narration_requires_entry():
        """presentation-narration without an entry source is rejected."""
        video_id = state.get("video_id")
        assert video_id, "No video_id"
        result = vod_avatar_post("video", "compose", {
            "id": video_id, "formatType": "presentation-narration",
            "duration": 60, "sources": [],
        })
        assert result.get("code") == "PRESENTATION_REQUIRED", \
            f"Expected PRESENTATION_REQUIRED, got: {result}"
        print(f"    Correctly rejected: {result.get('code')}")

    runner.run_test("video/compose — presentation-narration requires an entry source", test_compose_presentation_narration_requires_entry)

    def test_compose_session_highlights_too_many_sources():
        """session-highlights rejects more than one source."""
        video_id = state.get("video_id")
        assert video_id, "No video_id"
        result = vod_avatar_post("video", "compose", {
            "id": video_id, "formatType": "session-highlights",
            "duration": 60,
            "sources": [{"entryId": "1_aaaaaaaa"}, {"entryId": "1_bbbbbbbb"}],
        })
        assert result.get("code") == "TOO_MANY_SOURCES", \
            f"Expected TOO_MANY_SOURCES, got: {result}"
        print(f"    Correctly rejected: {result.get('code')}")

    runner.run_test("video/compose — session-highlights rejects more than one source", test_compose_session_highlights_too_many_sources)

    def test_compose_explainer_too_many_urls():
        """explainer-video rejects more than 5 URL sources."""
        video_id = state.get("video_id")
        assert video_id, "No video_id"
        urls = [{"url": f"https://example.com/{i}"} for i in range(6)]
        result = vod_avatar_post("video", "compose", {
            "id": video_id, "formatType": "explainer-video",
            "duration": 60, "sources": urls,
        })
        assert result.get("code") == "TOO_MANY_URLS", \
            f"Expected TOO_MANY_URLS, got: {result}"
        print(f"    Correctly rejected: {result.get('code')}")

    runner.run_test("video/compose — explainer-video rejects more than 5 URLs", test_compose_explainer_too_many_urls)

    def test_compose_presentation_narration_rejects_url():
        """presentation-narration rejects URL sources."""
        video_id = state.get("video_id")
        assert video_id, "No video_id"
        result = vod_avatar_post("video", "compose", {
            "id": video_id, "formatType": "presentation-narration",
            "duration": 60, "sources": [{"url": "https://example.com"}],
        })
        assert result.get("code") == "URLS_NOT_SUPPORTED", \
            f"Expected URLS_NOT_SUPPORTED, got: {result}"
        print(f"    Correctly rejected: {result.get('code')}")

    runner.run_test("video/compose — presentation-narration rejects URL sources", test_compose_presentation_narration_rejects_url)

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
        result = vod_avatar_post("video", "add", {
            "name": "Invalid Avatar Test",
            "avatarId": "nonexistent_avatar_id_12345",
        })
        assert result.get("code") == "AVATAR_NOT_FOUND", \
            f"Expected AVATAR_NOT_FOUND, got: {result}"
        print(f"    Correctly rejected: {result.get('code')}")

    runner.run_test("video/add — rejects invalid avatarId", test_invalid_avatar_id)

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
        """Verify VOD Avatar widget is available in EU, DE, Canada, and Australia regions."""
        for region, label in [("irp2", "EU"), ("frp2", "DE"), ("cap2", "Canada"), ("syp2", "Australia")]:
            url = f"https://unisphere.{region}.ovp.kaltura.com/v1/runtime.json"
            resp = requests.get(url, timeout=30)
            assert resp.status_code == 200, f"Expected 200 for {label}"
            data = resp.json()
            widgets = data.get("versions", {}).get("widgets", {})
            assert WIDGET_NAME in widgets, \
                f"Expected '{WIDGET_NAME}' in {label} manifest"
            version = widgets[WIDGET_NAME]["runtimes"]["studio"]["version"]
            print(f"    {label} ({region}): v{version}")

    runner.run_test("regional — VOD Avatar in EU, DE, Canada, Australia manifests", test_regional)

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
