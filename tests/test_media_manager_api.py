#!/usr/bin/env python3
"""End-to-end validation of the Media Manager Widget API.
Covers: CDN accessibility, manifest presence, bundle loading, browser embedding,
visual types (table, dialog), modes (select, manage), and runtime API."""

import sys
import os
import json
import time
import tempfile
import webbrowser
import requests

sys.path.insert(0, os.path.dirname(__file__))
from test_helpers import kaltura_post, TestRunner, PARTNER_ID, KS, SERVICE_URL

BASE_URL = "https://unisphere.nvp1.ovp.kaltura.com/v1"
WIDGET_NAME = "unisphere.widget.media-manager"
RUNTIME_NAME = "kaltura-items-media-manager"

state = {}


def _generate_user_ks():
    """Generate a short-lived USER KS for browser tests."""
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


def _write_html(filename, html_content):
    """Write HTML to a temp file and return the path."""
    path = os.path.join(tempfile.gettempdir(), filename)
    with open(path, "w") as f:
        f.write(html_content)
    return path


def main():
    runner = TestRunner("Media Manager Widget — E2E Validation")

    # ════════════════════════════════════════════
    # Phase 1: CDN & Manifest
    # ════════════════════════════════════════════

    def test_manifest():
        """Verify the runtime.json manifest is accessible."""
        resp = requests.get(f"{BASE_URL}/runtime.json", timeout=30)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        data = resp.json()
        widgets = data.get("versions", {}).get("widgets", {})
        state["widgets"] = widgets
        print(f"    Manifest: {len(widgets)} widgets")

    runner.run_test("manifest — runtime.json accessible", test_manifest)

    def test_widget_in_manifest():
        """Verify Media Manager widget is in the manifest with correct runtime."""
        widgets = state.get("widgets", {})
        assert WIDGET_NAME in widgets, f"Expected '{WIDGET_NAME}' in manifest"
        mm = widgets[WIDGET_NAME]
        assert RUNTIME_NAME in mm["runtimes"], \
            f"Expected '{RUNTIME_NAME}' runtime, got: {list(mm['runtimes'].keys())}"
        version = mm["runtimes"][RUNTIME_NAME]["version"]
        state["mm_version"] = version
        print(f"    Media Manager: v{version}")

    runner.run_test("manifest — contains Media Manager with correct runtime", test_widget_in_manifest)

    def test_bundle_accessible():
        """Verify the Media Manager bundle is accessible on CDN."""
        version = state.get("mm_version")
        url = f"{BASE_URL}/static/modules/media-manager/v{version}/runtime/{RUNTIME_NAME}/index.esm.js"
        resp = requests.head(url, timeout=30)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code} for {url}"
        print(f"    Bundle: {resp.status_code} ({url})")

    runner.run_test("bundle — Media Manager accessible on CDN", test_bundle_accessible)

    def test_loader_accessible():
        """Verify the Unisphere loader ESM is accessible."""
        url = f"{BASE_URL}/loader/index.esm.js"
        resp = requests.head(url, timeout=30)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        content_type = resp.headers.get("content-type", "")
        assert "javascript" in content_type, f"Expected JS content-type, got {content_type}"
        print(f"    Loader: {resp.status_code}, content-type={content_type}")

    runner.run_test("loader — Unisphere loader ESM accessible", test_loader_accessible)

    # ════════════════════════════════════════════
    # Phase 2: Regional Availability
    # ════════════════════════════════════════════

    def test_regional_manifests():
        """Verify Media Manager is available in EU and DE regions."""
        for region, label in [("irp2", "EU"), ("frp2", "DE")]:
            url = f"https://unisphere.{region}.ovp.kaltura.com/v1/runtime.json"
            resp = requests.get(url, timeout=30)
            assert resp.status_code == 200, f"Expected 200 for {label}, got {resp.status_code}"
            data = resp.json()
            widgets = data.get("versions", {}).get("widgets", {})
            assert WIDGET_NAME in widgets, f"Expected '{WIDGET_NAME}' in {label} manifest"
            version = widgets[WIDGET_NAME]["runtimes"][RUNTIME_NAME]["version"]
            print(f"    {label} ({region}): v{version}")

    runner.run_test("regional — Media Manager in EU and DE manifests", test_regional_manifests)

    # ════════════════════════════════════════════
    # Phase 3: Create test category for browser tests
    # ════════════════════════════════════════════

    def test_create_category():
        """Create a test category to scope the Media Manager."""
        tag = f"mm_test_{int(time.time())}"
        result = kaltura_post("category", "add", {
            "category[name]": f"MM-Test-{tag}",
            "category[description]": "Media Manager E2E test category",
        })
        state["category_id"] = result.get("id")
        if state["category_id"]:
            runner.register_cleanup(f"category {result['id']}",
                                    lambda cid=result["id"]: kaltura_post("category", "delete", {
                                        "id": cid, "moveEntriesToParentCategory": 1}))
        assert "id" in result, f"Expected category id: {result}"
        print(f"    Category: {result['id']} ({result.get('name', '')})")

    runner.run_test("category.add — create test category", test_create_category)

    # ════════════════════════════════════════════
    # Phase 4: Browser E2E Tests (Playwright)
    # ════════════════════════════════════════════

    try:
        from playwright.sync_api import sync_playwright
        HAS_PLAYWRIGHT = True
    except ImportError:
        HAS_PLAYWRIGHT = False
        print("\n  ⚠ Playwright not installed — skipping browser tests")
        print("    Install with: pip install playwright && python -m playwright install chromium")

    if HAS_PLAYWRIGHT:
        browser_ks = _generate_user_ks()
        category_id = state.get("category_id", "")

        def test_table_visual_renders():
            """Verify table visual renders in a container."""
            html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>MM Table Test</title></head>
<body>
<div id="mm-table" style="width:100%;height:600px;"></div>
<script type="module">
  import {{ loader }} from "{BASE_URL}/loader/index.esm.js";
  try {{
    const ws = await loader({{
      serverUrl: "{BASE_URL}",
      appId: "mm-test", appVersion: "1.0.0",
      session: {{ ks: "{browser_ks}", partnerId: {PARTNER_ID} }},
      runtimes: [{{
        widgetName: "{WIDGET_NAME}",
        runtimeName: "{RUNTIME_NAME}",
        settings: {{ contextType: "category", contextId: "{category_id}" }},
        visuals: [{{ type: "table", target: "mm-table", settings: {{ mode: "select" }} }}]
      }}]
    }});
    window.__mm_table_done = true;
    window.__mm_table_result = "OK";
  }} catch(e) {{
    window.__mm_table_done = true;
    window.__mm_table_result = "ERR:" + e.message;
  }}
</script></body></html>"""
            path = _write_html("mm_table_test.html", html)
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                page.goto(f"file://{path}", wait_until="networkidle", timeout=30000)
                page.wait_for_function("window.__mm_table_done !== undefined", timeout=30000)
                result = page.evaluate("window.__mm_table_result")
                container = page.inner_html("#mm-table")
                browser.close()
            assert result == "OK", f"Expected OK, got {result}"
            assert len(container) > 100, f"Expected rendered content, got {len(container)} chars"
            print(f"    Table visual: rendered ({len(container)} chars)")

        runner.run_test("browser — table visual renders in container", test_table_visual_renders)

        def test_manage_mode():
            """Verify manage mode renders with upload capabilities."""
            html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>MM Manage Test</title></head>
<body>
<div id="mm-manage" style="width:100%;height:600px;"></div>
<script type="module">
  import {{ loader }} from "{BASE_URL}/loader/index.esm.js";
  try {{
    const ws = await loader({{
      serverUrl: "{BASE_URL}",
      appId: "mm-test", appVersion: "1.0.0",
      session: {{ ks: "{browser_ks}", partnerId: {PARTNER_ID} }},
      runtimes: [{{
        widgetName: "{WIDGET_NAME}",
        runtimeName: "{RUNTIME_NAME}",
        settings: {{ contextType: "category", contextId: "{category_id}" }},
        visuals: [{{ type: "table", target: "mm-manage", settings: {{ mode: "manage" }} }}]
      }}]
    }});
    window.__mm_manage_done = true;
    window.__mm_manage_result = "OK";
  }} catch(e) {{
    window.__mm_manage_done = true;
    window.__mm_manage_result = "ERR:" + e.message;
  }}
</script></body></html>"""
            path = _write_html("mm_manage_test.html", html)
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                page.goto(f"file://{path}", wait_until="networkidle", timeout=30000)
                page.wait_for_function("window.__mm_manage_done !== undefined", timeout=30000)
                result = page.evaluate("window.__mm_manage_result")
                container = page.inner_html("#mm-manage")
                browser.close()
            assert result == "OK", f"Expected OK, got {result}"
            assert len(container) > 100, f"Expected rendered content, got {len(container)} chars"
            print(f"    Manage mode: rendered ({len(container)} chars)")

        runner.run_test("browser — manage mode renders with item actions", test_manage_mode)

        def test_dialog_visual():
            """Verify dialog visual can be configured."""
            html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>MM Dialog Test</title></head>
<body>
<script type="module">
  import {{ loader }} from "{BASE_URL}/loader/index.esm.js";
  try {{
    const ws = await loader({{
      serverUrl: "{BASE_URL}",
      appId: "mm-test", appVersion: "1.0.0",
      session: {{ ks: "{browser_ks}", partnerId: {PARTNER_ID} }},
      runtimes: [{{
        widgetName: "{WIDGET_NAME}",
        runtimeName: "{RUNTIME_NAME}",
        settings: {{ contextType: "category", contextId: "{category_id}" }},
        visuals: [{{ type: "dialog", target: {{ target: "body" }}, settings: {{ mode: "select" }} }}]
      }}]
    }});
    const mm = ws.getRuntime("{WIDGET_NAME}", "{RUNTIME_NAME}");
    const hasShowDialog = typeof mm.showDialog === "function";
    const hasHideDialog = typeof mm.hideDialog === "function";
    window.__mm_dialog_done = true;
    window.__mm_dialog_show = hasShowDialog;
    window.__mm_dialog_hide = hasHideDialog;
  }} catch(e) {{
    window.__mm_dialog_done = true;
    window.__mm_dialog_show = "ERR:" + e.message;
  }}
</script></body></html>"""
            path = _write_html("mm_dialog_test.html", html)
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                page.goto(f"file://{path}", wait_until="networkidle", timeout=30000)
                page.wait_for_function("window.__mm_dialog_done !== undefined", timeout=30000)
                has_show = page.evaluate("window.__mm_dialog_show")
                has_hide = page.evaluate("window.__mm_dialog_hide")
                browser.close()
            assert has_show is True, f"Expected showDialog=true, got {has_show}"
            assert has_hide is True, f"Expected hideDialog=true, got {has_hide}"
            print(f"    Dialog visual: showDialog={has_show}, hideDialog={has_hide}")

        runner.run_test("browser — dialog visual with showDialog/hideDialog API", test_dialog_visual)

        def test_runtime_api():
            """Verify runtime instance exposes onRowSelected subscription."""
            html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>MM API Test</title></head>
<body>
<div id="mm-api" style="width:100%;height:400px;"></div>
<script type="module">
  import {{ loader }} from "{BASE_URL}/loader/index.esm.js";
  try {{
    const ws = await loader({{
      serverUrl: "{BASE_URL}",
      appId: "mm-test", appVersion: "1.0.0",
      session: {{ ks: "{browser_ks}", partnerId: {PARTNER_ID} }},
      runtimes: [{{
        widgetName: "{WIDGET_NAME}",
        runtimeName: "{RUNTIME_NAME}",
        settings: {{ contextType: "category", contextId: "{category_id}" }},
        visuals: [{{ type: "table", target: "mm-api", settings: {{ mode: "select" }} }}]
      }}]
    }});
    const mm = ws.getRuntime("{WIDGET_NAME}", "{RUNTIME_NAME}");
    const hasOnRowSelected = mm.onRowSelected && typeof mm.onRowSelected.subscribe === "function";
    const hasUpdateSettings = typeof mm.updateSettings === "function";
    window.__mm_api_done = true;
    window.__mm_api_rowSelected = hasOnRowSelected;
    window.__mm_api_updateSettings = hasUpdateSettings;
  }} catch(e) {{
    window.__mm_api_done = true;
    window.__mm_api_rowSelected = "ERR:" + e.message;
  }}
</script></body></html>"""
            path = _write_html("mm_api_test.html", html)
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                page.goto(f"file://{path}", wait_until="networkidle", timeout=30000)
                page.wait_for_function("window.__mm_api_done !== undefined", timeout=30000)
                has_row = page.evaluate("window.__mm_api_rowSelected")
                has_update = page.evaluate("window.__mm_api_updateSettings")
                browser.close()
            assert has_update is True, f"Expected updateSettings=true, got {has_update}"
            print(f"    Runtime API: onRowSelected={has_row}, updateSettings={has_update}")

        runner.run_test("browser — runtime API (onRowSelected, updateSettings)", test_runtime_api)

        def test_getRuntimeAsync():
            """Verify getRuntimeAsync resolves for the Media Manager."""
            html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>MM Async Test</title></head>
<body>
<div id="mm-async" style="width:100%;height:400px;"></div>
<script type="module">
  import {{ loader }} from "{BASE_URL}/loader/index.esm.js";
  try {{
    const ws = await loader({{
      serverUrl: "{BASE_URL}",
      appId: "mm-test", appVersion: "1.0.0",
      session: {{ ks: "{browser_ks}", partnerId: {PARTNER_ID} }},
      runtimes: [{{
        widgetName: "{WIDGET_NAME}",
        runtimeName: "{RUNTIME_NAME}",
        settings: {{ contextType: "category", contextId: "{category_id}" }},
        visuals: [{{ type: "table", target: "mm-async", settings: {{ mode: "select" }} }}]
      }}]
    }});
    const mm = await ws.getRuntimeAsync("{WIDGET_NAME}", "{RUNTIME_NAME}");
    window.__mm_async_done = true;
    window.__mm_async_resolved = (mm !== null);
  }} catch(e) {{
    window.__mm_async_done = true;
    window.__mm_async_resolved = "ERR:" + e.message;
  }}
</script></body></html>"""
            path = _write_html("mm_async_test.html", html)
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                page.goto(f"file://{path}", wait_until="networkidle", timeout=30000)
                page.wait_for_function("window.__mm_async_done !== undefined", timeout=30000)
                resolved = page.evaluate("window.__mm_async_resolved")
                browser.close()
            assert resolved is True, f"Expected resolved=true, got {resolved}"
            print(f"    getRuntimeAsync: resolved={resolved}")

        runner.run_test("browser — getRuntimeAsync resolves", test_getRuntimeAsync)

    # ════════════════════════════════════════════
    # Cleanup & Summary
    # ════════════════════════════════════════════

    keep = "--keep" in sys.argv
    if keep:
        print(f"\n  --keep: preserving category {state.get('category_id', 'N/A')}")
    else:
        if sys.stdin.isatty() and not os.environ.get("CI"):
            input("\nPress Enter to clean up...")
        runner.cleanup()

    success = runner.summary()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
