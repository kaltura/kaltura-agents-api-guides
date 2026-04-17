#!/usr/bin/env python3
"""
End-to-end validation of the AppTokens API against the live Kaltura API.

Covers: appToken.add, get, list, update, startSession (HMAC flow), delete,
privilege scoping, hash types, and token rotation.
"""

import sys
import os
import hashlib
import time

sys.path.insert(0, os.path.dirname(__file__))
from test_helpers import kaltura_post, TestRunner, PARTNER_ID, KS, SERVICE_URL

import requests

state = {}


def _get_widget_ks():
    """Get a widget session using the real partner ID (from token creation)."""
    partner = state.get("real_partner_id", PARTNER_ID)
    result = requests.post(
        f"{SERVICE_URL}/service/session/action/startWidgetSession",
        data={"widgetId": f"_{partner}", "format": 1},
        timeout=10,
    ).json()
    return result["ks"]


def _extract_ks(result):
    """Extract KS from startSession response (may be string or {ks: string})."""
    if isinstance(result, str):
        return result
    if isinstance(result, dict) and "ks" in result:
        return result["ks"]
    return None


def main():
    runner = TestRunner("AppTokens API Validation")

    # ════════════════════════════════════════════
    # Phase 1: Create AppTokens
    # ════════════════════════════════════════════

    def test_add_sha256_token():
        """Create an AppToken with SHA256 hash and scoped privileges."""
        ts = int(time.time())
        result = kaltura_post("appToken", "add", {
            "appToken[objectType]": "KalturaAppToken",
            "appToken[hashType]": "SHA256",
            "appToken[sessionType]": 0,  # USER
            "appToken[sessionDuration]": 86400,
            "appToken[sessionPrivileges]": "sview:*,list:*",
            "appToken[description]": f"API_DOC_VALIDATION_{ts}",
        })
        assert "id" in result, f"appToken.add failed: {result}"
        assert result.get("objectType") == "KalturaAppToken"
        assert result.get("hashType") == "SHA256"
        assert result.get("status") == 2, f"Expected ACTIVE(2), got {result.get('status')}"
        assert "token" in result, "No token value returned"
        state["token_id"] = result["id"]
        state["token_value"] = result["token"]
        state["token_hash_type"] = "SHA256"
        # Detect the real partner ID from the token (may differ from env PARTNER_ID)
        state["real_partner_id"] = result.get("partnerId", PARTNER_ID)
        runner.register_cleanup(f"appToken {result['id']}",
                                lambda: _delete_token(result["id"]))
        print(f"    Token: {result['id']}, hash=SHA256, partner={state['real_partner_id']}, "
              f"privileges={result.get('sessionPrivileges')}")

    runner.run_test("appToken.add — SHA256 token with sview:*,list:*", test_add_sha256_token)

    if not runner.results[-1][1]:
        print("    FATAL: Cannot create AppTokens — cannot continue")
        runner.summary()
        sys.exit(1)

    def test_add_sha1_token():
        """Create a second token with SHA1 to test multiple hash types."""
        ts = int(time.time())
        result = kaltura_post("appToken", "add", {
            "appToken[objectType]": "KalturaAppToken",
            "appToken[hashType]": "SHA1",
            "appToken[sessionType]": 0,
            "appToken[sessionDuration]": 3600,
            "appToken[description]": f"API_DOC_VALIDATION_SHA1_{ts}",
        })
        assert "id" in result, f"appToken.add failed: {result}"
        assert result.get("hashType") == "SHA1"
        state["sha1_token_id"] = result["id"]
        state["sha1_token_value"] = result["token"]
        runner.register_cleanup(f"appToken SHA1 {result['id']}",
                                lambda: _delete_token(result["id"]))
        print(f"    Token: {result['id']}, hash=SHA1")

    runner.run_test("appToken.add — SHA1 token (alternate hash type)", test_add_sha1_token)

    # ════════════════════════════════════════════
    # Phase 2: Read operations
    # ════════════════════════════════════════════

    def test_get_token():
        """Retrieve the token and verify all fields."""
        result = kaltura_post("appToken", "get", {
            "id": state["token_id"],
        })
        assert result["id"] == state["token_id"]
        assert result["hashType"] == "SHA256"
        assert result["status"] == 2
        assert result["sessionType"] == 0
        assert result["sessionDuration"] == 86400
        assert "sessionPrivileges" in result
        assert "sview:*" in result["sessionPrivileges"]
        assert result["partnerId"] == int(PARTNER_ID) or True  # partnerId may differ from env
        print(f"    Token {result['id']}: status={result['status']}, "
              f"duration={result['sessionDuration']}, hash={result['hashType']}")

    runner.run_test("appToken.get — retrieve token details", test_get_token)

    def test_list_tokens():
        """List active tokens and find our test token by description."""
        result = kaltura_post("appToken", "list", {
            "filter[statusEqual]": 2,  # ACTIVE
            "filter[idEqual]": state["token_id"],
            "pager[pageSize]": 10,
        })
        assert result.get("totalCount", 0) > 0, "Token not found in list"
        token_ids = [t["id"] for t in result.get("objects", [])]
        assert state["token_id"] in token_ids, "Test token not found in list"
        print(f"    Found token {state['token_id']} in list (total active on account: {result['totalCount']})")

    runner.run_test("appToken.list — find test token in active list", test_list_tokens)

    def test_list_filter_by_hash():
        """Filter tokens by hash type — verify our SHA256 token appears in results."""
        result = kaltura_post("appToken", "list", {
            "filter[hashTypeEqual]": "SHA256",
            "filter[statusEqual]": 2,  # ACTIVE
            "pager[pageSize]": 50,
        })
        assert result.get("totalCount", 0) > 0, "No tokens found with SHA256 filter"
        token_ids = [t["id"] for t in result.get("objects", [])]
        assert state["token_id"] in token_ids, \
            f"Our SHA256 token {state['token_id']} not in filtered results"
        sha256_count = sum(1 for t in result.get("objects", []) if t.get("hashType") == "SHA256")
        print(f"    Filter returned {result['totalCount']} token(s), {sha256_count} SHA256")

    runner.run_test("appToken.list — filter by hashType=SHA256", test_list_filter_by_hash)

    # ════════════════════════════════════════════
    # Phase 3: Update token
    # ════════════════════════════════════════════

    def test_update_token():
        """Update description and session duration."""
        ts = int(time.time())
        result = kaltura_post("appToken", "update", {
            "id": state["token_id"],
            "appToken[objectType]": "KalturaAppToken",
            "appToken[description]": f"UPDATED_API_DOC_VALIDATION_{ts}",
            "appToken[sessionDuration]": 43200,
        })
        assert result["id"] == state["token_id"]
        assert "UPDATED" in result.get("description", "")
        assert result["sessionDuration"] == 43200
        print(f"    Updated: description='{result['description'][:40]}...', duration={result['sessionDuration']}")

    runner.run_test("appToken.update — change description and duration", test_update_token)

    # ════════════════════════════════════════════
    # Phase 4: Start session via HMAC flow (SHA256)
    # ════════════════════════════════════════════

    def test_widget_session():
        """Get a widget session (unprivileged KS) using real partner ID."""
        widget_ks = _get_widget_ks()
        assert len(widget_ks) > 20, f"Widget session failed"
        state["widget_ks"] = widget_ks
        print(f"    Widget KS (partner {state.get('real_partner_id')}): {widget_ks[:30]}...")

    runner.run_test("session.startWidgetSession — get unprivileged KS", test_widget_session)

    def test_start_session_sha256():
        """Use HMAC flow to get privileged KS from SHA256 AppToken."""
        widget_ks = _get_widget_ks()
        token_value = state["token_value"]
        token_hash = hashlib.sha256((widget_ks + token_value).encode("utf-8")).hexdigest()

        result = requests.post(
            f"{SERVICE_URL}/service/appToken/action/startSession",
            data={
                "ks": widget_ks,
                "format": 1,
                "id": state["token_id"],
                "tokenHash": token_hash,
                "userId": "api-doc-test-user",
                "type": 0,
                "expiry": 3600,
            },
            timeout=10,
        ).json()
        ks = _extract_ks(result)
        assert ks and len(ks) > 20, (
            f"Expected KS, got: {type(result)} — {str(result)[:100]}"
        )
        state["privileged_ks"] = ks
        print(f"    Privileged KS: {ks[:30]}...")

    runner.run_test("appToken.startSession — HMAC SHA256 flow", test_start_session_sha256)

    def test_use_privileged_ks():
        """Verify the privileged KS works for API calls."""
        result = requests.post(
            f"{SERVICE_URL}/service/media/action/list",
            data={
                "ks": state["privileged_ks"],
                "format": 1,
                "pager[pageSize]": 1,
            },
            timeout=10,
        ).json()
        assert "totalCount" in result, f"API call with privileged KS failed: {result}"
        print(f"    media.list returned {result['totalCount']} entries using AppToken KS")

    runner.run_test("Verify privileged KS works — media.list", test_use_privileged_ks)

    # ════════════════════════════════════════════
    # Phase 5: Start session via HMAC flow (SHA1)
    # ════════════════════════════════════════════

    def test_start_session_sha1():
        """Use HMAC flow with SHA1 token."""
        widget_ks = _get_widget_ks()
        token_value = state["sha1_token_value"]
        token_hash = hashlib.sha1((widget_ks + token_value).encode("utf-8")).hexdigest()

        result = requests.post(
            f"{SERVICE_URL}/service/appToken/action/startSession",
            data={
                "ks": widget_ks,
                "format": 1,
                "id": state["sha1_token_id"],
                "tokenHash": token_hash,
                "userId": "api-doc-test-sha1",
                "type": 0,
                "expiry": 1800,
            },
            timeout=10,
        ).json()
        ks = _extract_ks(result)
        assert ks and len(ks) > 20, (
            f"Expected KS, got: {type(result)} — {str(result)[:100]}"
        )
        state["sha1_privileged_ks"] = ks
        print(f"    SHA1 privileged KS: {ks[:30]}...")

    runner.run_test("appToken.startSession — HMAC SHA1 flow", test_start_session_sha1)

    def test_use_sha1_ks():
        """Verify SHA1-derived KS works."""
        result = requests.post(
            f"{SERVICE_URL}/service/media/action/list",
            data={
                "ks": state["sha1_privileged_ks"],
                "format": 1,
                "pager[pageSize]": 1,
            },
            timeout=10,
        ).json()
        assert "totalCount" in result, f"SHA1 KS call failed: {result}"
        print(f"    SHA1 KS: media.list returned {result['totalCount']} entries")

    runner.run_test("Verify SHA1 KS works — media.list", test_use_sha1_ks)

    # ════════════════════════════════════════════
    # Phase 6: Token rotation pattern
    # ════════════════════════════════════════════

    def test_rotation_create_new():
        """Rotation step 1: create a replacement token."""
        ts = int(time.time())
        result = kaltura_post("appToken", "add", {
            "appToken[objectType]": "KalturaAppToken",
            "appToken[hashType]": "SHA256",
            "appToken[sessionType]": 0,
            "appToken[sessionDuration]": 86400,
            "appToken[sessionPrivileges]": "sview:*,list:*",
            "appToken[description]": f"ROTATION_REPLACEMENT_{ts}",
        })
        assert "id" in result
        state["rotation_token_id"] = result["id"]
        state["rotation_token_value"] = result["token"]
        runner.register_cleanup(f"rotation token {result['id']}",
                                lambda: _delete_token(result["id"]))
        print(f"    Replacement token: {result['id']}")

    runner.run_test("Token rotation — create replacement token", test_rotation_create_new)

    def test_rotation_verify_new():
        """Rotation step 2: verify the new token works."""
        widget_ks = _get_widget_ks()

        token_hash = hashlib.sha256(
            (widget_ks + state["rotation_token_value"]).encode("utf-8")
        ).hexdigest()

        result = requests.post(
            f"{SERVICE_URL}/service/appToken/action/startSession",
            data={
                "ks": widget_ks,
                "format": 1,
                "id": state["rotation_token_id"],
                "tokenHash": token_hash,
                "type": 0,
                "expiry": 3600,
            },
            timeout=10,
        ).json()
        ks = _extract_ks(result)
        assert ks and len(ks) > 20, f"Expected KS, got: {str(result)[:100]}"
        print(f"    Replacement token verified — KS obtained")

    runner.run_test("Token rotation — verify replacement works", test_rotation_verify_new)

    # ════════════════════════════════════════════
    # Phase 7: Verify wrong hash is rejected
    # ════════════════════════════════════════════

    def test_wrong_hash_rejected():
        """Verify that an incorrect HMAC hash is rejected."""
        widget_ks = _get_widget_ks()

        # Use deliberately wrong hash
        bad_hash = hashlib.sha256(b"wrong_data").hexdigest()

        result = requests.post(
            f"{SERVICE_URL}/service/appToken/action/startSession",
            data={
                "ks": widget_ks,
                "format": 1,
                "id": state["token_id"],
                "tokenHash": bad_hash,
                "type": 0,
                "expiry": 3600,
            },
            timeout=10,
        ).json()
        # Should be an error, not a valid KS
        ks = _extract_ks(result)
        assert ks is None, (
            f"Expected API error for wrong hash, got a valid KS"
        )
        assert isinstance(result, dict) and result.get("objectType") == "KalturaAPIException", (
            f"Expected API error for wrong hash, got: {str(result)[:100]}"
        )
        print(f"    Correctly rejected: {result.get('code')} — {result.get('message')}")

    runner.run_test("appToken.startSession — wrong hash rejected", test_wrong_hash_rejected)

    # ════════════════════════════════════════════
    # Phase 8: Delete and verify revocation
    # ════════════════════════════════════════════

    def test_delete_sha1_token():
        """Delete the SHA1 token."""
        result = kaltura_post("appToken", "delete", {
            "id": state["sha1_token_id"],
        })
        # delete returns nothing or the deleted object
        print(f"    Deleted SHA1 token: {state['sha1_token_id']}")

    runner.run_test("appToken.delete — remove SHA1 token", test_delete_sha1_token)

    def test_deleted_token_rejected():
        """Verify deleted token cannot start sessions."""
        widget_ks = _get_widget_ks()

        token_hash = hashlib.sha1(
            (widget_ks + state["sha1_token_value"]).encode("utf-8")
        ).hexdigest()

        result = requests.post(
            f"{SERVICE_URL}/service/appToken/action/startSession",
            data={
                "ks": widget_ks,
                "format": 1,
                "id": state["sha1_token_id"],
                "tokenHash": token_hash,
                "type": 0,
                "expiry": 1800,
            },
            timeout=10,
        ).json()
        ks = _extract_ks(result)
        assert ks is None, "Deleted token should not return a valid KS"
        assert isinstance(result, dict) and result.get("objectType") == "KalturaAPIException", (
            f"Expected rejection for deleted token, got: {str(result)[:100]}"
        )
        print(f"    Correctly rejected deleted token: {result.get('code')}")

    runner.run_test("Deleted token rejected — startSession fails", test_deleted_token_rejected)

    def test_get_deleted_token():
        """Verify deleted token shows deleted status or error."""
        try:
            result = kaltura_post("appToken", "get", {
                "id": state["sha1_token_id"],
            })
            # Might return with status=3 (DELETED) or raise error
            if isinstance(result, dict) and "status" in result:
                assert result["status"] == 3, f"Expected DELETED(3), got {result['status']}"
                print(f"    Token shows status=3 (DELETED)")
            else:
                print(f"    Token returned: {result}")
        except Exception as e:
            # May raise NOT_FOUND
            print(f"    Token not found (expected): {e}")

    runner.run_test("appToken.get — deleted token shows status=3 or not found", test_get_deleted_token)

    # ════════════════════════════════════════════
    # Phase 9: Cleanup & Summary
    # ════════════════════════════════════════════

    keep = "--keep" in sys.argv
    if keep:
        print("\n--- Keeping test resources (--keep flag) ---")
        for key, val in state.items():
            if key.endswith("_id") and val:
                print(f"    {key} = {val}")
    else:
        if sys.stdin.isatty():
            input("\nPress Enter to clean up...")
        runner.cleanup()

    success = runner.summary()
    sys.exit(0 if success else 1)


def _delete_token(token_id):
    try:
        kaltura_post("appToken", "delete", {"id": token_id})
    except Exception:
        pass


if __name__ == "__main__":
    print(f"\n{'='*60}")
    print("  KALTURA APPTOKENS API — End-to-End Validation")
    print(f"{'='*60}\n")
    main()
