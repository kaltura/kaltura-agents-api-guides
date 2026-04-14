#!/usr/bin/env python3
"""End-to-end validation of the Content Lab Widget API.
Covers: CDN accessibility, manifest presence, bundle loading, browser embedding,
application and ai-consent runtimes, consent API, entry eligibility."""

import sys
import os
import json
import time
import tempfile
import requests

sys.path.insert(0, os.path.dirname(__file__))
from test_helpers import kaltura_post, TestRunner, PARTNER_ID, KS, SERVICE_URL

BASE_URL = "https://unisphere.nvp1.ovp.kaltura.com/v1"
WIDGET_NAME = "unisphere.widget.content-lab"

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
    runner = TestRunner("Content Lab Widget — E2E Validation")

    # ════════════════════════════════════════════
    # Phase 1: CDN & Manifest
    # ════════════════════════════════════════════

    def test_manifest():
        """Verify Content Lab widget is in the runtime.json manifest."""
        resp = requests.get(f"{BASE_URL}/runtime.json", timeout=30)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        data = resp.json()
        widgets = data.get("versions", {}).get("widgets", {})
        assert WIDGET_NAME in widgets, f"Expected '{WIDGET_NAME}' in manifest"
        cl = widgets[WIDGET_NAME]
        runtimes = cl.get("runtimes", {})
        assert "application" in runtimes, f"Expected 'application' runtime"
        assert "ai-consent" in runtimes, f"Expected 'ai-consent' runtime"
        state["app_version"] = runtimes["application"]["version"]
        state["consent_version"] = runtimes["ai-consent"]["version"]
        print(f"    application: v{state['app_version']}")
        print(f"    ai-consent: v{state['consent_version']}")

    runner.run_test("manifest — Content Lab with application + ai-consent runtimes", test_manifest)

    def test_app_bundle():
        """Verify the application bundle is accessible on CDN."""
        version = state.get("app_version")
        url = f"{BASE_URL}/static/modules/content-lab/v{version}/runtime/application/index.esm.js"
        resp = requests.head(url, timeout=30)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        print(f"    application bundle: {resp.status_code}")

    runner.run_test("bundle — application runtime accessible on CDN", test_app_bundle)

    def test_consent_bundle():
        """Verify the ai-consent bundle is accessible on CDN."""
        version = state.get("consent_version")
        url = f"{BASE_URL}/static/modules/content-lab/v{version}/runtime/ai-consent/index.esm.js"
        resp = requests.head(url, timeout=30)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        print(f"    ai-consent bundle: {resp.status_code}")

    runner.run_test("bundle — ai-consent runtime accessible on CDN", test_consent_bundle)

    # ════════════════════════════════════════════
    # Phase 2: Regional Availability
    # ════════════════════════════════════════════

    def test_regional():
        """Verify Content Lab is available in EU and DE regions."""
        for region, label in [("irp2", "EU"), ("frp2", "DE")]:
            url = f"https://unisphere.{region}.ovp.kaltura.com/v1/runtime.json"
            resp = requests.get(url, timeout=30)
            assert resp.status_code == 200, f"Expected 200 for {label}"
            data = resp.json()
            widgets = data.get("versions", {}).get("widgets", {})
            assert WIDGET_NAME in widgets, f"Expected '{WIDGET_NAME}' in {label} manifest"
            version = widgets[WIDGET_NAME]["runtimes"]["application"]["version"]
            print(f"    {label} ({region}): v{version}")

    runner.run_test("regional — Content Lab in EU and DE manifests", test_regional)

    # ════════════════════════════════════════════
    # Phase 3: Consent API
    # ════════════════════════════════════════════

    def test_consent_api():
        """Verify the consent API endpoint is accessible."""
        resp = requests.post(
            "https://consent.nvp1.ovp.kaltura.com/api/v1/consent/get-status",
            headers={
                "Authorization": f"Bearer {KS}",
                "Content-Type": "application/json",
            },
            json={"approved_entity": "AI"},
            timeout=30,
        )
        # Accept 200 (success) or 4xx (permission/config issue)
        assert resp.status_code < 500, f"Expected non-5xx, got {resp.status_code}"
        print(f"    Consent API: {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            status = data.get("approval_status", data.get("status", "unknown"))
            print(f"    AI consent status: {status}")

    runner.run_test("consent — AI consent API accessible", test_consent_api)

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

        def test_app_runtime_loads():
            """Verify the application runtime loads in the browser."""
            html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>CL App Test</title></head>
<body>
<div id="cl-app" style="width:100%;height:100vh;"></div>
<script type="module">
  import {{ loader }} from "{BASE_URL}/loader/index.esm.js";
  try {{
    const ws = await loader({{
      serverUrl: "{BASE_URL}",
      appId: "cl-test", appVersion: "1.0.0",
      session: {{ ks: "{browser_ks}", partnerId: {PARTNER_ID} }},
      runtimes: [{{
        widgetName: "{WIDGET_NAME}",
        runtimeName: "application",
        settings: {{
          _schemaVersion: "1",
          ks: "{browser_ks}",
          pid: "{PARTNER_ID}",
          uiconfId: "{os.environ.get('KALTURA_PLAYER_ID', '56732362')}",
          kalturaServerURI: "https://www.kaltura.com",
          analyticsServerURI: "analytics.kaltura.com",
          hostAppName: 1,
          hostedInKalturaProduct: false
        }},
        visuals: [{{ type: "drawer", target: "cl-app", settings: {{}} }}]
      }}]
    }});
    const rt = await ws.getRuntimeAsync("{WIDGET_NAME}", "application");
    window.__cl_done = true;
    window.__cl_result = rt !== null ? "OK" : "NULL";
    window.__cl_hasOpen = typeof rt.openApplication === "function";
  }} catch(e) {{
    window.__cl_done = true;
    window.__cl_result = "ERR:" + e.message;
  }}
</script></body></html>"""
            path = _write_html("cl_app_test.html", html)
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                page.goto(f"file://{path}", wait_until="networkidle", timeout=30000)
                page.wait_for_function("window.__cl_done !== undefined", timeout=30000)
                result = page.evaluate("window.__cl_result")
                has_open = page.evaluate("window.__cl_hasOpen")
                browser.close()
            assert result == "OK", f"Expected OK, got {result}"
            assert has_open is True, f"Expected openApplication method, got {has_open}"
            print(f"    Application runtime: loaded, openApplication={has_open}")

        runner.run_test("browser — application runtime loads with openApplication API", test_app_runtime_loads)

        def test_isEntryRelevant():
            """Verify isEntryRelevant method exists and returns eligibility result."""
            html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>CL Entry Relevant</title></head>
<body>
<div id="cl-relevant" style="width:100%;height:100vh;"></div>
<script type="module">
  import {{ loader }} from "{BASE_URL}/loader/index.esm.js";
  try {{
    const ws = await loader({{
      serverUrl: "{BASE_URL}",
      appId: "cl-relevant-test", appVersion: "1.0.0",
      session: {{ ks: "{browser_ks}", partnerId: {PARTNER_ID} }},
      runtimes: [{{
        widgetName: "{WIDGET_NAME}",
        runtimeName: "application",
        settings: {{
          _schemaVersion: "1",
          ks: "{browser_ks}",
          pid: "{PARTNER_ID}",
          uiconfId: "{os.environ.get('KALTURA_PLAYER_ID', '56732362')}",
          kalturaServerURI: "https://www.kaltura.com",
          analyticsServerURI: "analytics.kaltura.com",
          hostAppName: 1,
          hostedInKalturaProduct: false
        }},
        visuals: [{{ type: "drawer", target: "cl-relevant", settings: {{}} }}]
      }}]
    }});
    const rt = await ws.getRuntimeAsync("{WIDGET_NAME}", "application");
    window.__rel_hasMethod = typeof rt.isEntryRelevant === "function";
    // Call with a non-existent entry ID to verify the method executes
    try {{
      const result = await rt.isEntryRelevant("0_nonexistent");
      window.__rel_result = JSON.stringify({{
        canUse: result.canUse,
        reason: result.rejectionReason || "none"
      }});
    }} catch(e) {{
      // Method exists but call may fail — that's OK for validation
      window.__rel_result = "CALL_ERR:" + e.message;
    }}
    window.__rel_done = true;
  }} catch(e) {{
    window.__rel_done = true;
    window.__rel_result = "ERR:" + e.message;
  }}
</script></body></html>"""
            path = _write_html("cl_relevant_test.html", html)
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                page.goto(f"file://{path}", wait_until="networkidle",
                          timeout=30000)
                page.wait_for_function(
                    "window.__rel_done !== undefined", timeout=30000)
                has_method = page.evaluate("window.__rel_hasMethod")
                result = page.evaluate("window.__rel_result")
                browser.close()
            assert has_method is True, \
                f"Expected isEntryRelevant method, got {has_method}"
            print(f"    isEntryRelevant: method={has_method}, "
                  f"result={result}")

        runner.run_test("browser — isEntryRelevant method available on "
                        "application runtime", test_isEntryRelevant)

        def test_consent_runtime_loads():
            """Verify the ai-consent runtime loads in the browser."""
            html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>CL Consent Test</title></head>
<body>
<script type="module">
  import {{ loader }} from "{BASE_URL}/loader/index.esm.js";
  try {{
    const ws = await loader({{
      serverUrl: "{BASE_URL}",
      appId: "cl-consent-test", appVersion: "1.0.0",
      session: {{ ks: "{browser_ks}", partnerId: {PARTNER_ID} }},
      runtimes: [{{
        widgetName: "{WIDGET_NAME}",
        runtimeName: "ai-consent",
        settings: {{
          _schemaVersion: "1",
          ks: "{browser_ks}",
          pid: "{PARTNER_ID}",
          hostApp: "cl-test",
          canSetConsent: true,
          kaltura: {{
            analyticsServerURI: "analytics.kaltura.com",
            hostAppName: 1,
            hostAppVersion: "1.0.0"
          }}
        }},
        visuals: [{{ type: "banner", target: {{ target: "body" }}, settings: {{}} }}]
      }}]
    }});
    const rt = await ws.getRuntimeAsync("{WIDGET_NAME}", "ai-consent");
    window.__consent_done = true;
    window.__consent_result = rt !== null ? "OK" : "NULL";
    window.__consent_has_show = rt !== null && typeof rt.showAnnouncement === "function";
  }} catch(e) {{
    window.__consent_done = true;
    window.__consent_result = "ERR:" + e.message;
  }}
</script></body></html>"""
            path = _write_html("cl_consent_test.html", html)
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                page.goto(f"file://{path}", wait_until="networkidle", timeout=30000)
                page.wait_for_function("window.__consent_done !== undefined", timeout=30000)
                result = page.evaluate("window.__consent_result")
                has_show = page.evaluate("window.__consent_has_show")
                browser.close()
            assert result == "OK", f"Expected OK, got {result}"
            assert has_show is True, f"Expected showAnnouncement method"
            print(f"    AI consent runtime: loaded, showAnnouncement={has_show}")

        runner.run_test("browser — ai-consent runtime loads with showAnnouncement API", test_consent_runtime_loads)

        def test_dual_runtime_workspace():
            """Verify both runtimes load in a single workspace."""
            html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>CL Dual Test</title></head>
<body>
<div id="cl-dual" style="width:100%;height:100vh;"></div>
<script type="module">
  import {{ loader }} from "{BASE_URL}/loader/index.esm.js";
  try {{
    const ws = await loader({{
      serverUrl: "{BASE_URL}",
      appId: "cl-dual-test", appVersion: "1.0.0",
      session: {{ ks: "{browser_ks}", partnerId: {PARTNER_ID} }},
      runtimes: [
        {{
          widgetName: "{WIDGET_NAME}",
          runtimeName: "application",
          settings: {{
            _schemaVersion: "1",
            ks: "{browser_ks}",
            pid: "{PARTNER_ID}",
            uiconfId: "{os.environ.get('KALTURA_PLAYER_ID', '56732362')}",
            kalturaServerURI: "https://www.kaltura.com",
            analyticsServerURI: "analytics.kaltura.com",
            hostAppName: 1,
            hostedInKalturaProduct: false
          }},
          visuals: [{{ type: "drawer", target: "cl-dual", settings: {{}} }}]
        }},
        {{
          widgetName: "{WIDGET_NAME}",
          runtimeName: "ai-consent",
          settings: {{
            _schemaVersion: "1",
            ks: "{browser_ks}",
            pid: "{PARTNER_ID}",
            hostApp: "cl-test",
            canSetConsent: true,
            kaltura: {{
              analyticsServerURI: "analytics.kaltura.com",
              hostAppName: 1,
              hostAppVersion: "1.0.0"
            }}
          }},
          visuals: [{{ type: "banner", target: {{ target: "body" }}, settings: {{}} }}]
        }}
      ]
    }});
    const app = await ws.getRuntimeAsync("{WIDGET_NAME}", "application");
    const consent = await ws.getRuntimeAsync("{WIDGET_NAME}", "ai-consent");
    window.__dual_done = true;
    window.__dual_app = app !== null;
    window.__dual_consent = consent !== null;
  }} catch(e) {{
    window.__dual_done = true;
    window.__dual_app = "ERR:" + e.message;
  }}
</script></body></html>"""
            path = _write_html("cl_dual_test.html", html)
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                page.goto(f"file://{path}", wait_until="networkidle", timeout=30000)
                page.wait_for_function("window.__dual_done !== undefined", timeout=30000)
                app_ok = page.evaluate("window.__dual_app")
                consent_ok = page.evaluate("window.__dual_consent")
                browser.close()
            assert app_ok is True, f"Expected app=true, got {app_ok}"
            assert consent_ok is True, f"Expected consent=true, got {consent_ok}"
            print(f"    Dual runtime: application={app_ok}, ai-consent={consent_ok}")

        runner.run_test("browser — dual runtime workspace (application + ai-consent)", test_dual_runtime_workspace)

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
