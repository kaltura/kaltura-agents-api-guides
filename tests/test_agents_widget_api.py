#!/usr/bin/env python3
"""End-to-end validation of the Agents Widget API.
Covers: CDN accessibility, manifest presence, bundle loading, browser embedding,
drawer open/close API, categoryId setting."""

import sys
import os
import json
import tempfile
import requests

sys.path.insert(0, os.path.dirname(__file__))
from test_helpers import kaltura_post, TestRunner, PARTNER_ID, KS, SERVICE_URL

BASE_URL = "https://unisphere.nvp1.ovp.kaltura.com/v1"
WIDGET_NAME = "unisphere.widget.agents"
AGENTS_URL = os.environ.get("KALTURA_AGENTS_MANAGER_URL",
                            "https://agents-manager.nvp1.ovp.kaltura.com")

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
    runner = TestRunner("Agents Widget — E2E Validation")

    # ════════════════════════════════════════════
    # Phase 1: CDN & Manifest
    # ════════════════════════════════════════════

    def test_manifest():
        """Verify Agents widget is in the runtime.json manifest."""
        resp = requests.get(f"{BASE_URL}/runtime.json", timeout=30)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        data = resp.json()
        widgets = data.get("versions", {}).get("widgets", {})
        assert WIDGET_NAME in widgets, f"Expected '{WIDGET_NAME}' in manifest"
        agents = widgets[WIDGET_NAME]
        runtimes = agents.get("runtimes", {})
        assert "manager" in runtimes, f"Expected 'manager' runtime"
        state["manager_version"] = runtimes["manager"]["version"]
        print(f"    manager: v{state['manager_version']}")

    runner.run_test("manifest — Agents widget with manager runtime", test_manifest)

    def test_bundle():
        """Verify the manager bundle is accessible on CDN."""
        version = state.get("manager_version")
        url = f"{BASE_URL}/static/modules/agents/v{version}/runtime/manager/index.esm.js"
        resp = requests.head(url, timeout=30)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        print(f"    manager bundle: {resp.status_code}")

    runner.run_test("bundle — manager runtime accessible on CDN", test_bundle)

    # ════════════════════════════════════════════
    # Phase 2: Regional Availability
    # ════════════════════════════════════════════

    def test_regional():
        """Verify Agents widget is available in EU and DE regions."""
        for region, label in [("irp2", "EU"), ("frp2", "DE")]:
            url = f"https://unisphere.{region}.ovp.kaltura.com/v1/runtime.json"
            resp = requests.get(url, timeout=30)
            assert resp.status_code == 200, f"Expected 200 for {label}"
            data = resp.json()
            widgets = data.get("versions", {}).get("widgets", {})
            assert WIDGET_NAME in widgets, \
                f"Expected '{WIDGET_NAME}' in {label} manifest"
            version = widgets[WIDGET_NAME]["runtimes"]["manager"]["version"]
            print(f"    {label} ({region}): v{version}")

    runner.run_test("regional — Agents widget in EU and DE manifests", test_regional)

    # ════════════════════════════════════════════
    # Phase 3: Agents Manager Backend
    # ════════════════════════════════════════════

    def test_agents_backend():
        """Verify the Agents Manager backend is accessible."""
        resp = requests.post(
            f"{AGENTS_URL}/api/v1/actionDefinition/list",
            headers={
                "Authorization": f"Bearer {KS}",
                "Content-Type": "application/json",
            },
            json={"partnerId": str(PARTNER_ID)},
            timeout=30,
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        data = resp.json()
        total = data.get("totalCount", 0)
        print(f"    Action definitions: {total} types available")
        if total > 0:
            types = [obj.get("type", "?") for obj in data.get("objects", [])]
            print(f"    Types: {', '.join(types[:8])}")

    runner.run_test("backend — Agents Manager action definitions accessible",
                    test_agents_backend)

    # ════════════════════════════════════════════
    # Phase 4: Browser E2E Tests (Playwright)
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
            """Verify the manager runtime loads in the browser."""
            html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Agents Runtime Test</title></head>
<body>
<div id="agents-rt" style="width:100%;height:100vh;"></div>
<script type="module">
  import {{ loader }} from "{BASE_URL}/loader/index.esm.js";
  try {{
    const ws = await loader({{
      serverUrl: "{BASE_URL}",
      appId: "agents-rt-test", appVersion: "1.0.0",
      session: {{ ks: "{browser_ks}", partnerId: {PARTNER_ID} }},
      runtimes: [{{
        widgetName: "{WIDGET_NAME}",
        runtimeName: "manager",
        settings: {{
          ks: "{browser_ks}",
          pid: "{PARTNER_ID}",
          agentsServiceURI: "{AGENTS_URL}",
          kalturaServerURI: "https://www.kaltura.com",
          analyticsServerURI: "analytics.kaltura.com",
          hostAppName: 1
        }},
        visuals: [{{ type: "drawer", target: "agents-rt", settings: {{}} }}]
      }}]
    }});
    const rt = await ws.getRuntimeAsync("{WIDGET_NAME}", "manager");
    window.__agents_done = true;
    window.__agents_result = rt !== null ? "OK" : "NULL";
    window.__has_openDrawer = rt !== null && typeof rt.openDrawer === "function";
    window.__has_closeDrawer = rt !== null && typeof rt.closeDrawer === "function";
  }} catch(e) {{
    window.__agents_done = true;
    window.__agents_result = "ERR:" + e.message;
  }}
</script></body></html>"""
            path = _write_html("agents_rt_test.html", html)
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                page.goto(f"file://{path}", wait_until="networkidle",
                          timeout=30000)
                page.wait_for_function(
                    "window.__agents_done !== undefined", timeout=30000)
                result = page.evaluate("window.__agents_result")
                has_open = page.evaluate("window.__has_openDrawer")
                has_close = page.evaluate("window.__has_closeDrawer")
                browser.close()
            assert result == "OK", f"Expected OK, got {result}"
            assert has_open is True, f"Expected openDrawer method"
            assert has_close is True, f"Expected closeDrawer method"
            print(f"    Runtime: loaded, openDrawer={has_open}, "
                  f"closeDrawer={has_close}")

        runner.run_test(
            "browser — manager runtime loads with openDrawer/closeDrawer API",
            test_runtime_loads)

        def test_drawer_open_close():
            """Verify openDrawer and closeDrawer toggle the drawer state."""
            html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Agents Drawer Test</title></head>
<body>
<div id="agents-drawer" style="width:100%;height:100vh;"></div>
<script type="module">
  import {{ loader }} from "{BASE_URL}/loader/index.esm.js";
  try {{
    const ws = await loader({{
      serverUrl: "{BASE_URL}",
      appId: "agents-drawer-test", appVersion: "1.0.0",
      session: {{ ks: "{browser_ks}", partnerId: {PARTNER_ID} }},
      runtimes: [{{
        widgetName: "{WIDGET_NAME}",
        runtimeName: "manager",
        settings: {{
          ks: "{browser_ks}",
          pid: "{PARTNER_ID}",
          agentsServiceURI: "{AGENTS_URL}",
          kalturaServerURI: "https://www.kaltura.com",
          analyticsServerURI: "analytics.kaltura.com",
          hostAppName: 1
        }},
        visuals: [{{ type: "drawer", target: "agents-drawer", settings: {{}} }}]
      }}]
    }});
    const rt = await ws.getRuntimeAsync("{WIDGET_NAME}", "manager");

    // Test open
    rt.openDrawer();
    await new Promise(r => setTimeout(r, 500));
    window.__is_open = rt._isDrawerOpen === true;

    // Test close
    rt.closeDrawer();
    await new Promise(r => setTimeout(r, 500));
    window.__is_closed = rt._isDrawerOpen !== true;

    window.__drawer_done = true;
  }} catch(e) {{
    window.__drawer_done = true;
    window.__drawer_err = "ERR:" + e.message;
  }}
</script></body></html>"""
            path = _write_html("agents_drawer_test.html", html)
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                page.goto(f"file://{path}", wait_until="networkidle",
                          timeout=30000)
                page.wait_for_function(
                    "window.__drawer_done !== undefined", timeout=30000)
                err = page.evaluate("window.__drawer_err")
                is_open = page.evaluate("window.__is_open")
                is_closed = page.evaluate("window.__is_closed")
                browser.close()
            assert err is None, f"Drawer test error: {err}"
            assert is_open is True, f"Expected drawer open, got {is_open}"
            assert is_closed is True, f"Expected drawer closed, got {is_closed}"
            print(f"    openDrawer: open={is_open}, closeDrawer: closed="
                  f"{is_closed}")

        runner.run_test("browser — openDrawer/closeDrawer toggle drawer state",
                        test_drawer_open_close)

        def test_category_scoped():
            """Verify runtime loads with categoryId setting."""
            html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Agents Category Test</title></head>
<body>
<div id="agents-cat" style="width:100%;height:100vh;"></div>
<script type="module">
  import {{ loader }} from "{BASE_URL}/loader/index.esm.js";
  try {{
    const ws = await loader({{
      serverUrl: "{BASE_URL}",
      appId: "agents-cat-test", appVersion: "1.0.0",
      session: {{ ks: "{browser_ks}", partnerId: {PARTNER_ID} }},
      runtimes: [{{
        widgetName: "{WIDGET_NAME}",
        runtimeName: "manager",
        settings: {{
          ks: "{browser_ks}",
          pid: "{PARTNER_ID}",
          agentsServiceURI: "{AGENTS_URL}",
          kalturaServerURI: "https://www.kaltura.com",
          analyticsServerURI: "analytics.kaltura.com",
          hostAppName: 1,
          categoryId: "0"
        }},
        visuals: [{{ type: "drawer", target: "agents-cat", settings: {{}} }}]
      }}]
    }});
    const rt = await ws.getRuntimeAsync("{WIDGET_NAME}", "manager");
    window.__cat_done = true;
    window.__cat_result = rt !== null ? "OK" : "NULL";
    window.__cat_has_open = rt !== null && typeof rt.openDrawer === "function";
  }} catch(e) {{
    window.__cat_done = true;
    window.__cat_result = "ERR:" + e.message;
  }}
</script></body></html>"""
            path = _write_html("agents_cat_test.html", html)
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                page.goto(f"file://{path}", wait_until="networkidle",
                          timeout=30000)
                page.wait_for_function(
                    "window.__cat_done !== undefined", timeout=30000)
                result = page.evaluate("window.__cat_result")
                has_open = page.evaluate("window.__cat_has_open")
                browser.close()
            assert result == "OK", f"Expected OK, got {result}"
            assert has_open is True, f"Expected openDrawer with categoryId"
            print(f"    categoryId scoped: loaded={result}, "
                  f"openDrawer={has_open}")

        runner.run_test(
            "browser — runtime loads with categoryId setting",
            test_category_scoped)

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
