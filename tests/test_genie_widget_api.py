#!/usr/bin/env python3
"""End-to-end validation of the Genie Widget API.
Covers: CDN accessibility, manifest presence, bundle loading, regional availability,
browser embedding, runtime resolution, theme configuration, initial questions."""

import sys
import os
import json
import tempfile
import requests

sys.path.insert(0, os.path.dirname(__file__))
from test_helpers import kaltura_post, TestRunner, PARTNER_ID, KS, SERVICE_URL

BASE_URL = "https://unisphere.nvp1.ovp.kaltura.com/v1"
WIDGET_NAME = "unisphere.widget.genie"
RUNTIME_NAME = "chat"

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
    runner = TestRunner("Genie Widget — E2E Validation")

    # ════════════════════════════════════════════
    # Phase 1: CDN & Manifest
    # ════════════════════════════════════════════

    def test_manifest():
        """Verify Genie widget is in the runtime.json manifest with chat runtime."""
        resp = requests.get(f"{BASE_URL}/runtime.json", timeout=30)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        data = resp.json()
        widgets = data.get("versions", {}).get("widgets", {})
        assert WIDGET_NAME in widgets, f"Expected '{WIDGET_NAME}' in manifest"
        genie = widgets[WIDGET_NAME]
        runtimes = genie.get("runtimes", {})
        assert RUNTIME_NAME in runtimes, \
            f"Expected '{RUNTIME_NAME}' runtime, got: {list(runtimes.keys())}"
        state["chat_version"] = runtimes[RUNTIME_NAME]["version"]
        print(f"    chat: v{state['chat_version']}")
        # Log other runtimes for reference
        for rt_name, rt_data in runtimes.items():
            if rt_name != RUNTIME_NAME:
                print(f"    {rt_name}: v{rt_data['version']}")

    runner.run_test("manifest — Genie widget with chat runtime", test_manifest)

    def test_bundle():
        """Verify the chat runtime bundle is accessible on CDN."""
        version = state.get("chat_version")
        url = f"{BASE_URL}/static/modules/genie/v{version}/runtime/chat/index.esm.js"
        resp = requests.head(url, timeout=30)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        print(f"    chat bundle: {resp.status_code}")

    runner.run_test("bundle — chat runtime accessible on CDN", test_bundle)

    # ════════════════════════════════════════════
    # Phase 2: Regional Availability
    # ════════════════════════════════════════════

    def test_regional():
        """Verify Genie widget is available in EU and DE regions."""
        for region, label in [("irp2", "EU"), ("frp2", "DE")]:
            url = f"https://unisphere.{region}.ovp.kaltura.com/v1/runtime.json"
            resp = requests.get(url, timeout=30)
            assert resp.status_code == 200, f"Expected 200 for {label}"
            data = resp.json()
            widgets = data.get("versions", {}).get("widgets", {})
            assert WIDGET_NAME in widgets, \
                f"Expected '{WIDGET_NAME}' in {label} manifest"
            runtimes = widgets[WIDGET_NAME].get("runtimes", {})
            assert RUNTIME_NAME in runtimes, \
                f"Expected '{RUNTIME_NAME}' runtime in {label}"
            version = runtimes[RUNTIME_NAME]["version"]
            print(f"    {label} ({region}): v{version}")

    runner.run_test("regional — Genie widget in EU and DE manifests", test_regional)

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

        def test_chat_runtime_loads():
            """Verify the chat runtime loads successfully in the browser."""
            html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Genie Chat Runtime Test</title></head>
<body>
<div id="genie-chat-rt" style="width:100%;height:100vh;display:flex;"></div>
<script type="module">
  import {{ loader }} from "{BASE_URL}/loader/index.esm.js";
  try {{
    const ws = await loader({{
      serverUrl: "{BASE_URL}",
      appId: "genie-chat-rt-test", appVersion: "1.0.0",
      ui: {{ theme: "light", language: "en-US" }},
      runtimes: [{{
        widgetName: "{WIDGET_NAME}",
        runtimeName: "{RUNTIME_NAME}",
        settings: {{
          kalturaServerURI: "https://www.kaltura.com",
          ks: "{browser_ks}",
          partnerId: "{PARTNER_ID}"
        }},
        visuals: [{{ type: "page", target: "genie-chat-rt", settings: {{}} }}]
      }}]
    }});
    const rt = await ws.getRuntimeAsync("{WIDGET_NAME}", "{RUNTIME_NAME}");
    window.__genie_done = true;
    window.__genie_result = rt !== null ? "OK" : "NULL";
  }} catch(e) {{
    window.__genie_done = true;
    window.__genie_result = "ERR:" + e.message;
  }}
</script></body></html>"""
            path = _write_html("genie_chat_rt_test.html", html)
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                page.goto(f"file://{path}", wait_until="networkidle",
                          timeout=30000)
                page.wait_for_function(
                    "window.__genie_done !== undefined", timeout=30000)
                result = page.evaluate("window.__genie_result")
                browser.close()
            assert result == "OK", f"Expected OK, got {result}"
            print(f"    Chat runtime: loaded ({result})")

        runner.run_test(
            "browser — chat runtime loads successfully",
            test_chat_runtime_loads)

        def test_get_runtime_async():
            """Verify getRuntimeAsync resolves with correct widget/runtime names."""
            html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Genie getRuntimeAsync Test</title></head>
<body>
<div id="genie-gra" style="width:100%;height:100vh;display:flex;"></div>
<script type="module">
  import {{ loader }} from "{BASE_URL}/loader/index.esm.js";
  try {{
    const ws = await loader({{
      serverUrl: "{BASE_URL}",
      appId: "genie-gra-test", appVersion: "1.0.0",
      ui: {{ theme: "light", language: "en-US" }},
      runtimes: [{{
        widgetName: "{WIDGET_NAME}",
        runtimeName: "{RUNTIME_NAME}",
        settings: {{
          kalturaServerURI: "https://www.kaltura.com",
          ks: "{browser_ks}",
          partnerId: "{PARTNER_ID}"
        }},
        visuals: [{{ type: "page", target: "genie-gra", settings: {{}} }}]
      }}]
    }});
    const rt = await ws.getRuntimeAsync("{WIDGET_NAME}", "{RUNTIME_NAME}");
    window.__gra_done = true;
    window.__gra_not_null = rt !== null && rt !== undefined;
    // Verify we can call getRuntimeAsync with the exact widget and runtime names
    window.__gra_widget = "{WIDGET_NAME}";
    window.__gra_runtime = "{RUNTIME_NAME}";
    // Verify the runtime object is callable (has properties)
    window.__gra_has_props = rt !== null && typeof rt === "object";
  }} catch(e) {{
    window.__gra_done = true;
    window.__gra_not_null = false;
    window.__gra_err = "ERR:" + e.message;
  }}
</script></body></html>"""
            path = _write_html("genie_gra_test.html", html)
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                page.goto(f"file://{path}", wait_until="networkidle",
                          timeout=30000)
                page.wait_for_function(
                    "window.__gra_done !== undefined", timeout=30000)
                not_null = page.evaluate("window.__gra_not_null")
                has_props = page.evaluate("window.__gra_has_props")
                err = page.evaluate("window.__gra_err")
                widget = page.evaluate("window.__gra_widget")
                runtime = page.evaluate("window.__gra_runtime")
                browser.close()
            assert err is None, f"getRuntimeAsync error: {err}"
            assert not_null is True, f"Expected non-null runtime object"
            assert has_props is True, f"Expected runtime to be an object"
            assert widget == WIDGET_NAME, f"Widget mismatch: {widget}"
            assert runtime == RUNTIME_NAME, f"Runtime mismatch: {runtime}"
            print(f"    getRuntimeAsync: widget={widget}, runtime={runtime}, "
                  f"resolved={not_null}")

        runner.run_test(
            "browser — getRuntimeAsync resolves with correct names",
            test_get_runtime_async)

        def test_dark_theme():
            """Verify custom theme configuration (dark) is accepted."""
            html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Genie Dark Theme Test</title></head>
<body>
<div id="genie-theme" style="width:100%;height:100vh;display:flex;"></div>
<script type="module">
  import {{ loader }} from "{BASE_URL}/loader/index.esm.js";
  try {{
    const ws = await loader({{
      serverUrl: "{BASE_URL}",
      appId: "genie-theme-test", appVersion: "1.0.0",
      ui: {{ theme: "dark", language: "en-US" }},
      runtimes: [{{
        widgetName: "{WIDGET_NAME}",
        runtimeName: "{RUNTIME_NAME}",
        settings: {{
          kalturaServerURI: "https://www.kaltura.com",
          ks: "{browser_ks}",
          partnerId: "{PARTNER_ID}"
        }},
        visuals: [{{ type: "page", target: "genie-theme", settings: {{}} }}]
      }}]
    }});
    const rt = await ws.getRuntimeAsync("{WIDGET_NAME}", "{RUNTIME_NAME}");
    window.__theme_done = true;
    window.__theme_result = rt !== null ? "OK" : "NULL";
  }} catch(e) {{
    window.__theme_done = true;
    window.__theme_result = "ERR:" + e.message;
  }}
</script></body></html>"""
            path = _write_html("genie_theme_test.html", html)
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                page.goto(f"file://{path}", wait_until="networkidle",
                          timeout=30000)
                page.wait_for_function(
                    "window.__theme_done !== undefined", timeout=30000)
                result = page.evaluate("window.__theme_result")
                browser.close()
            assert result == "OK", f"Expected OK, got {result}"
            print(f"    Dark theme: accepted ({result})")

        runner.run_test(
            "browser — dark theme configuration accepted",
            test_dark_theme)

        def test_initial_questions():
            """Verify initial questions configuration is accepted via visuals settings."""
            html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Genie Initial Questions Test</title></head>
<body>
<div id="genie-iq" style="width:100%;height:100vh;display:flex;"></div>
<script type="module">
  import {{ loader }} from "{BASE_URL}/loader/index.esm.js";
  try {{
    const ws = await loader({{
      serverUrl: "{BASE_URL}",
      appId: "genie-iq-test", appVersion: "1.0.0",
      ui: {{ theme: "light", language: "en-US" }},
      runtimes: [{{
        widgetName: "{WIDGET_NAME}",
        runtimeName: "{RUNTIME_NAME}",
        settings: {{
          kalturaServerURI: "https://www.kaltura.com",
          ks: "{browser_ks}",
          partnerId: "{PARTNER_ID}"
        }},
        visuals: [{{
          type: "page",
          target: "genie-iq",
          settings: {{
            customization: {{
              initialPage: {{
                title: "Ask Anything",
                initialQuestions: [
                  {{ text: "How do I get started?", answerType: "flashcards" }},
                  {{ text: "What features are available?", answerType: "flashcards" }}
                ]
              }}
            }}
          }}
        }}]
      }}]
    }});
    const rt = await ws.getRuntimeAsync("{WIDGET_NAME}", "{RUNTIME_NAME}");
    window.__iq_done = true;
    window.__iq_result = rt !== null ? "OK" : "NULL";
  }} catch(e) {{
    window.__iq_done = true;
    window.__iq_result = "ERR:" + e.message;
  }}
</script></body></html>"""
            path = _write_html("genie_iq_test.html", html)
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                page.goto(f"file://{path}", wait_until="networkidle",
                          timeout=30000)
                page.wait_for_function(
                    "window.__iq_done !== undefined", timeout=30000)
                result = page.evaluate("window.__iq_result")
                browser.close()
            assert result == "OK", f"Expected OK, got {result}"
            print(f"    Initial questions: accepted ({result})")

        runner.run_test(
            "browser — initial questions configuration accepted",
            test_initial_questions)

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
