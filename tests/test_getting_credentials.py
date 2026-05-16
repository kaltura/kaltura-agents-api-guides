#!/usr/bin/env python3
"""End-to-end validation of Kaltura credential setup.

Covers: session.start (ADMIN + USER types), baseEntry.list proof-of-life,
partner.getInfo validation, and invalid secret error handling.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
from test_helpers import kaltura_post, TestRunner, PARTNER_ID, KS, SERVICE_URL

state = {}


def main():
    runner = TestRunner("API Credentials — E2E Validation")

    # ════════════════════════════════════════════
    # Phase 1: Session Generation
    # ════════════════════════════════════════════

    def test_admin_session():
        """Verify session.start with Admin Secret + type=2 produces a valid ADMIN KS."""
        import requests
        admin_secret = os.environ.get("KALTURA_ADMIN_SECRET", "")
        assert admin_secret, "KALTURA_ADMIN_SECRET not set in environment"

        resp = requests.post(f"{SERVICE_URL}/service/session/action/start", data={
            "format": 1,
            "partnerId": PARTNER_ID,
            "secret": admin_secret,
            "type": 2,
            "userId": os.environ.get("KALTURA_USER_ID", "test@example.com"),
        })
        result = resp.json()
        assert isinstance(result, str) and len(result) > 20, f"Expected KS string, got: {result}"
        state["admin_ks"] = result
        print(f"    ADMIN KS generated: {result[:40]}...")

    runner.run_test("session.start — ADMIN KS (type=2)", test_admin_session)

    def test_user_session():
        """Verify session.start with Admin Secret + type=0 produces a valid USER KS."""
        import requests
        admin_secret = os.environ.get("KALTURA_ADMIN_SECRET", "")

        resp = requests.post(f"{SERVICE_URL}/service/session/action/start", data={
            "format": 1,
            "partnerId": PARTNER_ID,
            "secret": admin_secret,
            "type": 0,
            "userId": "credential-test-user",
        })
        result = resp.json()
        assert isinstance(result, str) and len(result) > 20, f"Expected KS string, got: {result}"
        state["user_ks"] = result
        print(f"    USER KS generated: {result[:40]}...")

    runner.run_test("session.start — USER KS (type=0)", test_user_session)

    # ════════════════════════════════════════════
    # Phase 2: Proof of Life
    # ════════════════════════════════════════════

    def test_base_entry_list():
        """Verify the ADMIN KS works with baseEntry.list (proof of life)."""
        result = kaltura_post("baseEntry", "list", {
            "pager[pageSize]": 1,
        })
        assert "totalCount" in result, f"Expected totalCount in response: {result}"
        assert "objects" in result, f"Expected objects array in response: {result}"
        print(f"    Account has {result['totalCount']} entries")

    runner.run_test("baseEntry.list — proof of life with ADMIN KS", test_base_entry_list)

    def test_partner_get_info():
        """Verify partner.getInfo returns the configured Partner ID."""
        result = kaltura_post("partner", "getInfo", {})
        assert "id" in result, f"Expected id in partner info: {result}"
        assert str(result["id"]) == str(PARTNER_ID), \
            f"Expected partnerId={PARTNER_ID}, got {result['id']}"
        print(f"    Partner: {result.get('name', 'N/A')} (ID: {result['id']})")

    runner.run_test("partner.getInfo — verify Partner ID matches", test_partner_get_info)

    # ════════════════════════════════════════════
    # Phase 3: Error Handling
    # ════════════════════════════════════════════

    def test_invalid_secret():
        """Verify invalid secret returns INVALID_SECRET_TYPE error."""
        import requests

        resp = requests.post(f"{SERVICE_URL}/service/session/action/start", data={
            "format": 1,
            "partnerId": PARTNER_ID,
            "secret": "invalid_secret_value_for_testing",
            "type": 2,
            "userId": "test@example.com",
        })
        result = resp.json()
        assert isinstance(result, dict), f"Expected error object, got: {result}"
        assert "code" in result, f"Expected error code in response: {result}"
        print(f"    Error code: {result['code']}, message: {result.get('message', 'N/A')}")

    runner.run_test("session.start — invalid secret returns error", test_invalid_secret)

    # Cleanup & Summary
    success = runner.summary()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
