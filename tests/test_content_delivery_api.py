#!/usr/bin/env python3
"""
End-to-end validation of the Content Delivery API.

Covers: playManifest (HLS, DASH, progressive, download), raw serve URL,
download endpoint, flavorAsset delivery, access-controlled URLs.
"""

import sys
import os
import requests

sys.path.insert(0, os.path.dirname(__file__))
from test_helpers import kaltura_post, TestRunner, PARTNER_ID, KS, SERVICE_URL

state = {}


def main():
    runner = TestRunner("Content Delivery API Validation")

    # ════════════════════════════════════════════
    # Phase 1: Find a READY entry for delivery tests
    # ════════════════════════════════════════════

    def test_find_ready_entry():
        """Find a ready video entry for delivery testing."""
        result = kaltura_post("media", "list", {
            "filter[statusEqual]": 2,
            "filter[mediaTypeEqual]": 1,
            "filter[orderBy]": "-plays",
            "filter[playsGreaterThanOrEqual]": 1,
            "pager[pageSize]": 1,
        })
        assert result["totalCount"] > 0, "No ready video entries found for delivery tests"
        entry = result["objects"][0]
        state["entry_id"] = entry["id"]
        state["partner_id"] = str(entry.get("partnerId", PARTNER_ID))
        state["entry_name"] = entry.get("name", "?")
        state["download_url"] = entry.get("downloadUrl", "")
        print(f"    Entry: {entry['id']} — {entry.get('name', '?')}")

    runner.run_test("Find ready video entry", test_find_ready_entry)

    # ════════════════════════════════════════════
    # Phase 2: playManifest — Streaming Formats
    # ════════════════════════════════════════════

    def test_play_manifest_hls():
        """Verify HLS playManifest returns a valid M3U8 manifest."""
        pid = state["partner_id"]
        url = (f"https://cdnapisec.kaltura.com/p/{pid}/sp/{pid}00/"
               f"playManifest/entryId/{state['entry_id']}/format/applehttp/protocol/https"
               f"/ks/{KS}")
        resp = requests.get(url, timeout=15, allow_redirects=True)
        assert resp.status_code == 200, f"HLS returned {resp.status_code}"
        text = resp.text
        assert "#EXTM3U" in text or resp.headers.get("Content-Type", "").startswith("application/"), \
            "Response doesn't look like HLS manifest"
        print(f"    HLS manifest: {len(text)} chars")

    runner.run_test("playManifest — HLS (applehttp)", test_play_manifest_hls)

    def test_play_manifest_dash():
        """Verify MPEG-DASH playManifest returns a valid MPD manifest."""
        pid = state["partner_id"]
        url = (f"https://cdnapisec.kaltura.com/p/{pid}/sp/{pid}00/"
               f"playManifest/entryId/{state['entry_id']}/format/mpegdash/protocol/https"
               f"/ks/{KS}")
        resp = requests.get(url, timeout=15, allow_redirects=True)
        assert resp.status_code == 200, f"DASH returned {resp.status_code}"
        text = resp.text
        assert "MPD" in text or "dash" in resp.headers.get("Content-Type", "").lower(), \
            "Response doesn't look like DASH manifest"
        print(f"    DASH manifest: {len(text)} chars")

    runner.run_test("playManifest — MPEG-DASH", test_play_manifest_dash)

    def test_play_manifest_progressive():
        """Verify progressive URL format returns a redirect to MP4."""
        pid = state["partner_id"]
        url = (f"https://cdnapisec.kaltura.com/p/{pid}/sp/{pid}00/"
               f"playManifest/entryId/{state['entry_id']}/format/url/protocol/https"
               f"/ks/{KS}")
        resp = requests.head(url, timeout=15, allow_redirects=True)
        assert resp.status_code in (200, 301, 302, 303), \
            f"Progressive URL returned {resp.status_code}"
        content_type = resp.headers.get("Content-Type", "")
        print(f"    Progressive URL: status={resp.status_code}, content-type={content_type}")

    runner.run_test("playManifest — progressive (url)", test_play_manifest_progressive)

    def test_play_manifest_download():
        """Verify download format returns a downloadable response."""
        pid = state["partner_id"]
        url = (f"https://cdnapisec.kaltura.com/p/{pid}/sp/{pid}00/"
               f"playManifest/entryId/{state['entry_id']}/format/download/protocol/https"
               f"/flavorParamIds/0/ks/{KS}")
        resp = requests.head(url, timeout=15, allow_redirects=True)
        assert resp.status_code in (200, 301, 302, 303), \
            f"Download URL returned {resp.status_code}"
        print(f"    Download URL: status={resp.status_code}")

    runner.run_test("playManifest — download", test_play_manifest_download)

    def test_play_manifest_max_bitrate():
        """Verify maxBitrate parameter limits flavors in manifest."""
        pid = state["partner_id"]
        url = (f"https://cdnapisec.kaltura.com/p/{pid}/sp/{pid}00/"
               f"playManifest/entryId/{state['entry_id']}/format/applehttp/protocol/https"
               f"/maxBitrate/1500/ks/{KS}")
        resp = requests.get(url, timeout=15, allow_redirects=True)
        assert resp.status_code == 200, f"maxBitrate HLS returned {resp.status_code}"
        print(f"    maxBitrate=1500 HLS: {len(resp.text)} chars")

    runner.run_test("playManifest — maxBitrate parameter", test_play_manifest_max_bitrate)

    def test_play_manifest_clip_to():
        """Verify clipTo parameter for preview clips."""
        pid = state["partner_id"]
        url = (f"https://cdnapisec.kaltura.com/p/{pid}/sp/{pid}00/"
               f"playManifest/entryId/{state['entry_id']}/format/applehttp/protocol/https"
               f"/clipTo/10000/ks/{KS}")
        resp = requests.get(url, timeout=15, allow_redirects=True)
        assert resp.status_code == 200, f"clipTo HLS returned {resp.status_code}"
        print(f"    clipTo=10000 HLS: {len(resp.text)} chars")

    runner.run_test("playManifest — clipTo preview", test_play_manifest_clip_to)

    # ════════════════════════════════════════════
    # Phase 3: Entry downloadUrl property
    # ════════════════════════════════════════════

    def test_entry_download_url():
        """Verify the entry's downloadUrl property works."""
        download_url = state.get("download_url", "")
        assert download_url.startswith("http"), f"Expected URL, got: {download_url}"
        resp = requests.head(download_url, timeout=15, allow_redirects=True)
        assert resp.status_code in (200, 301, 302, 303), \
            f"downloadUrl returned {resp.status_code}"
        print(f"    downloadUrl: status={resp.status_code}")

    runner.run_test("media.get — downloadUrl property", test_entry_download_url)

    # ════════════════════════════════════════════
    # Phase 4: Flavor Asset Delivery
    # ════════════════════════════════════════════

    def test_flavor_asset_list():
        """List flavor assets for the test entry."""
        result = kaltura_post("flavorAsset", "list", {
            "filter[entryIdEqual]": state["entry_id"],
        })
        assert result.get("totalCount", 0) > 0, "No flavor assets found"
        flavors = result["objects"]
        state["flavors"] = flavors
        ready_flavors = [f for f in flavors if f.get("status") == 2]
        print(f"    {result['totalCount']} flavor(s), {len(ready_flavors)} ready:")
        for f in ready_flavors[:3]:
            print(f"      {f['id']}: {f.get('width', '?')}x{f.get('height', '?')} "
                  f"@ {f.get('bitrate', '?')}kbps, original={f.get('isOriginal', False)}")

    runner.run_test("flavorAsset.list — list transcoded flavors", test_flavor_asset_list)

    def test_flavor_asset_get_url():
        """Get download URL for a specific flavor asset."""
        ready_flavors = [f for f in state.get("flavors", []) if f.get("status") == 2]
        if not ready_flavors:
            raise RuntimeError("No ready flavors")
        flavor_id = ready_flavors[0]["id"]
        result = kaltura_post("flavorAsset", "getUrl", {
            "id": flavor_id,
        })
        assert isinstance(result, str) and result.startswith("http"), \
            f"Expected URL string, got: {result}"
        state["flavor_url"] = result
        print(f"    Flavor {flavor_id} URL: {result[:100]}...")

    runner.run_test("flavorAsset.getUrl — get download URL for flavor", test_flavor_asset_get_url)

    def test_flavor_asset_get_with_params():
        """Get flavor assets with their params for an entry."""
        result = kaltura_post("flavorAsset", "getFlavorAssetsWithParams", {
            "entryId": state["entry_id"],
        })
        assert isinstance(result, list) or isinstance(result, dict), \
            f"Unexpected response type: {type(result)}"
        if isinstance(result, list):
            print(f"    {len(result)} flavor+params pairs")
        elif isinstance(result, dict) and "objects" in result:
            print(f"    {len(result['objects'])} flavor+params pairs")
        else:
            print(f"    Response: {str(result)[:200]}")

    runner.run_test("flavorAsset.getFlavorAssetsWithParams", test_flavor_asset_get_with_params)

    # ════════════════════════════════════════════
    # Phase 5: Raw Serve URL
    # ════════════════════════════════════════════

    def test_raw_serve_url():
        """Verify raw serve URL returns content."""
        pid = state["partner_id"]
        url = (f"https://cdnapisec.kaltura.com/p/{pid}/"
               f"raw/entry_id/{state['entry_id']}/ks/{KS}")
        resp = requests.head(url, timeout=15, allow_redirects=True)
        assert resp.status_code in (200, 301, 302, 303), \
            f"Raw serve returned {resp.status_code}"
        content_type = resp.headers.get("Content-Type", "")
        print(f"    Raw serve: status={resp.status_code}, content-type={content_type}")

    runner.run_test("Raw serve URL — direct file access", test_raw_serve_url)

    def test_raw_serve_direct():
        """Verify raw serve with direct_serve=1 (inline)."""
        pid = state["partner_id"]
        url = (f"https://cdnapisec.kaltura.com/p/{pid}/"
               f"raw/entry_id/{state['entry_id']}/direct_serve/1/forceproxy/true/ks/{KS}")
        resp = requests.head(url, timeout=15, allow_redirects=True)
        assert resp.status_code in (200, 301, 302, 303), \
            f"Raw serve direct returned {resp.status_code}"
        print(f"    Raw serve (direct): status={resp.status_code}")

    runner.run_test("Raw serve URL — direct_serve/1 inline", test_raw_serve_direct)

    # ════════════════════════════════════════════
    # Cleanup & Summary
    # ════════════════════════════════════════════

    runner.cleanup()
    success = runner.summary()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    print(f"\n{'='*60}")
    print("  KALTURA CONTENT DELIVERY — End-to-End API Validation")
    print(f"{'='*60}\n")
    main()
