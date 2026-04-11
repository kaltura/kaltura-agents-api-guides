"""
Shared helpers for Kaltura API guide validation tests.

Configuration is loaded from environment variables or a .env file
in this directory. See .env.example for required variables.
"""

import os
import sys
import requests
import time

# Load .env file if python-dotenv is available, otherwise fall back to manual parsing
_env_path = os.path.join(os.path.dirname(__file__), ".env")

try:
    from dotenv import load_dotenv
    load_dotenv(_env_path, override=True)
except ImportError:
    # Minimal .env loader — no dependency needed
    # Force-set values so the test .env takes priority over system env vars
    if os.path.exists(_env_path):
        with open(_env_path) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                key, _, value = line.partition("=")
                if key and value:
                    os.environ[key.strip()] = value.strip()


def _require_env(name):
    val = os.environ.get(name)
    if not val:
        print(f"ERROR: {name} is not set. Copy .env.example to .env and fill in your values.")
        sys.exit(1)
    return val


# === Configuration (from environment) ===
PARTNER_ID = _require_env("KALTURA_PARTNER_ID")
KS = _require_env("KALTURA_KS")
SERVICE_URL = os.environ.get("KALTURA_SERVICE_URL", "https://www.kaltura.com/api_v3")
AGENTS_MANAGER_URL = os.environ.get("KALTURA_AGENTS_MANAGER_URL", "https://agents-manager.nvp1.ovp.kaltura.com")
GENIE_BASE_URL = os.environ.get("KALTURA_GENIE_URL", "https://genie.nvp1.ovp.kaltura.com")
APP_REGISTRY_URL = os.environ.get("KALTURA_APP_REGISTRY_URL", "https://app-registry.nvp1.ovp.kaltura.com/api/v1")
USER_PROFILE_URL = os.environ.get("KALTURA_USER_PROFILE_URL", "https://user.nvp1.ovp.kaltura.com/api/v1")
MESSAGING_URL = os.environ.get("KALTURA_MESSAGING_URL", "https://messaging.nvp1.ovp.kaltura.com/api/v1")
AUTH_BROKER_URL = os.environ.get("KALTURA_AUTH_BROKER_URL", "https://auth.nvp1.ovp.kaltura.com/api/v1")
REPORTS_URL = os.environ.get("KALTURA_REPORTS_URL", "https://reports.nvp1.ovp.kaltura.com")
SCM_URL = os.environ.get("KALTURA_SCM_URL", "https://scm.nvp1.ovp.kaltura.com/api/v1")


def kaltura_post(service, action, params=None):
    """POST to Kaltura API v3 with form-encoded params. Returns parsed JSON."""
    data = {"ks": KS, "format": 1}
    if params:
        data.update(params)
    resp = requests.post(
        f"{SERVICE_URL}/service/{service}/action/{action}",
        data=data,
        timeout=30,
    )
    resp.raise_for_status()
    result = resp.json()
    if isinstance(result, dict) and result.get("objectType") == "KalturaAPIException":
        raise Exception(f"Kaltura API error: {result.get('message')} (code: {result.get('code')})")
    return result


def bearer_post(base_url, path, json_body=None, timeout=30):
    """POST to a Kaltura JSON API with Bearer KS auth. Returns parsed JSON."""
    headers = {
        "Authorization": f"Bearer {KS}",
        "Content-Type": "application/json",
    }
    resp = requests.post(
        f"{base_url}{path}",
        headers=headers,
        json=json_body or {},
        timeout=timeout,
    )
    resp.raise_for_status()
    if not resp.content:
        return {}
    result = resp.json()
    if isinstance(result, dict) and result.get("objectType") == "KalturaAPIException":
        raise Exception(f"API error: {result.get('message')} (code: {result.get('code')})")
    return result


def app_registry_post(action, json_body=None):
    """POST to App Registry API. Returns parsed JSON."""
    return bearer_post(APP_REGISTRY_URL, f"/app-registry/{action}", json_body)


def user_profile_post(path, json_body=None, timeout=30):
    """POST to User Profile API. Returns parsed JSON."""
    return bearer_post(USER_PROFILE_URL, path, json_body, timeout=timeout)


def messaging_post(service, action, json_body=None):
    """POST to Messaging API. Returns parsed JSON."""
    return bearer_post(MESSAGING_URL, f"/{service}/{action}", json_body)


def auth_broker_post(service, action, json_body=None, timeout=30):
    """POST to Auth Broker API with KS auth header. Returns parsed JSON."""
    headers = {
        "Authorization": f"KS {KS}",
        "Content-Type": "application/json",
    }
    resp = requests.post(
        f"{AUTH_BROKER_URL}/{service}/{action}",
        headers=headers,
        json=json_body or {},
        timeout=timeout,
    )
    if not resp.ok:
        try:
            err = resp.json()
            msg = err.get("message", resp.text)
            code = err.get("code", resp.status_code)
            raise Exception(f"Auth Broker error: {msg} (code: {code})")
        except (ValueError, KeyError):
            resp.raise_for_status()
    if not resp.content:
        return {}
    result = resp.json()
    if isinstance(result, dict) and result.get("objectType") == "KalturaAPIException":
        raise Exception(f"Auth Broker error: {result.get('message')} (code: {result.get('code')})")
    return result


def auth_broker_get(path, timeout=30):
    """GET from Auth Broker API with KS auth header. Returns raw response text."""
    headers = {"Authorization": f"KS {KS}"}
    resp = requests.get(
        f"{AUTH_BROKER_URL}{path}",
        headers=headers,
        timeout=timeout,
    )
    resp.raise_for_status()
    return resp.text


def reports_post(path, json_body=None, timeout=30):
    """POST to Reports Microservice with Bearer KS auth. Returns parsed JSON."""
    return bearer_post(REPORTS_URL, path, json_body, timeout=timeout)


def scm_post(controller, action, json_body=None, timeout=30):
    """POST to Game Services (SCM) API. Returns parsed JSON."""
    return bearer_post(SCM_URL, f"/{controller}/{action}", json_body, timeout=timeout)


def agents_post(path, json_body=None):
    """POST to Agents Manager API with JSON body. Returns parsed JSON."""
    headers = {
        "Authorization": f"Bearer {KS}",
        "Content-Type": "application/json",
    }
    resp = requests.post(
        f"{AGENTS_MANAGER_URL}{path}",
        headers=headers,
        json=json_body or {},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def genie_post(path, json_body=None, headers_override=None, stream=False, timeout=30):
    """POST to Genie API with KS auth. Returns parsed JSON or raw response."""
    headers = {
        "Authorization": f"KS {KS}",
        "Content-Type": "application/json",
    }
    if headers_override:
        headers.update(headers_override)
    resp = requests.post(
        f"{GENIE_BASE_URL}{path}",
        headers=headers,
        json=json_body or {},
        stream=stream,
        timeout=timeout,
    )
    resp.raise_for_status()
    if stream:
        return resp
    return resp.json()


def create_test_entry():
    """Create a minimal test media entry. Returns entryId."""
    ts = int(time.time())
    result = kaltura_post("media", "add", {
        "entry[objectType]": "KalturaMediaEntry",
        "entry[mediaType]": 1,
        "entry[name]": f"API_DOC_VALIDATION_TEST_{ts}",
        "entry[description]": "Temporary entry for API doc validation. Safe to delete.",
    })
    return result["id"]


def delete_test_entry(entry_id):
    """Delete a media entry by ID."""
    try:
        kaltura_post("media", "delete", {"entryId": entry_id})
    except Exception as e:
        print(f"  [WARN] Failed to delete entry {entry_id}: {e}")


class TestRunner:
    """Collects test results and tracks resources for cleanup."""

    def __init__(self, name):
        self.name = name
        self.results = []
        self._cleanup_actions = []

    def register_cleanup(self, label, fn):
        self._cleanup_actions.append((label, fn))

    def run_test(self, test_name, fn):
        try:
            fn()
            self.results.append((test_name, True, ""))
            print(f"  PASS  {test_name}")
        except Exception as e:
            self.results.append((test_name, False, str(e)))
            print(f"  FAIL  {test_name}: {e}")

    def cleanup(self):
        print(f"\n--- Cleanup ({self.name}) ---")
        for label, fn in reversed(self._cleanup_actions):
            try:
                fn()
                print(f"  Cleaned up: {label}")
            except Exception as e:
                print(f"  [WARN] Cleanup failed for {label}: {e}")

    def summary(self):
        total = len(self.results)
        passed = sum(1 for _, ok, _ in self.results if ok)
        failed = total - passed
        print(f"\n{'='*60}")
        print(f"  {self.name}: {passed}/{total} passed, {failed} failed")
        if failed:
            print(f"\n  Failed tests:")
            for name, ok, detail in self.results:
                if not ok:
                    print(f"    - {name}: {detail}")
        print(f"{'='*60}")
        return failed == 0
