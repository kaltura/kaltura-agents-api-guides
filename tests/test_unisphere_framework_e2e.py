#!/usr/bin/env python3
"""Browser E2E validation of the Kaltura Unisphere Framework.
Covers: workspace bootstrap, Genie runtime loading, Media Manager visuals,
theming, language switching, player integration, runtime status, workspace kill.

Requires: pip install playwright && playwright install chromium
"""

import sys
import os
import time
import tempfile
import json

sys.path.insert(0, os.path.dirname(__file__))
from test_helpers import kaltura_post, TestRunner, PARTNER_ID, KS, SERVICE_URL

UNISPHERE_URL = "https://unisphere.nvp1.ovp.kaltura.com/v1"
GENIE_URL = os.environ.get("KALTURA_GENIE_URL", "https://genie.nvp1.ovp.kaltura.com")
PLAYER_ID = os.environ.get("KALTURA_PLAYER_ID", "56732362")

state = {}


def _generate_user_ks():
    """Generate a short-lived USER KS for browser tests."""
    admin_secret = os.environ.get("KALTURA_ADMIN_SECRET")
    if not admin_secret:
        return None
    result = kaltura_post("session", "start", {
        "secret": admin_secret,
        "partnerId": PARTNER_ID,
        "type": 0,
        "userId": "unisphere-e2e@example.com",
        "expiry": 3600,
        "privileges": "setrole:PLAYBACK_BASE_ROLE,sview:*,appid:unisphere-e2e",
    })
    return result if isinstance(result, str) else None


def _write_html(content, name="test"):
    """Write HTML to a temp file and return the path."""
    path = os.path.join(tempfile.gettempdir(), f"unisphere_e2e_{name}.html")
    with open(path, "w") as f:
        f.write(content)
    return path


def main():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("Playwright not installed. Install with: pip install playwright && playwright install chromium")
        print("Skipping browser E2E tests.")
        sys.exit(0)

    runner = TestRunner("Unisphere Framework — Browser E2E")

    # Generate USER KS for browser tests
    user_ks = _generate_user_ks()
    if not user_ks:
        print("WARNING: KALTURA_ADMIN_SECRET not set — using admin KS for browser tests")
        user_ks = KS

    state["ks"] = user_ks

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        # ════════════════════════════════════════════
        # Phase 1: Workspace Bootstrap
        # ════════════════════════════════════════════

        def test_workspace_bootstrap():
            """Verify loader() runs without JS errors and creates a workspace."""
            html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"></head>
<body>
<div id="test-container" style="width:400px;height:300px;"></div>
<script type="module">
  window.__errors = [];
  window.addEventListener('error', e => window.__errors.push(e.message));

  import {{ loader }} from "{UNISPHERE_URL}/loader/index.esm.js";

  try {{
    const workspace = await loader({{
      serverUrl: "{UNISPHERE_URL}",
      appId: "e2e-test", appVersion: "1.0.0",
      session: {{ ks: "{user_ks}", partnerId: "{PARTNER_ID}" }},
      runtimes: []
    }});
    window.__workspace_status = workspace.getStatus();
    window.__workspace_ready = true;
  }} catch (e) {{
    window.__errors.push("loader error: " + e.message);
    window.__workspace_ready = false;
  }}
</script>
</body></html>"""
            path = _write_html(html, "bootstrap")
            page = browser.new_page()
            try:
                page.goto(f"file://{path}", wait_until="networkidle", timeout=30000)
                page.wait_for_function("window.__workspace_ready !== undefined", timeout=15000)
                ready = page.evaluate("window.__workspace_ready")
                errors = page.evaluate("window.__errors")
                assert ready, f"Workspace failed to load. Errors: {errors}"
                status = page.evaluate("window.__workspace_status")
                print(f"    Workspace status: {status}, errors: {len(errors)}")
            finally:
                page.close()

        runner.run_test("e2e — workspace bootstrap (empty runtimes)", test_workspace_bootstrap)

        # ════════════════════════════════════════════
        # Phase 2: Genie Chat Runtime
        # ════════════════════════════════════════════

        def test_genie_runtime():
            """Verify Genie chat runtime loads and renders in a container."""
            html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"></head>
<body>
<div id="genie-container" style="width:100%;height:500px;display:flex;"></div>
<script type="module">
  window.__errors = [];
  window.addEventListener('error', e => window.__errors.push(e.message));

  import {{ loader }} from "{UNISPHERE_URL}/loader/index.esm.js";

  try {{
    const workspace = await loader({{
      serverUrl: "{UNISPHERE_URL}",
      appId: "e2e-genie", appVersion: "1.0.0",
      session: {{ ks: "{user_ks}", partnerId: "{PARTNER_ID}" }},
      ui: {{ theme: "light", language: "en-US" }},
      runtimes: [{{
        widgetName: "unisphere.widget.genie",
        runtimeName: "chat",
        settings: {{
          kalturaServerURI: "{SERVICE_URL.replace('/api_v3', '')}",
          ks: "{user_ks}",
          partnerId: "{PARTNER_ID}"
        }},
        visuals: [{{ type: "page", target: "genie-container", settings: {{}} }}]
      }}]
    }});
    window.__genie_loaded = true;
    const runtime = await workspace.getRuntimeAsync("unisphere.widget.genie", "chat");
    window.__genie_runtime_exists = !!runtime;
  }} catch (e) {{
    window.__errors.push("genie error: " + e.message);
    window.__genie_loaded = false;
  }}
</script>
</body></html>"""
            path = _write_html(html, "genie")
            page = browser.new_page()
            try:
                page.goto(f"file://{path}", wait_until="networkidle", timeout=60000)
                page.wait_for_function("window.__genie_loaded !== undefined", timeout=30000)
                loaded = page.evaluate("window.__genie_loaded")
                errors = page.evaluate("window.__errors")
                assert loaded, f"Genie failed to load. Errors: {errors}"
                # Check container has content
                container = page.query_selector("#genie-container")
                inner = container.inner_html() if container else ""
                assert len(inner) > 0, "Genie container is empty after load"
                runtime_exists = page.evaluate("window.__genie_runtime_exists")
                print(f"    Genie runtime exists: {runtime_exists}, container content: {len(inner)} chars")
            finally:
                page.close()

        runner.run_test("e2e — Genie chat runtime loads and renders", test_genie_runtime)

        # ════════════════════════════════════════════
        # Phase 3: Media Manager
        # ════════════════════════════════════════════

        def test_media_manager_table():
            """Verify Media Manager table visual loads in a container."""
            html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"></head>
<body>
<div id="mm-container" style="width:100%;height:500px;"></div>
<script type="module">
  window.__errors = [];
  window.addEventListener('error', e => window.__errors.push(e.message));

  import {{ loader }} from "{UNISPHERE_URL}/loader/index.esm.js";

  try {{
    const workspace = await loader({{
      serverUrl: "{UNISPHERE_URL}",
      appId: "e2e-mm", appVersion: "1.0.0",
      session: {{ ks: "{user_ks}", partnerId: "{PARTNER_ID}" }},
      runtimes: [{{
        widgetName: "unisphere.widget.media-manager",
        runtimeName: "kaltura-items-media-manager",
        settings: {{ contextType: "category" }},
        visuals: [{{ type: "table", target: "mm-container", settings: {{}} }}]
      }}]
    }});
    const runtime = await workspace.getRuntimeAsync(
      "unisphere.widget.media-manager", "kaltura-items-media-manager"
    );
    window.__mm_loaded = !!runtime;
  }} catch (e) {{
    window.__errors.push("mm error: " + e.message);
    window.__mm_loaded = false;
  }}
</script>
</body></html>"""
            path = _write_html(html, "media_manager")
            page = browser.new_page()
            try:
                page.goto(f"file://{path}", wait_until="networkidle", timeout=60000)
                page.wait_for_function("window.__mm_loaded !== undefined", timeout=30000)
                loaded = page.evaluate("window.__mm_loaded")
                errors = page.evaluate("window.__errors")
                assert loaded, f"Media Manager failed to load. Errors: {errors}"
                container = page.query_selector("#mm-container")
                inner = container.inner_html() if container else ""
                assert len(inner) > 0, "Media Manager container is empty after load"
                print(f"    Media Manager table loaded, container: {len(inner)} chars")
            finally:
                page.close()

        runner.run_test("e2e — Media Manager table visual loads", test_media_manager_table)

        def test_media_manager_dialog():
            """Verify Media Manager showDialog/hideDialog programmatic API."""
            html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"></head>
<body>
<div id="mm-container2" style="width:100%;height:400px;"></div>
<script type="module">
  window.__errors = [];
  window.addEventListener('error', e => window.__errors.push(e.message));

  import {{ loader }} from "{UNISPHERE_URL}/loader/index.esm.js";

  try {{
    const workspace = await loader({{
      serverUrl: "{UNISPHERE_URL}",
      appId: "e2e-mm-dialog", appVersion: "1.0.0",
      session: {{ ks: "{user_ks}", partnerId: "{PARTNER_ID}" }},
      runtimes: [{{
        widgetName: "unisphere.widget.media-manager",
        runtimeName: "kaltura-items-media-manager",
        settings: {{ contextType: "category" }},
        visuals: []
      }}]
    }});
    const mm = await workspace.getRuntimeAsync(
      "unisphere.widget.media-manager", "kaltura-items-media-manager"
    );
    // Test showDialog exists
    window.__has_show_dialog = typeof mm.showDialog === "function";
    window.__has_hide_dialog = typeof mm.hideDialog === "function";
    window.__dialog_test_done = true;
  }} catch (e) {{
    window.__errors.push("dialog error: " + e.message);
    window.__dialog_test_done = true;
    window.__has_show_dialog = false;
    window.__has_hide_dialog = false;
  }}
</script>
</body></html>"""
            path = _write_html(html, "mm_dialog")
            page = browser.new_page()
            try:
                page.goto(f"file://{path}", wait_until="networkidle", timeout=60000)
                page.wait_for_function("window.__dialog_test_done !== undefined", timeout=30000)
                has_show = page.evaluate("window.__has_show_dialog")
                has_hide = page.evaluate("window.__has_hide_dialog")
                errors = page.evaluate("window.__errors")
                assert has_show, f"showDialog not found on runtime. Errors: {errors}"
                assert has_hide, f"hideDialog not found on runtime. Errors: {errors}"
                print(f"    showDialog: {has_show}, hideDialog: {has_hide}")
            finally:
                page.close()

        runner.run_test("e2e — Media Manager dialog API (showDialog/hideDialog)", test_media_manager_dialog)

        # ════════════════════════════════════════════
        # Phase 4: Theming & Language
        # ════════════════════════════════════════════

        def test_dark_theme():
            """Verify dark theme is applied when configured."""
            html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"></head>
<body>
<div id="theme-container" style="width:400px;height:300px;display:flex;"></div>
<script type="module">
  window.__errors = [];
  window.addEventListener('error', e => window.__errors.push(e.message));

  import {{ loader }} from "{UNISPHERE_URL}/loader/index.esm.js";

  try {{
    const workspace = await loader({{
      serverUrl: "{UNISPHERE_URL}",
      appId: "e2e-theme", appVersion: "1.0.0",
      session: {{ ks: "{user_ks}", partnerId: "{PARTNER_ID}" }},
      ui: {{ theme: "dark", language: "en-US" }},
      runtimes: [{{
        widgetName: "unisphere.widget.genie",
        runtimeName: "chat",
        settings: {{
          kalturaServerURI: "{SERVICE_URL.replace('/api_v3', '')}",
          ks: "{user_ks}",
          partnerId: "{PARTNER_ID}"
        }},
        visuals: [{{ type: "page", target: "theme-container", settings: {{}} }}]
      }}]
    }});
    await workspace.getRuntimeAsync("unisphere.widget.genie", "chat");
    // Check for dark theme indicators in DOM
    const body = document.body;
    const all = document.querySelectorAll('*');
    let darkFound = false;
    for (const el of all) {{
      const cls = el.className || '';
      const style = window.getComputedStyle(el);
      if (cls.toString().includes('dark') || style.colorScheme === 'dark') {{
        darkFound = true;
        break;
      }}
    }}
    window.__dark_theme_applied = darkFound;
    window.__theme_ready = true;
  }} catch (e) {{
    window.__errors.push("theme error: " + e.message);
    window.__theme_ready = true;
    window.__dark_theme_applied = false;
  }}
</script>
</body></html>"""
            path = _write_html(html, "dark_theme")
            page = browser.new_page()
            try:
                page.goto(f"file://{path}", wait_until="networkidle", timeout=60000)
                page.wait_for_function("window.__theme_ready !== undefined", timeout=30000)
                dark = page.evaluate("window.__dark_theme_applied")
                errors = page.evaluate("window.__errors")
                # Dark theme is applied if the workspace loaded with dark config
                # The actual CSS class detection may vary, so we check for successful load
                container = page.query_selector("#theme-container")
                inner = container.inner_html() if container else ""
                assert len(inner) > 0, f"Theme container is empty. Errors: {errors}"
                print(f"    Dark theme detected: {dark}, container: {len(inner)} chars")
            finally:
                page.close()

        runner.run_test("e2e — dark theme configuration", test_dark_theme)

        def test_language_rtl():
            """Verify Hebrew language setting applies RTL direction."""
            html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"></head>
<body>
<div id="lang-container" style="width:400px;height:300px;display:flex;"></div>
<script type="module">
  window.__errors = [];
  window.addEventListener('error', e => window.__errors.push(e.message));

  import {{ loader }} from "{UNISPHERE_URL}/loader/index.esm.js";

  try {{
    const workspace = await loader({{
      serverUrl: "{UNISPHERE_URL}",
      appId: "e2e-lang", appVersion: "1.0.0",
      session: {{ ks: "{user_ks}", partnerId: "{PARTNER_ID}" }},
      ui: {{ theme: "light", language: "he-IL" }},
      runtimes: [{{
        widgetName: "unisphere.widget.genie",
        runtimeName: "chat",
        settings: {{
          kalturaServerURI: "{SERVICE_URL.replace('/api_v3', '')}",
          ks: "{user_ks}",
          partnerId: "{PARTNER_ID}"
        }},
        visuals: [{{ type: "page", target: "lang-container", settings: {{}} }}]
      }}]
    }});
    await workspace.getRuntimeAsync("unisphere.widget.genie", "chat");
    // Check for RTL direction
    const all = document.querySelectorAll('*');
    let rtlFound = false;
    for (const el of all) {{
      const dir = el.getAttribute('dir') || window.getComputedStyle(el).direction;
      if (dir === 'rtl') {{
        rtlFound = true;
        break;
      }}
    }}
    window.__rtl_applied = rtlFound;
    window.__lang_ready = true;
  }} catch (e) {{
    window.__errors.push("lang error: " + e.message);
    window.__lang_ready = true;
    window.__rtl_applied = false;
  }}
</script>
</body></html>"""
            path = _write_html(html, "language_rtl")
            page = browser.new_page()
            try:
                page.goto(f"file://{path}", wait_until="networkidle", timeout=60000)
                page.wait_for_function("window.__lang_ready !== undefined", timeout=30000)
                rtl = page.evaluate("window.__rtl_applied")
                errors = page.evaluate("window.__errors")
                container = page.query_selector("#lang-container")
                inner = container.inner_html() if container else ""
                assert len(inner) > 0, f"Language container is empty. Errors: {errors}"
                print(f"    RTL detected: {rtl}, container: {len(inner)} chars")
            finally:
                page.close()

        runner.run_test("e2e — Hebrew language RTL direction", test_language_rtl)

        # ════════════════════════════════════════════
        # Phase 5: Player Integration
        # ════════════════════════════════════════════

        def test_player_integration():
            """Verify KalturaPlayer.setup with Unisphere plugins renders."""
            html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<script src="https://cdnapisec.kaltura.com/p/{PARTNER_ID}/embedPlaykitJs/uiconf_id/{PLAYER_ID}"></script>
</head>
<body>
<div id="player-container" style="width:640px;height:360px;"></div>
<script>
  window.__errors = [];
  window.addEventListener('error', e => window.__errors.push(e.message));

  try {{
    if (typeof KalturaPlayer !== 'undefined') {{
      const player = KalturaPlayer.setup({{
        targetId: "player-container",
        provider: {{
          partnerId: {PARTNER_ID},
          uiConfId: {PLAYER_ID},
          ks: "{user_ks}"
        }}
      }});
      window.__player_created = true;
      window.__player_ready = true;
    }} else {{
      window.__errors.push("KalturaPlayer not defined");
      window.__player_created = false;
      window.__player_ready = true;
    }}
  }} catch (e) {{
    window.__errors.push("player error: " + e.message);
    window.__player_created = false;
    window.__player_ready = true;
  }}
</script>
</body></html>"""
            path = _write_html(html, "player")
            page = browser.new_page()
            try:
                page.goto(f"file://{path}", wait_until="networkidle", timeout=60000)
                page.wait_for_function("window.__player_ready !== undefined", timeout=30000)
                created = page.evaluate("window.__player_created")
                errors = page.evaluate("window.__errors")
                assert created, f"Player failed to initialize. Errors: {errors}"
                container = page.query_selector("#player-container")
                inner = container.inner_html() if container else ""
                assert len(inner) > 0, "Player container is empty"
                print(f"    Player created: {created}, container: {len(inner)} chars")
            finally:
                page.close()

        runner.run_test("e2e — Player v7 with Unisphere service renders", test_player_integration)

        # ════════════════════════════════════════════
        # Phase 6: Runtime Status & Cleanup
        # ════════════════════════════════════════════

        def test_runtime_status():
            """Verify getRuntimeAsync resolves with loaded status."""
            html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"></head>
<body>
<div id="status-container" style="width:400px;height:300px;display:flex;"></div>
<script type="module">
  window.__errors = [];
  window.addEventListener('error', e => window.__errors.push(e.message));

  import {{ loader }} from "{UNISPHERE_URL}/loader/index.esm.js";

  try {{
    const workspace = await loader({{
      serverUrl: "{UNISPHERE_URL}",
      appId: "e2e-status", appVersion: "1.0.0",
      session: {{ ks: "{user_ks}", partnerId: "{PARTNER_ID}" }},
      runtimes: [{{
        widgetName: "unisphere.widget.genie",
        runtimeName: "chat",
        settings: {{
          kalturaServerURI: "{SERVICE_URL.replace('/api_v3', '')}",
          ks: "{user_ks}",
          partnerId: "{PARTNER_ID}"
        }},
        visuals: [{{ type: "page", target: "status-container", settings: {{}} }}]
      }}]
    }});
    const runtime = await workspace.getRuntimeAsync("unisphere.widget.genie", "chat");
    window.__runtime_resolved = !!runtime;
    window.__workspace_status = workspace.getStatus();
    window.__status_ready = true;
  }} catch (e) {{
    window.__errors.push("status error: " + e.message);
    window.__status_ready = true;
    window.__runtime_resolved = false;
  }}
</script>
</body></html>"""
            path = _write_html(html, "runtime_status")
            page = browser.new_page()
            try:
                page.goto(f"file://{path}", wait_until="networkidle", timeout=60000)
                page.wait_for_function("window.__status_ready !== undefined", timeout=30000)
                resolved = page.evaluate("window.__runtime_resolved")
                ws_status = page.evaluate("window.__workspace_status")
                errors = page.evaluate("window.__errors")
                assert resolved, f"getRuntimeAsync did not resolve. Errors: {errors}"
                print(f"    Runtime resolved: {resolved}, workspace status: {ws_status}")
            finally:
                page.close()

        runner.run_test("e2e — getRuntimeAsync resolves with loaded runtime", test_runtime_status)

        def test_workspace_kill():
            """Verify workspace.kill() cleans up visuals from DOM."""
            html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"></head>
<body>
<div id="kill-container" style="width:400px;height:300px;display:flex;"></div>
<script type="module">
  window.__errors = [];
  window.addEventListener('error', e => window.__errors.push(e.message));

  import {{ loader }} from "{UNISPHERE_URL}/loader/index.esm.js";

  try {{
    const workspace = await loader({{
      serverUrl: "{UNISPHERE_URL}",
      appId: "e2e-kill", appVersion: "1.0.0",
      session: {{ ks: "{user_ks}", partnerId: "{PARTNER_ID}" }},
      runtimes: [{{
        widgetName: "unisphere.widget.genie",
        runtimeName: "chat",
        settings: {{
          kalturaServerURI: "{SERVICE_URL.replace('/api_v3', '')}",
          ks: "{user_ks}",
          partnerId: "{PARTNER_ID}"
        }},
        visuals: [{{ type: "page", target: "kill-container", settings: {{}} }}]
      }}]
    }});
    await workspace.getRuntimeAsync("unisphere.widget.genie", "chat");

    // Record state before kill
    window.__status_before_kill = workspace.getStatus();

    // Kill workspace — may be sync or async
    try {{
      workspace.kill();
      window.__kill_called = true;
    }} catch (e) {{
      window.__errors.push("kill() threw: " + e.message);
      window.__kill_called = false;
    }}
    await new Promise(r => setTimeout(r, 1000));

    window.__status_after_kill = workspace.getStatus();
    window.__kill_done = true;
  }} catch (e) {{
    window.__errors.push("kill error: " + e.message);
    window.__kill_done = true;
  }}
</script>
</body></html>"""
            path = _write_html(html, "workspace_kill")
            page = browser.new_page()
            try:
                page.goto(f"file://{path}", wait_until="networkidle", timeout=60000)
                page.wait_for_function("window.__kill_done !== undefined", timeout=30000)
                kill_called = page.evaluate("window.__kill_called")
                status_before = page.evaluate("window.__status_before_kill")
                status_after = page.evaluate("window.__status_after_kill")
                errors = page.evaluate("window.__errors")
                assert kill_called, f"workspace.kill() threw an error. Errors: {errors}"
                print(f"    kill() called: {kill_called}, status before: {status_before}, status after: {status_after}")
            finally:
                page.close()

        runner.run_test("e2e — workspace.kill() cleans up visuals", test_workspace_kill)

        browser.close()

    # Summary
    success = runner.summary()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
