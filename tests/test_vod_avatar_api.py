#!/usr/bin/env python3
"""End-to-end validation of the VOD Avatar Studio API.
Covers: CDN accessibility, manifest presence, bundle loading, browser embedding,
runtime settings validation, studio loading."""

import sys
import os
import json
import tempfile
import requests

sys.path.insert(0, os.path.dirname(__file__))
from test_helpers import kaltura_post, TestRunner, PARTNER_ID, KS, SERVICE_URL

BASE_URL = "https://unisphere.nvp1.ovp.kaltura.com/v1"
WIDGET_NAME = "unisphere.widget.vod-avatars"

state = {}


def _generate_user_ks():
    """Generate a short-lived admin KS for browser tests."""
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
    runner = TestRunner("VOD Avatar Studio — E2E Validation")

    # ════════════════════════════════════════════
    # Phase 1: CDN & Manifest
    # ════════════════════════════════════════════

    def test_manifest():
        """Verify VOD Avatar widget is in the runtime.json manifest."""
        resp = requests.get(f"{BASE_URL}/runtime.json", timeout=30)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        data = resp.json()
        widgets = data.get("versions", {}).get("widgets", {})
        assert WIDGET_NAME in widgets, f"Expected '{WIDGET_NAME}' in manifest"
        va = widgets[WIDGET_NAME]
        runtimes = va.get("runtimes", {})
        assert "studio" in runtimes, f"Expected 'studio' runtime"
        state["studio_version"] = runtimes["studio"]["version"]
        print(f"    studio: v{state['studio_version']}")

    runner.run_test("manifest — VOD Avatar widget with studio runtime",
                    test_manifest)

    def test_bundle():
        """Verify the studio bundle is accessible on CDN."""
        version = state.get("studio_version")
        url = (f"{BASE_URL}/static/modules/vod-avatars/v{version}"
               f"/runtime/studio/index.esm.js")
        resp = requests.head(url, timeout=30)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        print(f"    studio bundle: {resp.status_code}")

    runner.run_test("bundle — studio runtime accessible on CDN", test_bundle)

    # ════════════════════════════════════════════
    # Phase 2: Regional Availability
    # ════════════════════════════════════════════

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

    runner.run_test("regional — VOD Avatar in EU and DE manifests",
                    test_regional)

    # ════════════════════════════════════════════
    # Phase 3: Browser E2E Tests (Playwright)
    # ════════════════════════════════════════════

    try:
        from playwright.sync_api import sync_playwright
        HAS_PLAYWRIGHT = True
    except ImportError:
        HAS_PLAYWRIGHT = False
        print("\n  ⚠ Playwright not installed — skipping browser tests")

    if HAS_PLAYWRIGHT:
        browser_ks = _generate_user_ks()

        def test_runtime_loads():
            """Verify the studio runtime loads in the browser."""
            html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>VOD Avatar Test</title></head>
<body>
<div id="va-studio" style="width:100%;height:100vh;"></div>
<script type="module">
  import {{ loader }} from "{BASE_URL}/loader/index.esm.js";
  try {{
    const ws = await loader({{
      serverUrl: "{BASE_URL}",
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
    window.__va_has_update = rt !== null && typeof rt.updateSettings === "function";
    window.__va_has_kill = rt !== null && typeof rt.kill === "function";
  }} catch(e) {{
    window.__va_done = true;
    window.__va_result = "ERR:" + e.message;
  }}
</script></body></html>"""
            path = _write_html("va_rt_test.html", html)
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                page.goto(f"file://{path}", wait_until="networkidle",
                          timeout=30000)
                page.wait_for_function(
                    "window.__va_done !== undefined", timeout=30000)
                result = page.evaluate("window.__va_result")
                has_update = page.evaluate("window.__va_has_update")
                has_kill = page.evaluate("window.__va_has_kill")
                browser.close()
            assert result == "OK", f"Expected OK, got {result}"
            assert has_update is True, f"Expected updateSettings method"
            print(f"    Studio runtime: loaded, updateSettings={has_update}, "
                  f"kill={has_kill}")

        runner.run_test("browser — studio runtime loads successfully",
                        test_runtime_loads)

        def test_settings_validation():
            """Verify partnerId must be a number (not string)."""
            html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>VOD Avatar Settings</title></head>
<body>
<div id="va-settings" style="width:100%;height:100vh;"></div>
<script type="module">
  import {{ loader }} from "{BASE_URL}/loader/index.esm.js";

  window.__validation_warns = [];
  const origWarn = console.warn;
  console.warn = function() {{
    window.__validation_warns.push(Array.from(arguments).map(a => {{
      try {{ return typeof a === 'object' ? JSON.stringify(a) : String(a); }}
      catch(e) {{ return String(a); }}
    }}).join(' '));
    origWarn.apply(console, arguments);
  }};

  try {{
    // Intentionally use string partnerId — should fail validation
    const ws = await loader({{
      serverUrl: "{BASE_URL}",
      appId: "va-settings-test", appVersion: "1.0.0",
      session: {{ ks: "{browser_ks}", partnerId: {PARTNER_ID} }},
      runtimes: [{{
        widgetName: "{WIDGET_NAME}",
        runtimeName: "studio",
        settings: {{
          ks: "{browser_ks}",
          partnerId: "{PARTNER_ID}",
          kalturaServerURI: "https://www.kaltura.com"
        }},
        visuals: [{{ type: "page", target: "va-settings", settings: {{}} }}]
      }}]
    }});
    const rt = await ws.getRuntimeAsync("{WIDGET_NAME}", "studio");
    window.__sv_done = true;
    window.__sv_result = rt !== null ? "LOADED" : "REJECTED";
    window.__sv_has_validation = window.__validation_warns.some(
      w => w.includes("Expected number") || w.includes("Validation")
    );
  }} catch(e) {{
    window.__sv_done = true;
    window.__sv_result = "ERR:" + e.message;
  }}
</script></body></html>"""
            path = _write_html("va_settings_test.html", html)
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                page.goto(f"file://{path}", wait_until="networkidle",
                          timeout=30000)
                page.wait_for_function(
                    "window.__sv_done !== undefined", timeout=30000)
                result = page.evaluate("window.__sv_result")
                has_warn = page.evaluate("window.__sv_has_validation")
                browser.close()
            # String partnerId should be rejected
            assert result == "REJECTED", \
                f"Expected REJECTED with string partnerId, got {result}"
            assert has_warn is True, \
                f"Expected validation warning for string partnerId"
            print(f"    String partnerId: correctly rejected with "
                  f"validation warning")

        runner.run_test(
            "browser — partnerId type validation (number required)",
            test_settings_validation)

        def test_getRuntimeAsync():
            """Verify getRuntimeAsync resolves with studio runtime."""
            html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>VOD Avatar Async</title></head>
<body>
<div id="va-async" style="width:100%;height:100vh;"></div>
<script type="module">
  import {{ loader }} from "{BASE_URL}/loader/index.esm.js";
  try {{
    const ws = await loader({{
      serverUrl: "{BASE_URL}",
      appId: "va-async-test", appVersion: "1.0.0",
      session: {{ ks: "{browser_ks}", partnerId: {PARTNER_ID} }},
      runtimes: [{{
        widgetName: "{WIDGET_NAME}",
        runtimeName: "studio",
        settings: {{
          ks: "{browser_ks}",
          partnerId: {PARTNER_ID},
          kalturaServerURI: "https://www.kaltura.com"
        }},
        visuals: [{{ type: "page", target: "va-async", settings: {{}} }}]
      }}]
    }});
    const rt = await ws.getRuntimeAsync("{WIDGET_NAME}", "studio");
    window.__async_done = true;
    window.__async_widget = rt !== null ? rt.widgetName : "null";
    window.__async_runtime = rt !== null ? rt.runtimeName : "null";
  }} catch(e) {{
    window.__async_done = true;
    window.__async_err = e.message;
  }}
</script></body></html>"""
            path = _write_html("va_async_test.html", html)
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                page.goto(f"file://{path}", wait_until="networkidle",
                          timeout=30000)
                page.wait_for_function(
                    "window.__async_done !== undefined", timeout=30000)
                widget = page.evaluate("window.__async_widget")
                runtime = page.evaluate("window.__async_runtime")
                err = page.evaluate("window.__async_err")
                browser.close()
            assert err is None, f"getRuntimeAsync error: {err}"
            assert widget == WIDGET_NAME, \
                f"Expected widgetName={WIDGET_NAME}, got {widget}"
            assert runtime == "studio", \
                f"Expected runtimeName=studio, got {runtime}"
            print(f"    getRuntimeAsync: widgetName={widget}, "
                  f"runtimeName={runtime}")

        runner.run_test("browser — getRuntimeAsync resolves with correct "
                        "widget/runtime names", test_getRuntimeAsync)

    # ════════════════════════════════════════════
    # Cleanup & Summary
    # ════════════════════════════════════════════

    keep = "--keep" in sys.argv
    if not keep:
        if sys.stdin.isatty() and not os.environ.get("CI"):
            input("\nPress Enter to clean up...")
        runner.cleanup()

    success = runner.summary()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
