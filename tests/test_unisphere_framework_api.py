#!/usr/bin/env python3
"""End-to-end validation of the Kaltura Unisphere Framework API.
Covers: loader endpoints, runtime.json manifest, regional availability,
widget bundle accessibility, KS generation, and Genie auth verification."""

import sys
import os
import requests

sys.path.insert(0, os.path.dirname(__file__))
from test_helpers import kaltura_post, TestRunner, PARTNER_ID, KS, SERVICE_URL

UNISPHERE_REGIONS = {
    "nvp1": "https://unisphere.nvp1.ovp.kaltura.com/v1",
    "irp2": "https://unisphere.irp2.ovp.kaltura.com/v1",
    "frp2": "https://unisphere.frp2.ovp.kaltura.com/v1",
}
DEFAULT_REGION = "nvp1"
BASE_URL = UNISPHERE_REGIONS[DEFAULT_REGION]

state = {}


def main():
    runner = TestRunner("Unisphere Framework — E2E Validation")

    # ════════════════════════════════════════════
    # Phase 1: Loader & Manifest
    # ════════════════════════════════════════════

    def test_loader_endpoint():
        """Verify the Unisphere loader ESM endpoint returns JavaScript."""
        url = f"{BASE_URL}/loader/index.esm.js"
        resp = requests.get(url, timeout=30)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        ct = resp.headers.get("content-type", "")
        assert "javascript" in ct or "text/javascript" in ct or "application/javascript" in ct, \
            f"Expected JavaScript content-type, got: {ct}"
        assert len(resp.content) > 1000, f"Expected substantial JS content, got {len(resp.content)} bytes"
        print(f"    Loader: {len(resp.content)} bytes, content-type: {ct}")

    runner.run_test("loader — GET ESM endpoint (nvp1)", test_loader_endpoint)

    def test_manifest():
        """Verify runtime.json manifest returns valid JSON with widget definitions."""
        url = f"{BASE_URL}/runtime.json"
        resp = requests.get(url, timeout=30)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        data = resp.json()
        assert "versions" in data, f"Expected 'versions' key in manifest: {list(data.keys())}"
        assert "widgets" in data["versions"], f"Expected 'widgets' in versions: {list(data['versions'].keys())}"
        widgets = data["versions"]["widgets"]
        assert len(widgets) > 0, "Expected at least one widget in manifest"
        state["manifest"] = data
        state["widgets"] = widgets
        print(f"    Manifest: {len(widgets)} widgets, env={data.get('env', '?')}, version={data.get('_version', '?')}")

    runner.run_test("manifest — GET /v1/runtime.json", test_manifest)

    # ════════════════════════════════════════════
    # Phase 2: Regional Availability
    # ════════════════════════════════════════════

    def test_regional_loaders():
        """Verify loader ESM is available on EU and DE regions."""
        for region in ["irp2", "frp2"]:
            url = f"{UNISPHERE_REGIONS[region]}/loader/index.esm.js"
            resp = requests.head(url, timeout=30)
            assert resp.status_code == 200, f"{region}: Expected 200, got {resp.status_code}"
            print(f"    {region} loader: {resp.status_code}")

    runner.run_test("loader — regional endpoints (irp2, frp2)", test_regional_loaders)

    def test_regional_manifests():
        """Verify runtime.json is available on EU and DE regions."""
        for region in ["irp2", "frp2"]:
            url = f"{UNISPHERE_REGIONS[region]}/runtime.json"
            resp = requests.get(url, timeout=30)
            assert resp.status_code == 200, f"{region}: Expected 200, got {resp.status_code}"
            data = resp.json()
            assert "versions" in data, f"{region}: Expected 'versions' in manifest"
            widget_count = len(data["versions"].get("widgets", {}))
            print(f"    {region} manifest: {widget_count} widgets, env={data.get('env', '?')}")

    runner.run_test("manifest — regional endpoints (irp2, frp2)", test_regional_manifests)

    # ════════════════════════════════════════════
    # Phase 3: Widget Presence in Manifest
    # ════════════════════════════════════════════

    def test_genie_in_manifest():
        """Verify Genie widget with chat runtime is in the manifest."""
        widgets = state.get("widgets", {})
        assert "unisphere.widget.genie" in widgets, \
            f"Expected 'unisphere.widget.genie' in manifest, got: {list(widgets.keys())}"
        genie = widgets["unisphere.widget.genie"]
        assert "runtimes" in genie, f"Expected 'runtimes' in Genie widget"
        assert "chat" in genie["runtimes"], \
            f"Expected 'chat' runtime in Genie, got: {list(genie['runtimes'].keys())}"
        chat_version = genie["runtimes"]["chat"]["version"]
        print(f"    Genie chat: v{chat_version}")

    runner.run_test("manifest — contains Genie widget with chat runtime", test_genie_in_manifest)

    def test_media_manager_in_manifest():
        """Verify Media Manager widget is in the manifest."""
        widgets = state.get("widgets", {})
        assert "unisphere.widget.media-manager" in widgets, \
            f"Expected 'unisphere.widget.media-manager' in manifest"
        mm = widgets["unisphere.widget.media-manager"]
        assert "kaltura-items-media-manager" in mm["runtimes"], \
            f"Expected 'kaltura-items-media-manager' runtime, got: {list(mm['runtimes'].keys())}"
        version = mm["runtimes"]["kaltura-items-media-manager"]["version"]
        print(f"    Media Manager: v{version}")

    runner.run_test("manifest — contains Media Manager widget", test_media_manager_in_manifest)

    def test_key_widgets_in_manifest():
        """Verify content-lab, notifications, and in-app-messaging are in the manifest."""
        widgets = state.get("widgets", {})
        expected = [
            "unisphere.widget.content-lab",
            "unisphere.widget.notifications",
            "unisphere.widget.in-app-messaging",
        ]
        for widget_name in expected:
            assert widget_name in widgets, f"Expected '{widget_name}' in manifest"
            runtime_count = len(widgets[widget_name].get("runtimes", {}))
            print(f"    {widget_name}: {runtime_count} runtime(s)")

    runner.run_test("manifest — contains key widgets (content-lab, notifications, messaging)", test_key_widgets_in_manifest)

    # ════════════════════════════════════════════
    # Phase 4: Widget Bundle Accessibility
    # ════════════════════════════════════════════

    def test_genie_bundle():
        """Verify the Genie chat bundle is accessible on the CDN."""
        widgets = state.get("widgets", {})
        chat_version = widgets["unisphere.widget.genie"]["runtimes"]["chat"]["version"]
        url = f"{BASE_URL}/static/modules/genie/v{chat_version}/runtime/chat/index.esm.js"
        resp = requests.head(url, timeout=30)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code} for Genie chat bundle"
        print(f"    Genie chat bundle: {resp.status_code} (v{chat_version})")

    runner.run_test("bundle — Genie chat accessible on CDN", test_genie_bundle)

    def test_media_manager_bundle():
        """Verify the Media Manager bundle is accessible on the CDN."""
        widgets = state.get("widgets", {})
        mm_version = widgets["unisphere.widget.media-manager"]["runtimes"]["kaltura-items-media-manager"]["version"]
        url = f"{BASE_URL}/static/modules/media-manager/v{mm_version}/runtime/kaltura-items-media-manager/index.esm.js"
        resp = requests.head(url, timeout=30)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code} for Media Manager bundle"
        print(f"    Media Manager bundle: {resp.status_code} (v{mm_version})")

    runner.run_test("bundle — Media Manager accessible on CDN", test_media_manager_bundle)

    # ════════════════════════════════════════════
    # Phase 5: KS Generation & Auth
    # ════════════════════════════════════════════

    def test_generate_user_ks():
        """Generate a USER KS (type=0) with Genie privileges."""
        admin_secret = os.environ.get("KALTURA_ADMIN_SECRET")
        if not admin_secret:
            print("    Skipping — KALTURA_ADMIN_SECRET not set")
            return
        result = kaltura_post("session", "start", {
            "secret": admin_secret,
            "partnerId": PARTNER_ID,
            "type": 0,
            "userId": "unisphere-test@example.com",
            "expiry": 3600,
            "privileges": "setrole:PLAYBACK_BASE_ROLE,sview:*,appid:unisphere-test",
        })
        assert isinstance(result, str) and len(result) > 20, f"Expected KS string, got: {type(result)}"
        state["user_ks"] = result
        print(f"    USER KS: {result[:40]}...")

    runner.run_test("auth — generate USER KS with Genie privileges", test_generate_user_ks)

    def test_genie_ks_authenticates():
        """Verify the generated KS can authenticate with Genie."""
        user_ks = state.get("user_ks")
        if not user_ks:
            print("    Skipping — no USER KS generated")
            return
        genie_url = os.environ.get("KALTURA_GENIE_URL", "https://genie.nvp1.ovp.kaltura.com")
        resp = requests.post(
            f"{genie_url}/mcp/search",
            headers={
                "Authorization": f"KS {user_ks}",
                "Content-Type": "application/json",
            },
            json={"query": "test", "pid": int(PARTNER_ID)},
            timeout=60,
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text[:200]}"
        data = resp.json()
        assert "objects" in data or "results" in data or isinstance(data, list) or "message" not in data, \
            f"Unexpected response structure: {list(data.keys()) if isinstance(data, dict) else type(data)}"
        print(f"    Genie auth: {resp.status_code}")

    runner.run_test("auth — Genie KS authenticates with /mcp/search", test_genie_ks_authenticates)

    # ════════════════════════════════════════════
    # Phase 6: Manifest Structure Validation
    # ════════════════════════════════════════════

    def test_manifest_structure():
        """Verify each widget in the manifest has proper runtime structure."""
        widgets = state.get("widgets", {})
        for widget_name, widget_data in widgets.items():
            assert "runtimes" in widget_data, \
                f"Widget '{widget_name}' missing 'runtimes' key"
            runtimes = widget_data["runtimes"]
            assert len(runtimes) > 0, \
                f"Widget '{widget_name}' has no runtimes"
            for runtime_name, runtime_data in runtimes.items():
                assert "version" in runtime_data, \
                    f"Runtime '{widget_name}/{runtime_name}' missing 'version'"
                assert isinstance(runtime_data["version"], str), \
                    f"Runtime '{widget_name}/{runtime_name}' version is not a string"
        print(f"    All {len(widgets)} widgets have valid runtime structure")

    runner.run_test("manifest — widget structure validation", test_manifest_structure)

    # Cleanup & Summary
    success = runner.summary()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
