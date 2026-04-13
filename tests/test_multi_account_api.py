#!/usr/bin/env python3
"""End-to-end validation of the Multi-Account Management API.
Covers: partner.list, partner.get, session.impersonate (self),
session.impersonate (non-child rejection), cross-account report access."""

import sys
import os
import requests

sys.path.insert(0, os.path.dirname(__file__))
from test_helpers import kaltura_post, TestRunner, PARTNER_ID, KS, SERVICE_URL

ADMIN_SECRET = os.environ.get("KALTURA_ADMIN_SECRET", "")

state = {}


def main():
    runner = TestRunner("Multi-Account Management API — E2E Validation")

    # ════════════════════════════════════════════
    # Phase 1: Partner Service Access
    # ════════════════════════════════════════════

    def test_partner_list():
        """Verify partner.list is accessible with customer admin KS."""
        result = kaltura_post("partner", "list", {
            "pager[pageSize]": 10,
            "pager[pageIndex]": 1,
        })
        assert "objects" in result, f"Expected 'objects' in response: {list(result.keys())}"
        assert "totalCount" in result, f"Expected 'totalCount': {list(result.keys())}"
        state["partner_count"] = result["totalCount"]
        for p in result.get("objects", []):
            state.setdefault("partner_ids", []).append(p.get("id"))
        print(f"    Partners: totalCount={result['totalCount']}")

    runner.run_test("partner.list — list accounts", test_partner_list)

    def test_partner_get():
        """Verify partner.get returns own account details."""
        result = kaltura_post("partner", "get", {
            "id": PARTNER_ID,
        })
        assert result.get("id") == int(PARTNER_ID), \
            f"Expected id={PARTNER_ID}, got {result.get('id')}"
        assert "name" in result, f"Expected 'name': {list(result.keys())}"
        assert "status" in result, f"Expected 'status': {list(result.keys())}"
        state["partner_name"] = result.get("name")
        state["partner_parent_id"] = result.get("partnerParentId")
        print(f"    Partner: id={result['id']}, name={result['name']}, "
              f"parentId={result.get('partnerParentId', 'none')}")

    runner.run_test("partner.get — own account details", test_partner_get)

    # ════════════════════════════════════════════
    # Phase 2: session.impersonate
    # ════════════════════════════════════════════

    def test_impersonate_self():
        """Verify session.impersonate works for self-impersonation."""
        if not ADMIN_SECRET:
            print("    SKIP: KALTURA_ADMIN_SECRET not set")
            return
        resp = requests.post(
            f"{SERVICE_URL}/service/session/action/impersonate",
            data={
                "format": 1,
                "secret": ADMIN_SECRET,
                "impersonatedPartnerId": PARTNER_ID,
                "userId": "test_impersonate@example.com",
                "type": 2,
                "partnerId": PARTNER_ID,
                "expiry": 300,
            },
            timeout=15,
        )
        resp.raise_for_status()
        result = resp.json()
        assert isinstance(result, str) and len(result) > 20, \
            f"Expected KS string, got: {str(result)[:100]}"
        state["impersonated_ks"] = result
        print(f"    Got impersonated KS (length={len(result)})")

    runner.run_test("session.impersonate — self-impersonation", test_impersonate_self)

    def test_impersonated_ks_works():
        """Verify the impersonated KS can make API calls."""
        ks = state.get("impersonated_ks")
        if not ks:
            print("    SKIP: No impersonated KS from prior test")
            return
        resp = requests.post(
            f"{SERVICE_URL}/service/system/action/getVersion",
            data={"ks": ks, "format": 1},
            timeout=15,
        )
        resp.raise_for_status()
        result = resp.json()
        assert isinstance(result, str), f"Expected version string, got: {result}"
        print(f"    Impersonated KS verified, API version: {result}")

    runner.run_test("session.impersonate — impersonated KS is functional", test_impersonated_ks_works)

    def test_impersonate_non_child():
        """Verify session.impersonate rejects non-child partner IDs."""
        if not ADMIN_SECRET:
            print("    SKIP: KALTURA_ADMIN_SECRET not set")
            return
        resp = requests.post(
            f"{SERVICE_URL}/service/session/action/impersonate",
            data={
                "format": 1,
                "secret": ADMIN_SECRET,
                "impersonatedPartnerId": 99999,
                "userId": "test@example.com",
                "type": 2,
                "partnerId": PARTNER_ID,
                "expiry": 300,
            },
            timeout=15,
        )
        resp.raise_for_status()
        result = resp.json()
        assert isinstance(result, dict), f"Expected error dict, got: {type(result)}"
        assert result.get("objectType") == "KalturaAPIException", \
            f"Expected KalturaAPIException, got: {result.get('objectType')}"
        print(f"    Correctly rejected: code={result.get('code')}")

    runner.run_test("session.impersonate — rejects non-child partner", test_impersonate_non_child)

    # ════════════════════════════════════════════
    # Phase 3: Cross-Account Reports Access
    # ════════════════════════════════════════════

    def test_report_access():
        """Verify report.getTable is accessible (basic report query)."""
        import time
        now = int(time.time())
        week_ago = now - (7 * 86400)
        result = kaltura_post("report", "getTable", {
            "reportType": 38,  # TOP_CONTENT_CREATOR
            "reportInputFilter[objectType]": "KalturaEndUserReportInputFilter",
            "reportInputFilter[fromDate]": week_ago,
            "reportInputFilter[toDate]": now,
            "pager[pageSize]": 5,
            "pager[pageIndex]": 1,
            "responseOptions[objectType]": "KalturaReportResponseOptions",
            "responseOptions[delimiter]": "|",
        })
        assert isinstance(result, dict), f"Expected dict: {type(result)}"
        print(f"    Report accessible, keys: {list(result.keys())[:5]}")

    runner.run_test("report.getTable — basic report access", test_report_access)

    # ════════════════════════════════════════════
    # Cleanup & Summary
    # ════════════════════════════════════════════
    runner.cleanup()
    success = runner.summary()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
