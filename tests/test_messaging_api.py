#!/usr/bin/env python3
"""
End-to-end validation of the Messaging API against the live API.

Covers: email-template CRUD (add + get + update + list + delete + not-found),
unsubscribe-uri CRUD (add + get + update + list + delete),
message list (empty + filtered), message stats, message listGroupedBySession,
unsubscribe-groups list, email-provider list + lookup,
cross-service app registry integration.
"""

import sys
import os
import time
import requests

sys.path.insert(0, os.path.dirname(__file__))
from test_helpers import (
    messaging_post, app_registry_post, TestRunner, PARTNER_ID, KS,
    MESSAGING_URL, APP_REGISTRY_URL,
)

state = {}
TS = int(time.time())


def _check_messaging_connectivity():
    """Check if the Messaging API is reachable. Returns (ok, detail)."""
    try:
        headers = {
            "Authorization": f"Bearer {KS}",
            "Content-Type": "application/json",
        }
        resp = requests.post(
            f"{MESSAGING_URL}/email-template/list",
            headers=headers,
            json={},
            timeout=10,
        )
        if resp.status_code == 403 and "cloudfront" in resp.headers.get("Server", "").lower():
            return False, "CloudFront 403 — messaging service not accessible from this network"
        if resp.status_code == 403:
            return False, f"403 Forbidden — partner may not be provisioned for messaging"
        return True, f"HTTP {resp.status_code}"
    except requests.ConnectionError as e:
        return False, f"Connection error: {e}"
    except Exception as e:
        return False, f"Connectivity check failed: {e}"


def main():
    runner = TestRunner("Messaging API — E2E Validation")

    # ════════════════════════════════════════════
    # Connectivity check
    # ════════════════════════════════════════════
    ok, detail = _check_messaging_connectivity()
    if not ok:
        print(f"\n  SKIP  Messaging API not accessible: {detail}")
        print(f"         URL: {MESSAGING_URL}")
        print(f"         The messaging service requires partner provisioning.")
        print(f"         Contact your Kaltura account manager to enable messaging.\n")
        # Still report as a structured result
        runner.results.append(("connectivity — messaging API reachable", False, detail))
        runner.summary()
        sys.exit(1)
    print(f"  OK    Messaging API reachable ({detail})\n")

    # ════════════════════════════════════════════
    # Phase 0: Setup — create an App Registry entry for context
    # ════════════════════════════════════════════
    def test_setup_app():
        """Create a test app in App Registry for messaging context."""
        result = app_registry_post("add", {
            "appCustomId": f"test-msg-app-{TS}",
            "appType": "test",
            "appCustomName": f"Messaging Test App {TS}",
        })
        assert "id" in result, f"Expected id in response: {result}"
        state["app_guid"] = result["id"]
        state["app_custom_id"] = f"test-msg-app-{TS}"
        runner.register_cleanup(
            f"app {result['id']}",
            lambda: app_registry_post("delete", {"id": state["app_guid"]}),
        )
        print(f"    App created: {result['id']} (appCustomId={state['app_custom_id']})")

    runner.run_test("setup — create App Registry entry for messaging context", test_setup_app)

    # ════════════════════════════════════════════
    # Phase 1: Email Template CRUD
    # ════════════════════════════════════════════
    def test_template_add():
        """Create an email template with User and String tokens."""
        result = messaging_post("email-template", "add", {
            "appGuid": state["app_guid"],
            "name": f"Test Template {TS}",
            "subject": "Hello {recipient.firstName}, welcome to {eventName}",
            "body": "<p>Hi {recipient.firstName},</p><p>You are invited to {eventName}.</p>",
            "toAttributePath": "{recipient.email}",
            "msgParamsMap": {
                "recipient": {"type": "User"},
                "eventName": {"type": "String"},
            },
            "unsubscribeGroups": [f"test-group-{TS}"],
        })
        assert "id" in result, f"Expected id in response: {result}"
        assert result.get("name") == f"Test Template {TS}", \
            f"Expected name match, got {result.get('name')}"
        assert result.get("version") == 0, \
            f"Expected version=0, got {result.get('version')}"
        assert result.get("status") == "enabled", \
            f"Expected status=enabled, got {result.get('status')}"
        assert result.get("createdAt") is not None, \
            f"Expected createdAt in response, got None"
        state["template_id"] = result["id"]
        runner.register_cleanup(
            f"template {result['id']}",
            lambda: messaging_post("email-template", "delete", {"id": state["template_id"]}),
        )
        print(f"    Template created: {result['id']} (version={result['version']})")

    runner.run_test("email-template.add — create template with tokens", test_template_add)

    def test_template_get():
        """Retrieve template by ID and verify all fields."""
        result = messaging_post("email-template", "get", {"id": state["template_id"]})
        assert result["id"] == state["template_id"], f"ID mismatch: {result.get('id')}"
        assert result["appGuid"] == state["app_guid"], \
            f"appGuid mismatch: {result.get('appGuid')}"
        assert result["name"] == f"Test Template {TS}", \
            f"name mismatch: {result.get('name')}"
        assert "msgParamsMap" in result, f"Expected msgParamsMap in response"
        assert "recipient" in result["msgParamsMap"], \
            f"Expected 'recipient' token in msgParamsMap"
        assert result["msgParamsMap"]["recipient"]["type"] == "User", \
            f"Expected User type for recipient token"
        print(f"    Got: {result['id']}, name={result['name']}, tokens={list(result['msgParamsMap'].keys())}")

    runner.run_test("email-template.get — retrieve by ID", test_template_get)

    def test_template_update():
        """Update template subject and verify version increment."""
        before = messaging_post("email-template", "get", {"id": state["template_id"]})
        result = messaging_post("email-template", "update", {
            "id": state["template_id"],
            "subject": "Updated: Hello {recipient.firstName}",
            "description": "Updated test template",
        })
        assert result["subject"] == "Updated: Hello {recipient.firstName}", \
            f"Expected updated subject, got {result.get('subject')}"
        assert result.get("description") == "Updated test template", \
            f"Expected updated description, got {result.get('description')}"
        assert result["version"] == before["version"] + 1, \
            f"Expected version {before['version'] + 1}, got {result.get('version')}"
        # Name should be unchanged
        assert result["name"] == before["name"], \
            f"Name changed unexpectedly: {result.get('name')}"
        print(f"    Updated: subject='{result['subject']}', version={result['version']}")

    runner.run_test("email-template.update — change subject, verify version+1", test_template_update)

    def test_template_list_with_filter():
        """List templates with appGuid filter, verify our template is included."""
        result = messaging_post("email-template", "list", {
            "filter": {"appGuidIn": [state["app_guid"]], "status": "enabled"},
            "pager": {"offset": 0, "limit": 50},
        })
        assert "objects" in result, f"Expected objects in response: {result}"
        assert "totalCount" in result, f"Expected totalCount in response: {result}"
        ids = [obj["id"] for obj in result["objects"]]
        assert state["template_id"] in ids, \
            f"Expected {state['template_id']} in list results"
        print(f"    Listed {result['totalCount']} template(s) for appGuid={state['app_guid']}")

    runner.run_test("email-template.list — filter by appGuid", test_template_list_with_filter)

    def test_template_list_no_filter():
        """List templates with no filter returns all templates for the partner."""
        result = messaging_post("email-template", "list", {})
        assert "objects" in result, f"Expected objects: {result}"
        assert result["totalCount"] >= 1, \
            f"Expected at least 1 template, got {result['totalCount']}"
        print(f"    All templates: {result['totalCount']} total (no filter)")

    runner.run_test("email-template.list — no filter returns all templates", test_template_list_no_filter)

    def test_template_get_not_found():
        """Getting a non-existent ID returns an error."""
        try:
            messaging_post("email-template", "get", {"id": "000000000000000000000000"})
            raise AssertionError("Expected error for non-existent template, got success")
        except Exception as e:
            err = str(e)
            assert "not found" in err.lower() or "OBJECT_NOT_FOUND" in err \
                or "404" in err or "does not exist" in err.lower(), \
                f"Expected not-found error, got: {err}"
        print("    Correctly returned error for non-existent template ID")

    runner.run_test("email-template.get — error for invalid ID", test_template_get_not_found)

    # ════════════════════════════════════════════
    # Phase 2: Unsubscribe URI CRUD
    # ════════════════════════════════════════════
    def test_unsubscribe_uri_add():
        """Create an unsubscribe URI for the test app."""
        result = messaging_post("unsubscribe-uri", "add", {
            "appGuid": state["app_guid"],
            "uri": f"https://test-{TS}.example.com/unsubscribe",
        })
        assert "id" in result, f"Expected id in response: {result}"
        assert result.get("appGuid") == state["app_guid"], \
            f"appGuid mismatch: {result.get('appGuid')}"
        assert result.get("status") == "enabled", \
            f"Expected status=enabled, got {result.get('status')}"
        assert result.get("version") == 0, \
            f"Expected version=0, got {result.get('version')}"
        state["uri_id"] = result["id"]
        runner.register_cleanup(
            f"unsubscribe-uri {result['id']}",
            lambda: messaging_post("unsubscribe-uri", "delete", {"id": state["uri_id"]}),
        )
        print(f"    URI created: {result['id']} (uri={result.get('uri')})")

    runner.run_test("unsubscribe-uri.add — create URI", test_unsubscribe_uri_add)

    def test_unsubscribe_uri_get():
        """Retrieve unsubscribe URI by ID."""
        result = messaging_post("unsubscribe-uri", "get", {"id": state["uri_id"]})
        assert result["id"] == state["uri_id"], f"ID mismatch: {result.get('id')}"
        assert result["appGuid"] == state["app_guid"], \
            f"appGuid mismatch: {result.get('appGuid')}"
        assert f"test-{TS}.example.com" in result.get("uri", ""), \
            f"URI mismatch: {result.get('uri')}"
        print(f"    Got: {result['id']}, uri={result['uri']}")

    runner.run_test("unsubscribe-uri.get — retrieve by ID", test_unsubscribe_uri_get)

    def test_unsubscribe_uri_update():
        """Update unsubscribe URI and verify version increment."""
        before = messaging_post("unsubscribe-uri", "get", {"id": state["uri_id"]})
        result = messaging_post("unsubscribe-uri", "update", {
            "id": state["uri_id"],
            "uri": f"https://test-{TS}.example.com/unsubscribe-v2",
        })
        assert "unsubscribe-v2" in result.get("uri", ""), \
            f"Expected updated URI, got {result.get('uri')}"
        assert result["version"] == before["version"] + 1, \
            f"Expected version {before['version'] + 1}, got {result.get('version')}"
        print(f"    Updated: uri={result['uri']}, version={result['version']}")

    runner.run_test("unsubscribe-uri.update — change URI, verify version+1", test_unsubscribe_uri_update)

    def test_unsubscribe_uri_list():
        """List unsubscribe URIs with appGuid filter."""
        result = messaging_post("unsubscribe-uri", "list", {
            "filter": {"appGuidIn": [state["app_guid"]]},
            "pager": {"offset": 0, "limit": 25},
        })
        assert "objects" in result, f"Expected objects in response: {result}"
        ids = [obj["id"] for obj in result["objects"]]
        assert state["uri_id"] in ids, \
            f"Expected {state['uri_id']} in list results"
        print(f"    Listed {result['totalCount']} URI(s) for appGuid={state['app_guid']}")

    runner.run_test("unsubscribe-uri.list — filter by appGuid", test_unsubscribe_uri_list)

    def test_unsubscribe_uri_delete():
        """Delete unsubscribe URI and verify it's gone."""
        messaging_post("unsubscribe-uri", "delete", {"id": state["uri_id"]})

        # Verify it's gone
        try:
            messaging_post("unsubscribe-uri", "get", {"id": state["uri_id"]})
            raise AssertionError("Expected error after delete")
        except Exception as e:
            err = str(e)
            assert "not found" in err.lower() or "OBJECT_NOT_FOUND" in err \
                or "404" in err or "does not exist" in err.lower() \
                or "deleted" in err.lower(), \
                f"Expected not-found error, got: {err}"

        # Remove from cleanup
        runner._cleanup_actions = [
            (label, fn) for label, fn in runner._cleanup_actions
            if "unsubscribe-uri" not in label
        ]
        print(f"    Deleted {state['uri_id']} — verified gone")

    runner.run_test("unsubscribe-uri.delete — permanent removal verified", test_unsubscribe_uri_delete)

    # ════════════════════════════════════════════
    # Phase 3: Message Operations (read-only)
    # ════════════════════════════════════════════
    def test_message_list():
        """List messages (may be empty for test account)."""
        result = messaging_post("message", "list", {
            "pager": {"offset": 0, "limit": 10},
        })
        assert "objects" in result, f"Expected objects in response: {result}"
        assert "totalCount" in result, f"Expected totalCount in response: {result}"
        assert isinstance(result["objects"], list), \
            f"Expected objects to be a list, got {type(result['objects'])}"
        print(f"    Listed {result['totalCount']} message(s)")

    runner.run_test("message.list — list messages", test_message_list)

    def test_message_list_with_filter():
        """List messages filtered by appGuid."""
        result = messaging_post("message", "list", {
            "filter": {"appGuidIn": [state["app_guid"]]},
            "pager": {"offset": 0, "limit": 10},
        })
        assert "objects" in result, f"Expected objects in response: {result}"
        # New app, so expect 0 messages
        assert result["totalCount"] == 0, \
            f"Expected 0 messages for new app, got {result['totalCount']}"
        print(f"    Listed {result['totalCount']} message(s) for appGuid={state['app_guid']}")

    runner.run_test("message.list — filter by appGuid (empty result)", test_message_list_with_filter)

    def test_message_stats():
        """Get message stats (empty for a non-existent session)."""
        result = messaging_post("message", "stats", {
            "session": f"nonexistent-session-{TS}",
        })
        # Stats for a non-existent session should return empty/zero counts
        assert isinstance(result, dict), f"Expected dict response, got {type(result)}"
        print(f"    Stats response: {result}")

    runner.run_test("message.stats — stats for non-existent session", test_message_stats)

    def test_message_list_grouped_by_session():
        """List messages grouped by session."""
        result = messaging_post("message", "listGroupedBySession", {
            "filter": {"appGuidIn": [state["app_guid"]]},
            "pager": {"offset": 0, "limit": 10},
        })
        assert "objects" in result, f"Expected objects in response: {result}"
        assert "totalCount" in result, f"Expected totalCount in response: {result}"
        print(f"    Grouped sessions: {result['totalCount']} total")

    runner.run_test("message.listGroupedBySession — list grouped messages", test_message_list_grouped_by_session)

    def test_discrete_aggregate_messages():
        """List discrete aggregate messages (empty for test app)."""
        result = messaging_post("message", "listDiscreteAggregateMessages", {
            "filter": {"appGuidIn": [state["app_guid"]]},
            "pager": {"offset": 0, "limit": 10},
        })
        assert "objects" in result, f"Expected objects in response: {result}"
        assert result["totalCount"] == 0, \
            f"Expected 0 discrete messages for new app, got {result['totalCount']}"
        print(f"    Discrete messages: {result['totalCount']} total")

    runner.run_test("message.listDiscreteAggregateMessages — empty for new app", test_discrete_aggregate_messages)

    # ════════════════════════════════════════════
    # Phase 4: Unsubscribe Groups
    # ════════════════════════════════════════════
    def test_unsubscribe_groups_list():
        """List unsubscribe groups (should include our template's group)."""
        result = messaging_post("unsubscribe-groups", "list", {})
        assert isinstance(result, (list, dict)), \
            f"Expected list or dict response, got {type(result)}"
        # The response may be a list of group names or an object with groups
        if isinstance(result, list):
            groups = result
        elif "objects" in result:
            groups = result["objects"]
        else:
            groups = list(result.keys()) if result else []
        print(f"    Unsubscribe groups: {len(groups)} group(s)")

    runner.run_test("unsubscribe-groups.list — list all groups", test_unsubscribe_groups_list)

    # ════════════════════════════════════════════
    # Phase 5: Email Provider Queries
    # ════════════════════════════════════════════
    def test_email_provider_list():
        """List email providers for the partner."""
        result = messaging_post("email-provider", "list", {})
        assert "objects" in result, f"Expected objects in response: {result}"
        assert "totalCount" in result, f"Expected totalCount in response: {result}"
        print(f"    Email providers: {result['totalCount']} total")

    runner.run_test("email-provider.list — list providers", test_email_provider_list)

    def test_email_provider_lookup():
        """Lookup which provider resolves for our test app."""
        result = messaging_post("email-provider", "lookup", {
            "appGuid": state["app_guid"],
        })
        # Should return a provider (either partner-specific or default)
        assert isinstance(result, dict), f"Expected dict response, got {type(result)}"
        if "id" in result:
            print(f"    Provider resolved: {result['id']} (type={result.get('type')})")
        else:
            print(f"    Provider lookup response: {result}")

    runner.run_test("email-provider.lookup — resolve provider for app", test_email_provider_lookup)

    # ════════════════════════════════════════════
    # Phase 6: Template Delete + Verify
    # ════════════════════════════════════════════
    def test_template_delete():
        """Delete template and verify it's gone from list."""
        messaging_post("email-template", "delete", {"id": state["template_id"]})

        # Verify excluded from filtered list
        result = messaging_post("email-template", "list", {
            "filter": {"idIn": [state["template_id"]], "status": "enabled"},
        })
        matching = [obj for obj in result["objects"] if obj["id"] == state["template_id"]]
        assert len(matching) == 0, \
            f"Expected template gone from enabled list, found {len(matching)}"

        # Remove from cleanup
        runner._cleanup_actions = [
            (label, fn) for label, fn in runner._cleanup_actions
            if "template" not in label
        ]
        print(f"    Deleted template {state['template_id']} — verified gone from enabled list")

    runner.run_test("email-template.delete — permanent removal verified", test_template_delete)

    # ════════════════════════════════════════════
    # Cleanup & Summary
    # ════════════════════════════════════════════
    keep = "--keep" in sys.argv
    if keep:
        print(f"\n--keep flag set. Resources preserved:")
        print(f"  App GUID: {state.get('app_guid')}")
        print(f"\n  Clean up manually:")
        app_guid = state.get('app_guid')
        print(f'    curl -X POST "{APP_REGISTRY_URL}/app-registry/delete" \\')
        print(f'      -H "Authorization: Bearer $KS" \\')
        print(f'      -H "Content-Type: application/json" \\')
        print(f'      -d \'{{"id": "{app_guid}"}}\'')
    else:
        if sys.stdin.isatty():
            input("\nPress Enter to clean up...")
        runner.cleanup()

    success = runner.summary()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
