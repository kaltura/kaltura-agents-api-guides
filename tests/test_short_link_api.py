#!/usr/bin/env python3
"""End-to-end validation of the Short Link API. Covers: add, get, list, update, delete, goto"""

import sys
import os
import time
import requests

sys.path.insert(0, os.path.dirname(__file__))
from test_helpers import kaltura_post, TestRunner, PARTNER_ID, KS, SERVICE_URL

state = {}

SHORTLINK_SERVICE = "shortlink_shortlink"


def _shortlink_post(action, params=None):
    """POST to shortlink_shortlink service."""
    return kaltura_post(SHORTLINK_SERVICE, action, params or {})


def main():
    runner = TestRunner("Short Link API — E2E Validation")

    # ════════════════════════════════════════════
    # Phase 1: Create short links
    # ════════════════════════════════════════════

    def test_add_basic():
        """Create a basic short link."""
        result = _shortlink_post("add", {
            "shortLink[objectType]": "KalturaShortLink",
            "shortLink[systemName]": "TEST-BASIC-LINK",
            "shortLink[fullUrl]": "https://kaltura.md/raw/KALTURA_API_GETTING_STARTED.md",
            "shortLink[status]": 2,
        })
        assert "id" in result, f"Expected id in response: {result}"
        assert result["status"] == 2, f"Expected status=2, got {result['status']}"
        assert result["systemName"] == "TEST-BASIC-LINK", f"Wrong systemName: {result['systemName']}"
        state["link_id"] = result["id"]
        runner.register_cleanup(
            f"shortlink {result['id']}",
            lambda: _shortlink_post("delete", {"id": state["link_id"]})
        )
        print(f"    Created: {result['id']} -> {result['fullUrl'][:50]}...")

    runner.run_test("shortLink.add — basic creation", test_add_basic)

    def test_add_with_expiry():
        """Create a short link with expiration."""
        expires_at = int(time.time()) + 86400 * 7  # 7 days
        result = _shortlink_post("add", {
            "shortLink[objectType]": "KalturaShortLink",
            "shortLink[systemName]": "TEST-EXPIRING-LINK",
            "shortLink[fullUrl]": "https://kaltura.md/llms.txt",
            "shortLink[status]": 2,
            "shortLink[expiresAt]": expires_at,
            "shortLink[name]": "Test Expiring Link",
        })
        assert "id" in result, f"Expected id in response: {result}"
        assert result.get("expiresAt") == expires_at, f"Expected expiresAt={expires_at}, got {result.get('expiresAt')}"
        state["expiring_link_id"] = result["id"]
        runner.register_cleanup(
            f"shortlink {result['id']}",
            lambda: _shortlink_post("delete", {"id": state["expiring_link_id"]})
        )
        print(f"    Created: {result['id']}, expires={expires_at}, name={result.get('name')}")

    runner.run_test("shortLink.add — with expiration", test_add_with_expiry)

    def test_add_disabled():
        """Create a disabled short link."""
        result = _shortlink_post("add", {
            "shortLink[objectType]": "KalturaShortLink",
            "shortLink[systemName]": "TEST-DISABLED-LINK",
            "shortLink[fullUrl]": "https://kaltura.md/raw/README.md",
            "shortLink[status]": 1,
        })
        assert "id" in result, f"Expected id in response: {result}"
        assert result["status"] == 1, f"Expected status=1 (DISABLED), got {result['status']}"
        state["disabled_link_id"] = result["id"]
        runner.register_cleanup(
            f"shortlink {result['id']}",
            lambda: _shortlink_post("delete", {"id": state["disabled_link_id"]})
        )
        print(f"    Created disabled: {result['id']}")

    runner.run_test("shortLink.add — disabled status", test_add_disabled)

    def test_add_validation_systemname():
        """Verify systemName is required and has min length."""
        try:
            _shortlink_post("add", {
                "shortLink[objectType]": "KalturaShortLink",
                "shortLink[fullUrl]": "https://kaltura.md/raw/README.md",
                "shortLink[status]": 2,
            })
            assert False, "Expected validation error for missing systemName"
        except Exception as e:
            assert "PROPERTY_VALIDATION" in str(e) or "systemName" in str(e), f"Unexpected error: {e}"
            print(f"    Correctly rejected: {str(e)[:70]}")

    runner.run_test("shortLink.add — validates systemName required", test_add_validation_systemname)

    def test_add_validation_fullurl():
        """Verify fullUrl is required."""
        try:
            _shortlink_post("add", {
                "shortLink[objectType]": "KalturaShortLink",
                "shortLink[systemName]": "TEST-NO-URL",
                "shortLink[status]": 2,
            })
            assert False, "Expected validation error for missing fullUrl"
        except Exception as e:
            assert "PROPERTY_VALIDATION" in str(e) or "fullUrl" in str(e), f"Unexpected error: {e}"
            print(f"    Correctly rejected: {str(e)[:70]}")

    runner.run_test("shortLink.add — validates fullUrl required", test_add_validation_fullurl)

    # ════════════════════════════════════════════
    # Phase 2: Get and resolve
    # ════════════════════════════════════════════

    def test_get():
        """Retrieve a short link by ID."""
        result = _shortlink_post("get", {"id": state["link_id"]})
        assert result.get("id") == state["link_id"], f"Expected id={state['link_id']}, got {result.get('id')}"
        assert result.get("systemName") == "TEST-BASIC-LINK"
        assert result.get("fullUrl") == "https://kaltura.md/raw/KALTURA_API_GETTING_STARTED.md"
        print(f"    Got: {result['id']}, system={result['systemName']}")

    runner.run_test("shortLink.get — retrieve by ID", test_get)

    def test_get_invalid():
        """Verify get with invalid ID returns error."""
        try:
            _shortlink_post("get", {"id": "nonexistent_id_xyz"})
            assert False, "Expected INVALID_OBJECT_ID error"
        except Exception as e:
            assert "INVALID_OBJECT_ID" in str(e), f"Unexpected error: {e}"
            print(f"    Correctly rejected: INVALID_OBJECT_ID")

    runner.run_test("shortLink.get — invalid ID error", test_get_invalid)

    def test_goto_redirect():
        """Test goto action returns 302 redirect."""
        url = f"{SERVICE_URL}/service/{SHORTLINK_SERVICE}/action/goto/id/{state['link_id']}"
        resp = requests.get(url, allow_redirects=False)
        assert resp.status_code == 302, f"Expected 302, got {resp.status_code}"
        location = resp.headers.get("Location", "")
        assert "KALTURA_API_GETTING_STARTED" in location, f"Unexpected redirect: {location}"
        print(f"    302 -> {location[:60]}...")

    runner.run_test("shortLink.goto — redirect to fullUrl", test_goto_redirect)

    def test_goto_disabled_rejected():
        """Verify goto rejects disabled links."""
        url = f"{SERVICE_URL}/service/{SHORTLINK_SERVICE}/action/goto/id/{state['disabled_link_id']}"
        resp = requests.get(url, allow_redirects=False)
        assert resp.status_code != 302, f"Expected non-redirect for disabled link, got 302"
        print(f"    Disabled link rejected: status={resp.status_code}")

    runner.run_test("shortLink.goto — rejects disabled link", test_goto_disabled_rejected)

    def test_tiny_url_format():
        """Test /tiny/{id} URL format (301 -> goto)."""
        # Extract host from SERVICE_URL
        from urllib.parse import urlparse
        parsed = urlparse(SERVICE_URL)
        tiny_url = f"{parsed.scheme}://{parsed.hostname}/tiny/{state['link_id']}"
        resp = requests.get(tiny_url, allow_redirects=False)
        assert resp.status_code == 301, f"Expected 301 from /tiny/, got {resp.status_code}"
        location = resp.headers.get("Location", "")
        assert "shortLink" in location.lower() or "shortlink" in location.lower(), \
            f"Expected redirect to shortLink goto: {location}"
        print(f"    /tiny/{state['link_id']} -> 301 -> {location[:60]}...")

    runner.run_test("shortLink /tiny/ URL — 301 redirect format", test_tiny_url_format)

    # ════════════════════════════════════════════
    # Phase 3: List and filter
    # ════════════════════════════════════════════

    def test_list_all():
        """List all enabled short links."""
        result = _shortlink_post("list", {
            "filter[statusEqual]": 2,
            "filter[orderBy]": "-createdAt",
            "pager[pageSize]": 10,
            "pager[pageIndex]": 1,
        })
        assert "objects" in result, f"Expected objects in response: {result}"
        assert "totalCount" in result, f"Expected totalCount: {result}"
        assert result["totalCount"] > 0, f"Expected at least 1 link, got {result['totalCount']}"
        print(f"    Listed: {len(result['objects'])} of {result['totalCount']} total")

    runner.run_test("shortLink.list — all enabled links", test_list_all)

    def test_list_by_system_name():
        """Filter by systemName."""
        result = _shortlink_post("list", {
            "filter[systemNameEqual]": "TEST-BASIC-LINK",
            "pager[pageSize]": 10,
        })
        assert "objects" in result, f"Expected objects: {result}"
        objects = result.get("objects", [])
        assert len(objects) >= 1, f"Expected at least 1 result for TEST-BASIC-LINK, got {len(objects)}"
        assert objects[0]["systemName"] == "TEST-BASIC-LINK"
        print(f"    systemNameEqual filter: found {len(objects)} link(s)")

    runner.run_test("shortLink.list — filter by systemName", test_list_by_system_name)

    def test_list_by_id_in():
        """Filter by idIn."""
        ids = ",".join([state["link_id"], state.get("expiring_link_id", "")])
        result = _shortlink_post("list", {
            "filter[idIn]": ids,
            "pager[pageSize]": 10,
        })
        objects = result.get("objects", [])
        assert len(objects) >= 1, f"Expected results for idIn, got {len(objects)}"
        returned_ids = [o["id"] for o in objects]
        assert state["link_id"] in returned_ids, f"Expected {state['link_id']} in results"
        print(f"    idIn filter: {len(objects)} result(s)")

    runner.run_test("shortLink.list — filter by idIn", test_list_by_id_in)

    def test_list_order_by():
        """List with orderBy."""
        result = _shortlink_post("list", {
            "filter[statusEqual]": 2,
            "filter[orderBy]": "+createdAt",
            "pager[pageSize]": 5,
        })
        objects = result.get("objects", [])
        if len(objects) >= 2:
            assert objects[0]["createdAt"] <= objects[1]["createdAt"], \
                f"Order not ascending: {objects[0]['createdAt']} > {objects[1]['createdAt']}"
        print(f"    orderBy +createdAt: {len(objects)} results")

    runner.run_test("shortLink.list — orderBy createdAt ascending", test_list_order_by)

    def test_list_paging():
        """Test pager functionality."""
        result1 = _shortlink_post("list", {
            "filter[statusEqual]": 2,
            "filter[orderBy]": "-createdAt",
            "pager[pageSize]": 2,
            "pager[pageIndex]": 1,
        })
        objects1 = result1.get("objects", [])
        total = result1.get("totalCount", 0)
        if total <= 2:
            print(f"    Only {total} links, skip paging test")
            return
        result2 = _shortlink_post("list", {
            "filter[statusEqual]": 2,
            "filter[orderBy]": "-createdAt",
            "pager[pageSize]": 2,
            "pager[pageIndex]": 2,
        })
        objects2 = result2.get("objects", [])
        if objects1 and objects2:
            assert objects1[0]["id"] != objects2[0]["id"], "Page 1 and 2 returned same first item"
        print(f"    Paging: page1={len(objects1)}, page2={len(objects2)}, total={total}")

    runner.run_test("shortLink.list — pager offset", test_list_paging)

    # ════════════════════════════════════════════
    # Phase 4: Update
    # ════════════════════════════════════════════

    def test_update_name():
        """Update display name."""
        result = _shortlink_post("update", {
            "id": state["link_id"],
            "shortLink[objectType]": "KalturaShortLink",
            "shortLink[name]": "Updated Test Link Name",
        })
        assert result.get("name") == "Updated Test Link Name", \
            f"Expected updated name, got {result.get('name')}"
        print(f"    Updated name: {result['name']}")

    runner.run_test("shortLink.update — change name", test_update_name)

    def test_update_full_url():
        """Update destination URL."""
        new_url = "https://kaltura.md/raw/KALTURA_SESSION_GUIDE.md"
        result = _shortlink_post("update", {
            "id": state["link_id"],
            "shortLink[objectType]": "KalturaShortLink",
            "shortLink[fullUrl]": new_url,
        })
        assert result.get("fullUrl") == new_url, f"Expected new URL, got {result.get('fullUrl')}"
        print(f"    Updated fullUrl: {result['fullUrl'][:50]}...")

    runner.run_test("shortLink.update — change fullUrl", test_update_full_url)

    def test_update_disable():
        """Disable a short link via update."""
        result = _shortlink_post("update", {
            "id": state["link_id"],
            "shortLink[objectType]": "KalturaShortLink",
            "shortLink[status]": 1,
        })
        assert result.get("status") == 1, f"Expected status=1, got {result.get('status')}"
        print(f"    Disabled: status={result['status']}")

        # Re-enable for remaining tests
        _shortlink_post("update", {
            "id": state["link_id"],
            "shortLink[objectType]": "KalturaShortLink",
            "shortLink[status]": 2,
        })

    runner.run_test("shortLink.update — disable and re-enable", test_update_disable)

    def test_update_invalid_id():
        """Verify update with invalid ID returns error."""
        try:
            _shortlink_post("update", {
                "id": "nonexistent_xyz",
                "shortLink[objectType]": "KalturaShortLink",
                "shortLink[name]": "Should Fail",
            })
            assert False, "Expected INVALID_OBJECT_ID error"
        except Exception as e:
            assert "INVALID_OBJECT_ID" in str(e), f"Unexpected error: {e}"
            print(f"    Correctly rejected: INVALID_OBJECT_ID")

    runner.run_test("shortLink.update — invalid ID error", test_update_invalid_id)

    # ════════════════════════════════════════════
    # Phase 5: Delete
    # ════════════════════════════════════════════

    def test_delete():
        """Delete a short link (soft delete)."""
        result = _shortlink_post("delete", {"id": state["link_id"]})
        assert result.get("status") == 3, f"Expected status=3 (DELETED), got {result.get('status')}"
        state["link_deleted"] = True
        print(f"    Deleted: {result['id']}, status={result['status']}")

    runner.run_test("shortLink.delete — soft delete", test_delete)

    def test_goto_after_delete():
        """Verify goto rejects deleted links."""
        url = f"{SERVICE_URL}/service/{SHORTLINK_SERVICE}/action/goto/id/{state['link_id']}"
        resp = requests.get(url, allow_redirects=False)
        assert resp.status_code != 302, f"Expected non-redirect for deleted link, got 302"
        print(f"    Deleted link rejected: status={resp.status_code}")

    runner.run_test("shortLink.goto — rejects deleted link", test_goto_after_delete)

    def test_delete_invalid_id():
        """Verify delete with invalid ID returns error."""
        try:
            _shortlink_post("delete", {"id": "nonexistent_xyz"})
            assert False, "Expected INVALID_OBJECT_ID error"
        except Exception as e:
            assert "INVALID_OBJECT_ID" in str(e), f"Unexpected error: {e}"
            print(f"    Correctly rejected: INVALID_OBJECT_ID")

    runner.run_test("shortLink.delete — invalid ID error", test_delete_invalid_id)

    # ════════════════════════════════════════════
    # Cleanup & Summary
    # ════════════════════════════════════════════

    keep = "--keep" in sys.argv
    if keep:
        print("\n  --keep flag set. Resources preserved:")
        for key, val in state.items():
            if "_id" in key:
                print(f"    {key}: {val}")
    else:
        if sys.stdin.isatty() and not state.get("link_deleted"):
            input("\n  Press Enter to clean up...")
        runner.cleanup()

    success = runner.summary()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
