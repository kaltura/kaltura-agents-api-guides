#!/usr/bin/env python3
"""
End-to-end validation of the Multi-Stream (Dual/Multi-Screen) Entries API.

Covers: importing video content via addFromUrl, creating parent-child
relationships, verifying via baseEntry.get, listing children via
baseEntry.list with parentEntryIdEqual filter, linking/unlinking
existing entries via baseEntry.update, waiting for READY status,
verifying playManifest delivery, and cleanup.
"""

import sys
import os
import time
import tempfile
import webbrowser
import requests

sys.path.insert(0, os.path.dirname(__file__))
from test_helpers import kaltura_post, TestRunner, PARTNER_ID, KS, SERVICE_URL

# Player v7 uiconf with Dual Screen plugin enabled
PLAYER_ID = os.environ.get("KALTURA_PLAYER_ID", "56732362")

# Small public video for import testing (direct MP4 URL, not a playManifest redirect)
SAMPLE_VIDEO_URL = os.environ.get(
    "KALTURA_TEST_VIDEO_URL",
    "https://cfvod.kaltura.com/pd/p/811441/sp/81144100/serveFlavor/entryId/1_uoup50ye/v/1/ev/6/flavorId/1_m8w4gjs8/name/a.mp4"
)

# Polling config for entry readiness
READY_STATUS = 2
POLL_INTERVAL = 5      # seconds between status checks
POLL_TIMEOUT = 180     # max seconds to wait for READY

state = {}


def _wait_for_ready(entry_id, label="entry"):
    """Poll baseEntry.get until status=2 (READY) or timeout."""
    start = time.time()
    while time.time() - start < POLL_TIMEOUT:
        result = kaltura_post("baseEntry", "get", {"entryId": entry_id})
        status = result.get("status")
        if status == READY_STATUS:
            print(f"    {label} {entry_id} is READY (took {int(time.time() - start)}s)")
            return result
        if status == -1:
            raise Exception(f"{label} {entry_id} failed transcoding (status=-1)")
        print(f"    {label} {entry_id} status={status}, waiting...")
        time.sleep(POLL_INTERVAL)
    raise Exception(f"{label} {entry_id} did not reach READY within {POLL_TIMEOUT}s (last status={status})")


def _delete_entry(entry_id):
    """Delete a media entry by ID."""
    try:
        kaltura_post("media", "delete", {"entryId": entry_id})
    except Exception as e:
        print(f"  [WARN] Failed to delete entry {entry_id}: {e}")


def main():
    runner = TestRunner("Multi-Stream (Dual/Multi-Screen) Entries API — E2E Validation")

    # ════════════════════════════════════════════
    # Phase 1: Create Parent Entry with Content
    # ════════════════════════════════════════════

    def test_create_parent_from_url():
        """Create parent entry by importing video from URL."""
        ts = int(time.time())
        result = kaltura_post("media", "addFromUrl", {
            "mediaEntry[objectType]": "KalturaMediaEntry",
            "mediaEntry[mediaType]": 1,
            "mediaEntry[name]": f"MULTISTREAM_E2E_PARENT_{ts}",
            "mediaEntry[description]": "Multi-stream e2e test parent. Safe to delete.",
            "url": SAMPLE_VIDEO_URL,
        })
        assert "id" in result, f"No entry ID returned: {result}"
        state["parent_id"] = result["id"]
        runner.register_cleanup(f"parent entry {result['id']}",
                                lambda: _delete_entry(result["id"]))
        print(f"    Parent entry: {result['id']}, status={result.get('status')}")

    runner.run_test("media.addFromUrl — create parent entry with content", test_create_parent_from_url)

    def test_create_child1_from_url():
        """Create first child entry with parentEntryId set, importing video from URL."""
        ts = int(time.time())
        result = kaltura_post("media", "addFromUrl", {
            "mediaEntry[objectType]": "KalturaMediaEntry",
            "mediaEntry[mediaType]": 1,
            "mediaEntry[name]": f"MULTISTREAM_E2E_CHILD1_{ts}",
            "mediaEntry[description]": "Multi-stream e2e test child 1. Safe to delete.",
            "mediaEntry[parentEntryId]": state["parent_id"],
            "url": SAMPLE_VIDEO_URL,
        })
        assert "id" in result, f"No entry ID returned: {result}"
        state["child1_id"] = result["id"]
        runner.register_cleanup(f"child entry 1 {result['id']}",
                                lambda: _delete_entry(result["id"]))
        print(f"    Child 1: {result['id']}, parentEntryId={result.get('parentEntryId')}")

    runner.run_test("media.addFromUrl — create child entry with parentEntryId", test_create_child1_from_url)

    # ════════════════════════════════════════════
    # Phase 2: Wait for Content Processing
    # ════════════════════════════════════════════

    def test_parent_reaches_ready():
        """Wait for parent entry to reach READY status."""
        result = _wait_for_ready(state["parent_id"], "parent")
        state["parent_duration"] = result.get("duration", 0)
        print(f"    Parent duration: {state['parent_duration']}s")

    runner.run_test("poll — parent entry reaches READY", test_parent_reaches_ready)

    def test_child1_reaches_ready():
        """Wait for child entry 1 to reach READY status."""
        result = _wait_for_ready(state["child1_id"], "child 1")
        state["child1_duration"] = result.get("duration", 0)
        print(f"    Child 1 duration: {state['child1_duration']}s")

    runner.run_test("poll — child entry 1 reaches READY", test_child1_reaches_ready)

    # ════════════════════════════════════════════
    # Phase 3: Verify Parent-Child Relationship
    # ════════════════════════════════════════════

    def test_verify_parent_no_parent_id():
        """Verify the parent entry has no parentEntryId."""
        result = kaltura_post("baseEntry", "get", {"entryId": state["parent_id"]})
        parent_entry_id = result.get("parentEntryId", "")
        assert not parent_entry_id, f"Parent should have no parentEntryId, got: {parent_entry_id}"
        print(f"    Parent {result['id']} has no parentEntryId (correct)")

    runner.run_test("baseEntry.get — parent has no parentEntryId", test_verify_parent_no_parent_id)

    def test_verify_child_parent_link():
        """Verify child's parentEntryId matches the parent."""
        result = kaltura_post("baseEntry", "get", {"entryId": state["child1_id"]})
        assert result.get("parentEntryId") == state["parent_id"], \
            f"Expected parentEntryId={state['parent_id']}, got {result.get('parentEntryId')}"
        print(f"    Child {result['id']} → parentEntryId={result['parentEntryId']} (correct)")

    runner.run_test("baseEntry.get — child has correct parentEntryId", test_verify_child_parent_link)

    def test_durations_match():
        """Verify parent and child have matching durations (same source video)."""
        # Same video imported twice — durations should match
        assert state.get("parent_duration", 0) > 0, "Parent duration is 0"
        assert state.get("child1_duration", 0) > 0, "Child duration is 0"
        assert state["parent_duration"] == state["child1_duration"], \
            f"Duration mismatch: parent={state['parent_duration']}s, child={state['child1_duration']}s"
        print(f"    Durations match: {state['parent_duration']}s")

    runner.run_test("verify — parent and child durations match", test_durations_match)

    # ════════════════════════════════════════════
    # Phase 4: List Children of Parent
    # ════════════════════════════════════════════

    def test_list_children():
        """List children using parentEntryIdEqual filter."""
        result = kaltura_post("baseEntry", "list", {
            "filter[parentEntryIdEqual]": state["parent_id"],
        })
        assert result.get("totalCount", 0) >= 1, \
            f"Expected at least 1 child, got totalCount={result.get('totalCount')}"
        child_ids = [obj["id"] for obj in result.get("objects", [])]
        assert state["child1_id"] in child_ids, \
            f"Child {state['child1_id']} not in list: {child_ids}"
        print(f"    Found {result['totalCount']} child(ren): {child_ids}")

    runner.run_test("baseEntry.list — list children with parentEntryIdEqual", test_list_children)

    def test_parent_not_in_children_list():
        """Verify parent does not appear in its own children list."""
        result = kaltura_post("baseEntry", "list", {
            "filter[parentEntryIdEqual]": state["parent_id"],
        })
        child_ids = [obj["id"] for obj in result.get("objects", [])]
        assert state["parent_id"] not in child_ids, \
            "Parent entry should not appear in its own children list"
        print(f"    Parent correctly absent from children list")

    runner.run_test("baseEntry.list — parent excluded from own children", test_parent_not_in_children_list)

    # ════════════════════════════════════════════
    # Phase 5: Add Second Child (3+ streams)
    # ════════════════════════════════════════════

    def test_create_child2_from_url():
        """Create a second child entry to test multi-stream with 3+ entries."""
        ts = int(time.time())
        result = kaltura_post("media", "addFromUrl", {
            "mediaEntry[objectType]": "KalturaMediaEntry",
            "mediaEntry[mediaType]": 1,
            "mediaEntry[name]": f"MULTISTREAM_E2E_CHILD2_{ts}",
            "mediaEntry[description]": "Multi-stream e2e test child 2. Safe to delete.",
            "mediaEntry[parentEntryId]": state["parent_id"],
            "url": SAMPLE_VIDEO_URL,
        })
        assert "id" in result
        state["child2_id"] = result["id"]
        runner.register_cleanup(f"child entry 2 {result['id']}",
                                lambda: _delete_entry(result["id"]))
        print(f"    Child 2: {result['id']}")

    runner.run_test("media.addFromUrl — create second child entry", test_create_child2_from_url)

    def test_child2_reaches_ready():
        """Wait for child entry 2 to reach READY status."""
        _wait_for_ready(state["child2_id"], "child 2")

    runner.run_test("poll — child entry 2 reaches READY", test_child2_reaches_ready)

    def test_list_multiple_children():
        """Verify both children appear in the list."""
        # Child2 was just created — allow a few seconds for indexing
        for attempt in range(6):
            result = kaltura_post("baseEntry", "list", {
                "filter[parentEntryIdEqual]": state["parent_id"],
            })
            child_ids = [obj["id"] for obj in result.get("objects", [])]
            if state["child1_id"] in child_ids and state["child2_id"] in child_ids:
                break
            time.sleep(3)
        assert result.get("totalCount", 0) >= 2, \
            f"Expected at least 2 children, got {result.get('totalCount')}"
        assert state["child1_id"] in child_ids, "Child 1 missing from list"
        assert state["child2_id"] in child_ids, "Child 2 missing from list"
        print(f"    Found {result['totalCount']} children: {child_ids}")

    runner.run_test("baseEntry.list — verify multiple children listed", test_list_multiple_children)

    # ════════════════════════════════════════════
    # Phase 6: Link Existing Entry as Child
    # ════════════════════════════════════════════

    def test_create_independent_entry():
        """Create an independent entry (no parent) to later link as child."""
        ts = int(time.time())
        result = kaltura_post("media", "addFromUrl", {
            "mediaEntry[objectType]": "KalturaMediaEntry",
            "mediaEntry[mediaType]": 1,
            "mediaEntry[name]": f"MULTISTREAM_E2E_INDEPENDENT_{ts}",
            "mediaEntry[description]": "Will be linked as child via update. Safe to delete.",
            "url": SAMPLE_VIDEO_URL,
        })
        assert "id" in result
        state["independent_id"] = result["id"]
        runner.register_cleanup(f"independent entry {result['id']}",
                                lambda: _delete_entry(result["id"]))
        assert not result.get("parentEntryId"), "New entry should have no parentEntryId"
        print(f"    Independent entry: {result['id']}")

    runner.run_test("media.addFromUrl — create independent entry", test_create_independent_entry)

    def test_link_existing_as_child():
        """Link an existing entry as child via baseEntry.update."""
        result = kaltura_post("baseEntry", "update", {
            "entryId": state["independent_id"],
            "baseEntry[parentEntryId]": state["parent_id"],
        })
        assert result.get("parentEntryId") == state["parent_id"], \
            f"Expected parentEntryId={state['parent_id']}, got {result.get('parentEntryId')}"
        print(f"    Entry {state['independent_id']} linked to parent {state['parent_id']}")

    runner.run_test("baseEntry.update — link existing entry as child", test_link_existing_as_child)

    def test_linked_child_in_list():
        """Verify newly linked child appears in children list."""
        for attempt in range(12):
            result = kaltura_post("baseEntry", "list", {
                "filter[parentEntryIdEqual]": state["parent_id"],
            })
            child_ids = [obj["id"] for obj in result.get("objects", [])]
            if state["independent_id"] in child_ids:
                break
            time.sleep(5)
        assert result.get("totalCount", 0) >= 3, \
            f"Expected at least 3 children, got {result.get('totalCount')}"
        assert state["independent_id"] in child_ids, \
            f"Linked entry {state['independent_id']} not in children list"
        print(f"    {result['totalCount']} children total (including linked entry)")

    runner.run_test("baseEntry.list — linked entry appears in children", test_linked_child_in_list)

    # ════════════════════════════════════════════
    # Phase 7: Unlink a Child
    # ════════════════════════════════════════════

    def test_unlink_child():
        """Unlink a child by clearing parentEntryId."""
        result = kaltura_post("baseEntry", "update", {
            "entryId": state["independent_id"],
            "baseEntry[parentEntryId]": "",
        })
        parent_id_after = result.get("parentEntryId", "")
        assert not parent_id_after, \
            f"parentEntryId should be empty after unlink, got: {parent_id_after}"
        print(f"    Entry {state['independent_id']} unlinked")

    runner.run_test("baseEntry.update — unlink child (clear parentEntryId)", test_unlink_child)

    def test_unlinked_removed_from_list():
        """Verify unlinked entry no longer in children list."""
        result = kaltura_post("baseEntry", "list", {
            "filter[parentEntryIdEqual]": state["parent_id"],
        })
        child_ids = [obj["id"] for obj in result.get("objects", [])]
        assert state["independent_id"] not in child_ids, \
            f"Unlinked entry still in children list"
        print(f"    {result['totalCount']} children remain (unlinked entry removed)")

    runner.run_test("baseEntry.list — unlinked entry removed from children", test_unlinked_removed_from_list)

    # ════════════════════════════════════════════
    # Phase 8: Content Delivery Verification
    # ════════════════════════════════════════════

    def test_parent_playmanifest():
        """Verify playManifest returns a valid HLS manifest for the parent entry."""
        # Flavor publishing may lag slightly behind READY status — brief settle
        time.sleep(5)
        manifest_url = (
            f"https://cdnapisec.kaltura.com/p/{PARTNER_ID}/sp/{PARTNER_ID}00"
            f"/playManifest/entryId/{state['parent_id']}/format/applehttp/protocol/https"
        )
        resp = requests.get(manifest_url, timeout=15, allow_redirects=True)
        assert resp.status_code == 200, f"playManifest returned {resp.status_code}"
        body = resp.text
        assert "#EXTM3U" in body, f"Response is not an HLS manifest: {body[:200]}"
        print(f"    Parent HLS manifest OK ({len(body)} bytes)")

    runner.run_test("playManifest — parent entry returns valid HLS manifest", test_parent_playmanifest)

    def test_child_playmanifest():
        """Verify playManifest returns a valid HLS manifest for the child entry."""
        manifest_url = (
            f"https://cdnapisec.kaltura.com/p/{PARTNER_ID}/sp/{PARTNER_ID}00"
            f"/playManifest/entryId/{state['child1_id']}/format/applehttp/protocol/https"
        )
        resp = requests.get(manifest_url, timeout=15, allow_redirects=True)
        assert resp.status_code == 200, f"playManifest returned {resp.status_code}"
        body = resp.text
        assert "#EXTM3U" in body, f"Response is not an HLS manifest: {body[:200]}"
        print(f"    Child 1 HLS manifest OK ({len(body)} bytes)")

    runner.run_test("playManifest — child entry returns valid HLS manifest", test_child_playmanifest)

    def test_parent_thumbnail():
        """Verify thumbnail API returns an image for the parent entry."""
        thumb_url = (
            f"https://cdnapisec.kaltura.com/p/{PARTNER_ID}"
            f"/thumbnail/entry_id/{state['parent_id']}/width/320/height/180"
        )
        resp = requests.get(thumb_url, timeout=15, allow_redirects=True)
        assert resp.status_code == 200, f"Thumbnail returned {resp.status_code}"
        content_type = resp.headers.get("Content-Type", "")
        assert "image" in content_type, f"Expected image content-type, got: {content_type}"
        print(f"    Parent thumbnail OK ({len(resp.content)} bytes, {content_type})")

    runner.run_test("thumbnail — parent entry returns valid image", test_parent_thumbnail)

    # ════════════════════════════════════════════
    # Phase 9: Flavor Assets Verification
    # ════════════════════════════════════════════

    def test_parent_flavors():
        """Verify parent entry has transcoded flavor assets."""
        result = kaltura_post("flavorAsset", "list", {
            "filter[entryIdEqual]": state["parent_id"],
        })
        assert result.get("totalCount", 0) >= 1, \
            f"Expected at least 1 flavor, got {result.get('totalCount')}"
        flavors = result.get("objects", [])
        ready_flavors = [f for f in flavors if f.get("status") == 2]
        print(f"    Parent has {len(ready_flavors)} READY flavor(s) out of {len(flavors)} total")
        assert len(ready_flavors) >= 1, "Expected at least 1 READY flavor"

    runner.run_test("flavorAsset.list — parent has READY flavors", test_parent_flavors)

    def test_child_flavors():
        """Verify child entry has transcoded flavor assets."""
        result = kaltura_post("flavorAsset", "list", {
            "filter[entryIdEqual]": state["child1_id"],
        })
        assert result.get("totalCount", 0) >= 1, \
            f"Expected at least 1 flavor, got {result.get('totalCount')}"
        flavors = result.get("objects", [])
        ready_flavors = [f for f in flavors if f.get("status") == 2]
        print(f"    Child 1 has {len(ready_flavors)} READY flavor(s) out of {len(flavors)} total")
        assert len(ready_flavors) >= 1, "Expected at least 1 READY flavor"

    runner.run_test("flavorAsset.list — child has READY flavors", test_child_flavors)

    # ════════════════════════════════════════════
    # Phase 10: Player Experience — Dual Screen
    # ════════════════════════════════════════════

    def test_generate_and_open_player_page():
        """Generate an HTML page with Player v7 Dual Screen and open in browser."""
        parent_id = state["parent_id"]
        child_ids_result = kaltura_post("baseEntry", "list", {
            "filter[parentEntryIdEqual]": parent_id,
        })
        child_entries = child_ids_result.get("objects", [])
        child_summary = ", ".join(
            f"{c['id']} ({c.get('name', '?')})" for c in child_entries
        )

        # Generate a short-lived USER KS for the player (1 hour, playback + list)
        player_ks = kaltura_post("session", "start", {
            "secret": os.environ.get("KALTURA_ADMIN_SECRET", ""),
            "partnerId": PARTNER_ID,
            "userId": "e2e_player_test",
            "type": 0,
            "expiry": 3600,
            "privileges": "sview:*,disableentitlement,list:*",
        })
        print(f"    Player KS generated (USER, 1hr TTL)")

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Multi-Stream Dual Screen — E2E Player Test</title>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
         background: #1a1a2e; color: #e0e0e0; padding: 20px; }}
  h1 {{ font-size: 1.4rem; margin-bottom: 8px; color: #fff; }}
  .subtitle {{ color: #888; font-size: 0.85rem; margin-bottom: 20px; }}
  #player-container {{ width: 100%; max-width: 960px; aspect-ratio: 16/9;
                       background: #000; border-radius: 8px; overflow: hidden;
                       margin-bottom: 20px; }}
  .controls {{ display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 20px; }}
  .controls button {{ padding: 8px 16px; border: 1px solid #444; border-radius: 6px;
                      background: #2a2a4a; color: #e0e0e0; cursor: pointer;
                      font-size: 0.85rem; transition: all 0.2s; }}
  .controls button:hover {{ background: #3a3a6a; border-color: #666; }}
  .controls button.active {{ background: #5a4a8a; border-color: #8a7aba; color: #fff; }}
  .info {{ background: #0d0d1a; border: 1px solid #333; border-radius: 8px;
           padding: 16px; font-size: 0.8rem; line-height: 1.6; }}
  .info h3 {{ color: #aaa; font-size: 0.75rem; text-transform: uppercase;
              letter-spacing: 1px; margin-bottom: 8px; }}
  .info code {{ background: #1a1a2e; padding: 2px 6px; border-radius: 3px;
                font-family: 'SF Mono', monospace; color: #8a7aba; }}
  #status {{ color: #4a9; margin-top: 12px; font-style: italic; }}
  #debug {{ margin-top: 12px; font-size: 0.75rem; color: #666; white-space: pre-wrap; }}
</style>
</head>
<body>

<h1>Multi-Stream Dual Screen — E2E Player Test</h1>
<p class="subtitle">
  Parent: <code>{parent_id}</code> &nbsp;|&nbsp;
  Children: {len(child_entries)} stream(s) &nbsp;|&nbsp;
  Player: <code>{PLAYER_ID}</code>
</p>

<div id="player-container"></div>

<div class="controls">
  <button onclick="setLayout('PIP')" id="btn-pip">PiP</button>
  <button onclick="setLayout('PIPInverse')">PiP Inverse</button>
  <button onclick="setLayout('SideBySide')" id="btn-sbs">Side by Side</button>
  <button onclick="setLayout('SideBySideInverse')">SbS Inverse</button>
  <button onclick="setLayout('SingleMedia')">Primary Only</button>
  <button onclick="setLayout('SingleMediaInverse')">Secondary Only</button>
</div>

<div class="info">
  <h3>Test Checklist</h3>
  <ol style="padding-left: 20px;">
    <li>Player loads with <strong>PiP layout</strong> (secondary stream as small overlay)</li>
    <li>Click <strong>"Side by Side"</strong> — both streams display equally</li>
    <li>Click <strong>"PiP Inverse"</strong> — secondary becomes the large view</li>
    <li>Click <strong>"Primary Only" / "Secondary Only"</strong> — single stream view</li>
    <li>Drag the PiP overlay to a different corner</li>
    <li>Verify audio plays from <strong>parent stream only</strong></li>
    <li>Play/pause/seek — both streams stay <strong>synchronized</strong></li>
  </ol>
  <div id="status">Loading player...</div>
  <div id="debug"></div>
</div>

<script src="https://cdnapisec.kaltura.com/p/{PARTNER_ID}/embedPlaykitJs/uiconf_id/{PLAYER_ID}"></script>
<script>
  var kalturaPlayer;
  var debugEl = document.getElementById('debug');

  function log(msg) {{
    console.log('[DualScreen E2E]', msg);
    debugEl.textContent += msg + '\\n';
  }}

  try {{
    kalturaPlayer = KalturaPlayer.setup({{
      targetId: 'player-container',
      provider: {{
        partnerId: {PARTNER_ID},
        uiConfId: {PLAYER_ID},
        ks: '{player_ks}'
      }},
      playback: {{
        autoplay: false,
        preload: 'auto'
      }}
    }});

    log('Player setup complete. Loading entry {parent_id}...');
    kalturaPlayer.loadMedia({{ entryId: '{parent_id}' }});

    kalturaPlayer.addEventListener('playing', function() {{
      document.getElementById('status').textContent =
        'Playing — dual screen active. Try the layout buttons above.';
    }});

    kalturaPlayer.addEventListener('error', function(e) {{
      var msg = e.payload?.error?.message || JSON.stringify(e.payload);
      document.getElementById('status').textContent = 'Player error: ' + msg;
      document.getElementById('status').style.color = '#e44';
      log('ERROR: ' + JSON.stringify(e.payload, null, 2));
    }});

    // Listen for dual screen layout changes
    kalturaPlayer.addEventListener('dualscreen_change_layout', function(e) {{
      document.getElementById('status').textContent =
        'Layout changed to: ' + (e.payload?.layout || JSON.stringify(e.payload));
      updateActiveButton(e.payload?.layout);
      log('Layout changed: ' + JSON.stringify(e.payload));
    }});

    document.getElementById('status').textContent =
      'Player loaded. Press play to start dual screen playback.';
    document.getElementById('btn-pip').classList.add('active');

  }} catch (err) {{
    document.getElementById('status').textContent = 'Setup error: ' + err.message;
    document.getElementById('status').style.color = '#e44';
    log('SETUP ERROR: ' + err.message + '\\n' + err.stack);
  }}

  // player.configure() only sets initial config — it does NOT trigger runtime
  // layout changes. The plugin exposes private _switchTo* methods that must be
  // called directly. We wait for media to load then check the dualScreen service.
  var dsReady = false;
  var dsPlugin = null;

  function tryInitDualScreen() {{
    if (dsReady) return;
    try {{
      var svc = kalturaPlayer.getService('dualScreen');
      if (!svc || !svc.ready) {{
        log('dualScreen service not available yet');
        return;
      }}
      svc.ready.then(function() {{
        dsPlugin = kalturaPlayer.plugins.dualscreen;
        dsReady = true;
        log('Dual screen service READY');
        var players = svc.getDualScreenPlayers ? svc.getDualScreenPlayers() : [];
        log('Dual screen players: ' + players.length);
        log('Plugin methods: ' + Object.getOwnPropertyNames(Object.getPrototypeOf(dsPlugin)).filter(function(m) {{ return m.indexOf('_switch') === 0; }}).join(', '));
        log('Layout buttons ENABLED — click any button above');
        document.getElementById('status').textContent = 'Dual screen ready — try the layout buttons!';
        document.getElementById('status').style.color = '#4a9';
      }}).catch(function(err) {{
        log('Dual screen ready rejected: ' + err);
      }});
    }} catch(e) {{
      log('tryInitDualScreen error: ' + e.message);
    }}
  }}

  // Try on multiple events — the service may become available at different points
  kalturaPlayer.addEventListener('playing', tryInitDualScreen);
  kalturaPlayer.addEventListener('canplay', tryInitDualScreen);
  // Also try after a delay in case change_source_ended fires early
  kalturaPlayer.ready().then(function() {{
    log('player.ready() resolved');
    tryInitDualScreen();
    // Retry after delays in case secondary media loads later
    setTimeout(tryInitDualScreen, 2000);
    setTimeout(tryInitDualScreen, 5000);
  }});

  function setLayout(layout) {{
    if (!dsReady || !dsPlugin) {{
      log('Dual screen not ready yet — press play first');
      document.getElementById('status').textContent = 'Press play first, then switch layouts.';
      return;
    }}
    try {{
      switch (layout) {{
        case 'PIP':
          dsPlugin._switchToPIP({{ force: true }}, true);
          break;
        case 'PIPInverse':
          dsPlugin._applyInverse();
          dsPlugin._switchToPIP({{ force: true }}, true);
          break;
        case 'SideBySide':
          dsPlugin._switchToSideBySide({{ force: true }}, true);
          break;
        case 'SideBySideInverse':
          dsPlugin._applyInverse();
          dsPlugin._switchToSideBySide({{ force: true }}, true);
          break;
        case 'SingleMedia':
          dsPlugin._switchToSingleMedia({{ force: true }}, true);
          break;
        case 'SingleMediaInverse':
          dsPlugin._applyInverse();
          dsPlugin._switchToSingleMedia({{ force: true }}, true);
          break;
        case 'Hidden':
          dsPlugin._switchToHidden(true);
          break;
      }}
      updateActiveButton(layout);
      document.getElementById('status').textContent = 'Layout: ' + layout;
      log('Switched to: ' + layout);
    }} catch(e) {{
      log('setLayout error: ' + e.message);
      document.getElementById('status').textContent = 'Layout switch failed: ' + e.message;
      document.getElementById('status').style.color = '#e44';
    }}
  }}

  function updateActiveButton(layout) {{
    document.querySelectorAll('.controls button').forEach(function(btn) {{
      btn.classList.remove('active');
      if (btn.textContent.trim() === layoutLabels[layout]) btn.classList.add('active');
    }});
  }}
  var layoutLabels = {{
    'PIP': 'PiP', 'PIPInverse': 'PiP Inverse',
    'SideBySide': 'Side by Side', 'SideBySideInverse': 'SbS Inverse',
    'SingleMedia': 'Primary Only', 'SingleMediaInverse': 'Secondary Only',
    'Hidden': 'Hidden'
  }};
</script>

</body>
</html>"""

        # Write to temp file and open in browser
        html_path = os.path.join(tempfile.gettempdir(), "kaltura_multistream_e2e_test.html")
        with open(html_path, "w") as f:
            f.write(html)

        print(f"    HTML test page: {html_path}")
        print(f"    Parent entry: {parent_id}")
        print(f"    Children: {child_summary}")
        print(f"    Player uiconf: {PLAYER_ID}")
        print(f"    Opening in browser...")

        webbrowser.open(f"file://{html_path}")

        print(f"    Browser opened — verify dual screen playback manually:")
        print(f"      1. PiP layout loads with secondary as overlay")
        print(f"      2. Layout buttons switch between PiP/SbS/Single")
        print(f"      3. Audio from parent only, streams synchronized")
        print(f"      4. PiP overlay is draggable")

    runner.run_test("player — generate and open dual screen test page", test_generate_and_open_player_page)

    # ════════════════════════════════════════════
    # Cleanup & Summary
    # ════════════════════════════════════════════

    keep = "--keep" in sys.argv
    if keep:
        # Skip cleanup — print entry IDs and a manual cleanup command
        all_ids = [v for k, v in state.items() if k.endswith("_id")]
        print(f"\n    --keep flag set. Entries preserved for manual testing:")
        for k, v in state.items():
            if k.endswith("_id"):
                print(f"      {k}: {v}")
        print(f"\n    To clean up later, run:")
        print(f"      python3 -c \"")
        print(f"      import sys; sys.path.insert(0, '.')  ")
        print(f"      from test_helpers import kaltura_post")
        for eid in all_ids:
            print(f"      kaltura_post('media', 'delete', {{'entryId': '{eid}'}})")
        print(f"      \"")
    else:
        # Interactive cleanup — wait for user if terminal is interactive
        if sys.stdin.isatty():
            print("\n    ⏸  Player test page is open in your browser.")
            print("    Press Enter when done testing to proceed with cleanup...")
            input()
        runner.cleanup()

    success = runner.summary()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
