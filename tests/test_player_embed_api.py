#!/usr/bin/env python3
"""
End-to-end validation of the Kaltura Player Embed Guide against the live API.

Covers: iframe embed URL construction, playManifest URL response, thumbnail API,
player config endpoint, uiConf.get for player verification, and embed URL
parameter validation.

Note: Full player rendering requires a browser. These tests validate the
server-side APIs and URL construction that the guide documents.
"""

import sys
import os
import time

sys.path.insert(0, os.path.dirname(__file__))
from test_helpers import kaltura_post, TestRunner, PARTNER_ID, KS, SERVICE_URL

import requests

PLAYER_ID = os.environ.get("KALTURA_PLAYER_ID", "")

state = {}


def main():
    runner = TestRunner("Player Embed Guide — E2E Validation")

    # ════════════════════════════════════════════
    # Phase 1: Prerequisites — Find a ready entry and player
    # ════════════════════════════════════════════

    def test_find_ready_entry():
        """Find an existing ready video entry for player/embed tests."""
        result = kaltura_post("media", "list", {
            "filter[statusEqual]": 2,
            "filter[mediaTypeEqual]": 1,
            "filter[orderBy]": "-plays",
            "filter[playsGreaterThanOrEqual]": 1,
            "pager[pageSize]": 1,
        })
        assert result["totalCount"] > 0, "No ready video entries in account"
        entry = result["objects"][0]
        state["entry_id"] = entry["id"]
        state["entry_name"] = entry.get("name", "?")
        print(f"    Using entry: {entry['id']} — {state['entry_name']}")

    runner.run_test("Find ready video entry", test_find_ready_entry)

    def test_find_player():
        """Find a valid player (uiConf) for embed tests."""
        if PLAYER_ID:
            state["player_id"] = PLAYER_ID
            print(f"    Using configured KALTURA_PLAYER_ID: {PLAYER_ID}")
            return
        # List available players
        result = kaltura_post("uiConf", "list", {
            "filter[objTypeEqual]": 1,  # PLAYER
            "filter[statusEqual]": 2,   # READY
            "pager[pageSize]": 5,
        })
        if result["totalCount"] > 0:
            player = result["objects"][0]
            state["player_id"] = str(player["id"])
            print(f"    Found player: {player['id']} — {player.get('name', '?')}")
        else:
            # Try listing all uiConfs without status filter
            result = kaltura_post("uiConf", "list", {
                "filter[objTypeEqual]": 1,
                "pager[pageSize]": 5,
            })
            assert result["totalCount"] > 0, "No players (uiConf) found in account"
            state["player_id"] = str(result["objects"][0]["id"])
            print(f"    Found player (no status filter): {state['player_id']}")

    runner.run_test("Find player uiConf", test_find_player)

    def test_uiconf_get():
        """uiConf.get retrieves player configuration."""
        result = kaltura_post("uiConf", "get", {
            "id": state["player_id"],
        })
        assert result.get("id") == int(state["player_id"]), \
            f"Expected player ID {state['player_id']}, got {result.get('id')}"
        assert "partnerId" in result, f"Missing partnerId: {list(result.keys())}"
        state["player_name"] = result.get("name", "?")
        print(f"    Player: {result['id']}, name={state['player_name']}, "
              f"swfUrl={result.get('swfUrl', 'N/A')[:50]}...")

    runner.run_test("uiConf.get — retrieve player config", test_uiconf_get)

    # ════════════════════════════════════════════
    # Phase 2: Iframe Embed URL Construction
    # ════════════════════════════════════════════

    def test_iframe_embed_url():
        """Construct iframe embed URL and verify it returns HTML."""
        # Standard iframe embed URL pattern from the guide
        embed_url = (
            f"https://cdnapisec.kaltura.com/p/{PARTNER_ID}"
            f"/embedPlaykitJs/uiconf_id/{state['player_id']}"
            f"?iframeembed=true&entry_id={state['entry_id']}"
        )
        resp = requests.get(embed_url, timeout=30, allow_redirects=True)
        assert resp.status_code == 200, \
            f"Iframe embed URL returned {resp.status_code}: {embed_url}"
        content_type = resp.headers.get("Content-Type", "")
        assert "text/html" in content_type or "text/javascript" in content_type, \
            f"Expected HTML/JS content, got: {content_type}"
        state["embed_url"] = embed_url
        print(f"    Embed URL OK (status={resp.status_code}, "
              f"content-type={content_type[:30]}, size={len(resp.content)})")

    runner.run_test("Iframe embed URL — returns HTML", test_iframe_embed_url)

    def test_iframe_embed_with_ks():
        """Iframe embed URL with KS parameter for authenticated playback."""
        embed_url = (
            f"https://cdnapisec.kaltura.com/p/{PARTNER_ID}"
            f"/embedPlaykitJs/uiconf_id/{state['player_id']}"
            f"?iframeembed=true&entry_id={state['entry_id']}"
            f"&flashvars[ks]={KS}"
        )
        resp = requests.get(embed_url, timeout=30, allow_redirects=True)
        assert resp.status_code == 200, \
            f"Authenticated embed URL returned {resp.status_code}"
        print(f"    Authenticated embed URL OK (status={resp.status_code})")

    runner.run_test("Iframe embed URL — with KS parameter", test_iframe_embed_with_ks)

    # ════════════════════════════════════════════
    # Phase 3: playManifest — Adaptive Streaming
    # ════════════════════════════════════════════

    def test_play_manifest_hls():
        """playManifest returns HLS manifest URL (may redirect)."""
        manifest_url = (
            f"{SERVICE_URL}/../p/{PARTNER_ID}"
            f"/playManifest/entryId/{state['entry_id']}"
            f"/format/applehttp/protocol/https/ks/{KS}"
        )
        resp = requests.get(manifest_url, timeout=30, allow_redirects=True)
        # playManifest may return 200 (manifest content) or redirect
        assert resp.status_code in (200, 301, 302), \
            f"playManifest returned {resp.status_code}"
        if resp.status_code == 200:
            content = resp.text[:200]
            # HLS manifests start with #EXTM3U
            is_hls = "#EXTM3U" in content or "m3u8" in content.lower()
            print(f"    HLS manifest: {resp.status_code}, HLS detected: {is_hls}, "
                  f"size={len(resp.content)}")
        else:
            print(f"    playManifest redirect: {resp.status_code} → {resp.headers.get('Location', '?')[:80]}")

    runner.run_test("playManifest — HLS (applehttp) format", test_play_manifest_hls)

    def test_play_manifest_dash():
        """playManifest with DASH format."""
        manifest_url = (
            f"{SERVICE_URL}/../p/{PARTNER_ID}"
            f"/playManifest/entryId/{state['entry_id']}"
            f"/format/mpegdash/protocol/https/ks/{KS}"
        )
        resp = requests.get(manifest_url, timeout=30, allow_redirects=True)
        assert resp.status_code in (200, 301, 302), \
            f"DASH playManifest returned {resp.status_code}"
        print(f"    DASH manifest: status={resp.status_code}, size={len(resp.content)}")

    runner.run_test("playManifest — DASH (mpegdash) format", test_play_manifest_dash)

    # ════════════════════════════════════════════
    # Phase 4: Thumbnail API
    # ════════════════════════════════════════════

    def test_thumbnail_default():
        """Default thumbnail URL returns an image."""
        thumb_url = (
            f"{SERVICE_URL}/../p/{PARTNER_ID}"
            f"/thumbnail/entry_id/{state['entry_id']}"
        )
        resp = requests.get(thumb_url, timeout=30, allow_redirects=True)
        assert resp.status_code == 200, f"Thumbnail returned {resp.status_code}"
        content_type = resp.headers.get("Content-Type", "")
        assert "image" in content_type, f"Expected image content, got: {content_type}"
        print(f"    Default thumbnail: {content_type}, size={len(resp.content)}")

    runner.run_test("Thumbnail API — default thumbnail", test_thumbnail_default)

    def test_thumbnail_with_dimensions():
        """Thumbnail with width/height parameters."""
        thumb_url = (
            f"{SERVICE_URL}/../p/{PARTNER_ID}"
            f"/thumbnail/entry_id/{state['entry_id']}"
            f"/width/320/height/180"
        )
        resp = requests.get(thumb_url, timeout=30, allow_redirects=True)
        assert resp.status_code == 200, f"Sized thumbnail returned {resp.status_code}"
        content_type = resp.headers.get("Content-Type", "")
        assert "image" in content_type, f"Expected image: {content_type}"
        print(f"    Sized thumbnail (320x180): {content_type}, size={len(resp.content)}")

    runner.run_test("Thumbnail API — with width/height", test_thumbnail_with_dimensions)

    def test_thumbnail_at_time():
        """Thumbnail at a specific time offset (vid_sec parameter)."""
        thumb_url = (
            f"{SERVICE_URL}/../p/{PARTNER_ID}"
            f"/thumbnail/entry_id/{state['entry_id']}"
            f"/width/320/vid_sec/5"
        )
        resp = requests.get(thumb_url, timeout=30, allow_redirects=True)
        assert resp.status_code == 200, f"Time-offset thumbnail returned {resp.status_code}"
        content_type = resp.headers.get("Content-Type", "")
        assert "image" in content_type, f"Expected image: {content_type}"
        print(f"    Time-offset thumbnail (5s): {content_type}, size={len(resp.content)}")

    runner.run_test("Thumbnail API — at specific time (vid_sec)", test_thumbnail_at_time)

    # ════════════════════════════════════════════
    # Phase 5: Flavor Assets (Download URLs)
    # ════════════════════════════════════════════

    def test_list_flavors():
        """flavorAsset.list returns available transcoded versions."""
        result = kaltura_post("flavorAsset", "list", {
            "filter[entryIdEqual]": state["entry_id"],
        })
        assert "objects" in result, f"Missing objects: {list(result.keys())}"
        assert result["totalCount"] > 0, "No flavor assets for entry"
        ready_flavors = [f for f in result["objects"] if f.get("status") == 2]
        state["flavor_count"] = len(ready_flavors)
        if ready_flavors:
            state["flavor_id"] = ready_flavors[0]["id"]
            state["flavor_params_id"] = ready_flavors[0]["flavorParamsId"]
        print(f"    Flavors: {result['totalCount']} total, {len(ready_flavors)} ready")

    runner.run_test("flavorAsset.list — list entry flavors", test_list_flavors)

    def test_flavor_download_url():
        """flavorAsset.getUrl returns a download URL."""
        if "flavor_id" not in state:
            raise Exception("Skipped — no ready flavor from earlier test")
        result = kaltura_post("flavorAsset", "getUrl", {
            "id": state["flavor_id"],
        })
        # getUrl returns a string URL
        assert isinstance(result, str), f"Expected URL string, got {type(result)}: {result}"
        assert result.startswith("http"), f"Expected HTTP URL: {result}"
        print(f"    Download URL: {result[:80]}...")

    runner.run_test("flavorAsset.getUrl — download URL", test_flavor_download_url)

    # ════════════════════════════════════════════
    # Phase 6: Player Configuration Validation
    # ════════════════════════════════════════════

    def test_uiconf_list_players():
        """List all Player v7 players (uiConf type=1)."""
        result = kaltura_post("uiConf", "list", {
            "filter[objTypeEqual]": 1,
            "pager[pageSize]": 10,
        })
        assert "objects" in result
        assert result["totalCount"] > 0, "No players found"
        print(f"    Players available: {result['totalCount']}")
        for p in result["objects"][:3]:
            print(f"      {p['id']}: {p.get('name', '?')} (status={p.get('status')})")

    runner.run_test("uiConf.list — list Player v7 configurations", test_uiconf_list_players)

    def test_embed_url_invalid_entry():
        """Embed URL with non-existent entry still returns embed page (player handles error)."""
        embed_url = (
            f"https://cdnapisec.kaltura.com/p/{PARTNER_ID}"
            f"/embedPlaykitJs/uiconf_id/{state['player_id']}"
            f"?iframeembed=true&entry_id=0_nonexistent999"
        )
        resp = requests.get(embed_url, timeout=30, allow_redirects=True)
        # Embed page should still load (player shows error message in-browser)
        assert resp.status_code == 200, \
            f"Embed page for invalid entry returned {resp.status_code}"
        print(f"    Invalid entry embed: page loads (status={resp.status_code}, "
              f"player handles error client-side)")

    runner.run_test("Iframe embed — invalid entry_id handled gracefully", test_embed_url_invalid_entry)

    # ════════════════════════════════════════════
    # Summary (no cleanup needed — read-only)
    # ════════════════════════════════════════════

    success = runner.summary()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    print(f"\n{'='*60}")
    print("  KALTURA PLAYER EMBED GUIDE — End-to-End Validation")
    print(f"{'='*60}\n")
    main()
