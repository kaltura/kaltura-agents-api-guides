#!/usr/bin/env python3
"""
End-to-end validation of KALTURA_EXPERIENCE_COMPONENTS_API.md against the live API.

Tests the server-side API patterns documented in the guide:
- Genie Widget KS generation (section 7.3) with documented privileges
- Genie-specific KS privileges: genieid, geniecategoryid, genieancestorid
- Verifying generated KS tokens authenticate with the Genie API
"""

import sys
import os
import uuid
import json
import requests

sys.path.insert(0, os.path.dirname(__file__))
from test_helpers import (
    kaltura_post, TestRunner, PARTNER_ID, KS, SERVICE_URL, GENIE_BASE_URL,
)

ADMIN_SECRET = os.environ.get("KALTURA_ADMIN_SECRET", "")
GENIE_QUERY = "What is Kaltura?"

state = {}


def _generate_user_ks(privileges=""):
    """Generate a USER KS (type=0) with given privileges via session.start."""
    params = {
        "secret": ADMIN_SECRET,
        "partnerId": PARTNER_ID,
        "type": 0,
        "userId": "genie_widget_test",
        "expiry": 3600,
    }
    if privileges:
        params["privileges"] = privileges
    resp = requests.post(
        f"{SERVICE_URL}/service/session/action/start",
        data={"format": 1, **params},
        timeout=30,
    )
    resp.raise_for_status()
    ks = resp.json()
    if isinstance(ks, dict) and ks.get("objectType") == "KalturaAPIException":
        raise Exception(f"session.start error: {ks.get('message')} (code: {ks.get('code')})")
    assert isinstance(ks, str) and len(ks) > 20, f"Expected KS string, got: {ks}"
    return ks


def _genie_search_with_ks(ks_token):
    """Call Genie /mcp/search with a specific KS token. Returns (http_status, parsed_json)."""
    resp = requests.post(
        f"{GENIE_BASE_URL}/mcp/search",
        headers={
            "Authorization": f"KS {ks_token}",
            "Content-Type": "application/json",
        },
        json={"query": GENIE_QUERY, "include_sources": False},
        timeout=30,
    )
    return resp.status_code, resp.json()


def main():
    runner = TestRunner("Experience Components — E2E Validation")

    # ════════════════════════════════════════════
    # Phase 1: Genie Widget KS Generation (section 7.3)
    # ════════════════════════════════════════════

    def test_genie_ks_generation():
        """Generate a USER KS with the documented Genie Widget privileges."""
        if not ADMIN_SECRET:
            print("    SKIP: KALTURA_ADMIN_SECRET not set in .env")
            return
        session_id = str(uuid.uuid4())
        privileges = (
            f"setrole:PLAYBACK_BASE_ROLE,sview:*,"
            f"appid:test-app-localhost,sessionid:{session_id}"
        )
        ks = _generate_user_ks(privileges)
        state["genie_ks"] = ks
        print(f"    Generated USER KS with Genie Widget privileges")
        print(f"    KS length: {len(ks)} chars, sessionid: {session_id}")

    runner.run_test("session.start — Genie Widget KS (setrole:PLAYBACK_BASE_ROLE,sview:*)",
                     test_genie_ks_generation)

    def test_genie_ks_authenticates():
        """Verify the generated Genie KS authenticates with the Genie API."""
        ks = state.get("genie_ks")
        if not ks:
            print("    SKIP: No Genie KS generated (ADMIN_SECRET not set)")
            return
        status_code, result = _genie_search_with_ks(ks)
        assert status_code == 200, f"Genie returned HTTP {status_code}: {result}"
        assert result.get("status") == "success", f"Genie search failed: {result}"
        data = result["data"]
        assert "text" in data, f"Expected text in response. Keys: {list(data.keys())}"
        print(f"    Genie API authenticated with widget KS (HTTP {status_code})")
        print(f"    Response: {len(data['text'])} chars")

    runner.run_test("Genie /mcp/search — authenticates with widget KS",
                     test_genie_ks_authenticates)

    # ════════════════════════════════════════════
    # Phase 2: Genie-Specific KS Privileges
    # ════════════════════════════════════════════

    def test_genieid_privilege():
        """Generate a KS with genieid:default privilege and verify it works."""
        if not ADMIN_SECRET:
            print("    SKIP: KALTURA_ADMIN_SECRET not set in .env")
            return
        privileges = "setrole:PLAYBACK_BASE_ROLE,sview:*,genieid:default"
        ks = _generate_user_ks(privileges)
        status_code, result = _genie_search_with_ks(ks)
        assert status_code == 200, f"genieid:default HTTP {status_code}: {result}"
        assert result.get("status") == "success", f"genieid:default failed: {result}"
        data = result["data"]
        assert "text" in data, f"Expected text in response. Keys: {list(data.keys())}"
        print(f"    genieid:default — authenticated, {len(data['text'])} chars")

    runner.run_test("Genie /mcp/search — genieid:default privilege",
                     test_genieid_privilege)

    def test_geniecategoryid_privilege():
        """Generate a KS with geniecategoryid privilege — verifies the privilege is accepted."""
        if not ADMIN_SECRET:
            print("    SKIP: KALTURA_ADMIN_SECRET not set in .env")
            return
        # Use category ID 0 — Genie accepts the privilege even if no content
        # matches that category. A "no results" response (status=error with
        # informational message) is expected and valid — the key assertion is
        # that Genie does NOT return 401/403 (authentication rejection).
        privileges = "setrole:PLAYBACK_BASE_ROLE,sview:*,geniecategoryid:0"
        ks = _generate_user_ks(privileges)
        status_code, result = _genie_search_with_ks(ks)
        assert status_code == 200, (
            f"geniecategoryid rejected with HTTP {status_code}: {result}"
        )
        # status can be "success" (matching content found) or "error" (no results)
        # Both prove the privilege was accepted — no auth failure
        print(f"    geniecategoryid:0 — HTTP {status_code}, status={result.get('status')}")

    runner.run_test("Genie /mcp/search — geniecategoryid privilege accepted",
                     test_geniecategoryid_privilege)

    def test_genieancestorid_privilege():
        """Generate a KS with genieancestorid privilege — verifies the privilege is accepted."""
        if not ADMIN_SECRET:
            print("    SKIP: KALTURA_ADMIN_SECRET not set in .env")
            return
        privileges = "setrole:PLAYBACK_BASE_ROLE,sview:*,genieancestorid:0"
        ks = _generate_user_ks(privileges)
        status_code, result = _genie_search_with_ks(ks)
        assert status_code == 200, (
            f"genieancestorid rejected with HTTP {status_code}: {result}"
        )
        print(f"    genieancestorid:0 — HTTP {status_code}, status={result.get('status')}")

    runner.run_test("Genie /mcp/search — genieancestorid privilege accepted",
                     test_genieancestorid_privilege)

    # ════════════════════════════════════════════
    # Phase 3: Entitlement Privileges (section 7.3)
    # ════════════════════════════════════════════

    def test_entitlement_privilege():
        """Generate a KS with enableentitlement and verify Genie accepts it."""
        if not ADMIN_SECRET:
            print("    SKIP: KALTURA_ADMIN_SECRET not set in .env")
            return
        # enableentitlement without privacycontext — Genie should still accept
        privileges = "setrole:PLAYBACK_BASE_ROLE,sview:*,enableentitlement"
        ks = _generate_user_ks(privileges)
        status_code, result = _genie_search_with_ks(ks)
        assert status_code == 200, (
            f"enableentitlement rejected with HTTP {status_code}: {result}"
        )
        print(f"    enableentitlement — HTTP {status_code}, status={result.get('status')}")

    runner.run_test("Genie /mcp/search — enableentitlement privilege accepted",
                     test_entitlement_privilege)

    # ════════════════════════════════════════════
    # Phase 4: Express Recorder KS Privilege (section 3)
    # ════════════════════════════════════════════

    def test_express_recorder_ks_privilege():
        """Generate a KS with editadmintags:* (Express Recorder requirement)."""
        if not ADMIN_SECRET:
            print("    SKIP: KALTURA_ADMIN_SECRET not set in .env")
            return
        privileges = "editadmintags:*"
        ks = _generate_user_ks(privileges)
        # Verify the KS is valid by listing entries (read-only, always accessible)
        result = kaltura_post("baseEntry", "list", {
            "ks": ks,
            "pager[pageSize]": 1,
        })
        assert "totalCount" in result, f"KS validation failed: {result}"
        print(f"    editadmintags:* KS generated and validated")
        print(f"    baseEntry.list returned totalCount={result.get('totalCount')}")

    runner.run_test("session.start — Express Recorder KS (editadmintags:*)",
                     test_express_recorder_ks_privilege)

    # ════════════════════════════════════════════
    # Cleanup & Summary
    # ════════════════════════════════════════════

    runner.cleanup()
    success = runner.summary()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    print(f"\n{'='*60}")
    print("  EXPERIENCE COMPONENTS — End-to-End Validation")
    print(f"{'='*60}\n")
    main()
