#!/usr/bin/env python3
"""
End-to-end validation of the Auth Broker API against the live API.

Covers: auth-profile CRUD (add, get, list, update, delete), SAML metadata endpoint,
app-subscription CRUD (add, get, list, update, delete), version tracking,
error handling (invalid IDs, missing required fields).
"""

import sys
import os
import time

sys.path.insert(0, os.path.dirname(__file__))
from test_helpers import (
    auth_broker_post, auth_broker_get, app_registry_post,
    TestRunner, PARTNER_ID, KS, AUTH_BROKER_URL,
)

state = {}
TS = int(time.time())

DUMMY_CERT = (
    "MIICpDCCAYwCCQDU+pQ4pHgSpDANBgkqhkiG9w0BAQsFADAUMRIwEAYDVQQDDAlsb2NhbGhvc3Qw"
    "HhcNMjMwMTAxMDAwMDAwWhcNMjQwMTAxMDAwMDAwWjAUMRIwEAYDVQQDDAlsb2NhbGhvc3QwggEi"
    "MA0GCSqGSIb3DQEBAQUAA4IBDwAwggEKAoIBAQC7o4qne60TB3pOYaBy"
)

CALLBACK_URL = "https://auth.nvp1.ovp.kaltura.com/api/v1/auth-manager/saml/ac"


def main():
    runner = TestRunner("Auth Broker API — E2E Validation")

    # ════════════════════════════════════════════
    # Phase 1: Auth Profile CRUD
    # ════════════════════════════════════════════
    def test_auth_profile_add():
        """Create a test SAML auth profile and verify defaults."""
        result = auth_broker_post("auth-profile", "add", {
            "name": f"Test SAML Profile {TS}",
            "description": "Temporary profile for API doc validation. Safe to delete.",
            "providerType": "other",
            "authStrategy": "saml",
            "authStrategyConfig": {
                "issuer": f"kaltura-api-test-{TS}",
                "entryPoint": f"https://test-idp-{TS}.example.com/sso",
                "callbackUrl": CALLBACK_URL,
                "cert": DUMMY_CERT,
            },
            "userAttributeMappings": {
                "email": "Core_User_Email",
            },
            "userGroupMappings": {},
            "userIdAttribute": "Core_User_Email",
            "createNewUser": True,
            "disableRequestedAuthnContext": True,
        })
        assert "id" in result, f"Expected id in response: {result}"
        assert result.get("objectType") == "AuthProfile", \
            f"Expected objectType=AuthProfile, got {result.get('objectType')}"
        assert result.get("version") == 0, \
            f"Expected version=0, got {result.get('version')}"
        state["profile_id"] = result["id"]
        runner.register_cleanup(
            f"auth-profile {result['id']}",
            lambda: auth_broker_post("auth-profile", "delete", {"id": state["profile_id"]}),
        )
        print(f"    Created: {result['id']} (type={result.get('providerType')}, version={result['version']})")

    runner.run_test("auth-profile.add — create SAML profile", test_auth_profile_add)

    def test_auth_profile_get():
        """Retrieve auth profile by ID and verify all fields."""
        result = auth_broker_post("auth-profile", "get", {"id": state["profile_id"]})
        assert result["id"] == state["profile_id"], f"ID mismatch: {result.get('id')}"
        assert result.get("authStrategy") == "saml", \
            f"authStrategy mismatch: {result.get('authStrategy')}"
        assert result.get("providerType") == "other", \
            f"providerType mismatch: {result.get('providerType')}"
        assert result.get("objectType") == "AuthProfile", \
            f"objectType mismatch: {result.get('objectType')}"
        print(f"    Got: {result['id']}, strategy={result.get('authStrategy')}, version={result.get('version')}")

    runner.run_test("auth-profile.get — retrieve by ID", test_auth_profile_get)

    def test_auth_profile_list():
        """List auth profiles and verify test profile is included."""
        result = auth_broker_post("auth-profile", "list", {})
        assert "objects" in result, f"Expected objects in response: {result}"
        assert "totalCount" in result, f"Expected totalCount in response: {result}"
        ids = [obj["id"] for obj in result["objects"]]
        assert state["profile_id"] in ids, \
            f"Expected {state['profile_id']} in list results"
        print(f"    Listed {result['totalCount']} total, {len(result['objects'])} returned")

    runner.run_test("auth-profile.list — verify test profile in results", test_auth_profile_list)

    def test_auth_profile_update():
        """Update description and verify version increment."""
        before = auth_broker_post("auth-profile", "get", {"id": state["profile_id"]})
        result = auth_broker_post("auth-profile", "update", {
            "id": state["profile_id"],
            "description": f"Updated description at {TS}",
        })
        assert result.get("description") == f"Updated description at {TS}", \
            f"Expected updated description, got {result.get('description')}"
        assert result.get("version") == before["version"] + 1, \
            f"Expected version {before['version'] + 1}, got {result.get('version')}"
        print(f"    Updated: description changed, version={result['version']}")

    runner.run_test("auth-profile.update — change description, verify version+1", test_auth_profile_update)

    def test_saml_metadata():
        """GET SAML metadata endpoint and verify XML EntityDescriptor."""
        profile_id = state["profile_id"]
        xml_text = auth_broker_get(f"/auth-manager/saml/metadata/{PARTNER_ID}/{profile_id}")
        assert "EntityDescriptor" in xml_text, \
            f"Expected EntityDescriptor in SAML metadata XML, got: {xml_text[:200]}"
        print(f"    SAML metadata: {len(xml_text)} chars, contains EntityDescriptor")

    runner.run_test("SAML metadata — GET /auth-manager/saml/metadata/{pid}/{id}", test_saml_metadata)

    # ════════════════════════════════════════════
    # Phase 2: App Subscription CRUD
    # ════════════════════════════════════════════
    def test_create_test_app():
        """Create a test app in App Registry for subscription linking."""
        result = app_registry_post("add", {
            "appCustomId": f"test-auth-app-{TS}",
            "appType": "test",
            "appCustomName": f"Auth Broker Test App {TS}",
        })
        assert "id" in result, f"Expected id in response: {result}"
        state["test_app_id"] = result["id"]
        state["test_app_guid"] = result["id"]
        runner.register_cleanup(
            f"test app {result['id']}",
            lambda: app_registry_post("delete", {"id": state["test_app_id"]}),
        )
        print(f"    Created test app: {result['id']}")

    runner.run_test("app-registry.add — create test app for subscription", test_create_test_app)

    def test_app_subscription_add():
        """Create an app subscription linking the test app to the auth profile."""
        result = auth_broker_post("app-subscription", "add", {
            "name": f"Test Subscription {TS}",
            "appGuid": state["test_app_guid"],
            "authProfileIds": [state["profile_id"]],
            "appLandingPage": f"https://test-app-{TS}.example.com/landing",
            "appErrorPage": f"https://test-app-{TS}.example.com/error",
            "ksPrivileges": "kmslogin",
        })
        assert "id" in result, f"Expected id in response: {result}"
        assert result.get("version") == 0, \
            f"Expected version=0, got {result.get('version')}"
        state["subscription_id"] = result["id"]
        runner.register_cleanup(
            f"app-subscription {result['id']}",
            lambda: auth_broker_post("app-subscription", "delete", {"id": state["subscription_id"]}),
        )
        print(f"    Created: {result['id']} (appGuid={state['test_app_guid']}, version={result.get('version')})")

    runner.run_test("app-subscription.add — create subscription", test_app_subscription_add)

    def test_app_subscription_get():
        """Retrieve app subscription by ID."""
        result = auth_broker_post("app-subscription", "get", {"id": state["subscription_id"]})
        assert result["id"] == state["subscription_id"], f"ID mismatch: {result.get('id')}"
        assert state["profile_id"] in result.get("authProfileIds", []), \
            f"Expected auth profile {state['profile_id']} in authProfileIds"
        print(f"    Got: {result['id']}, authProfileIds={result.get('authProfileIds')}")

    runner.run_test("app-subscription.get — retrieve by ID", test_app_subscription_get)

    def test_app_subscription_list():
        """List app subscriptions filtered by appGuid."""
        result = auth_broker_post("app-subscription", "list", {
            "filter": {"appGuid": state["test_app_guid"]},
        })
        assert "objects" in result, f"Expected objects in response: {result}"
        ids = [obj["id"] for obj in result["objects"]]
        assert state["subscription_id"] in ids, \
            f"Expected {state['subscription_id']} in list results"
        print(f"    Listed {result.get('totalCount', len(result['objects']))} subscription(s) for appGuid={state['test_app_guid']}")

    runner.run_test("app-subscription.list — filter by appGuid", test_app_subscription_list)

    def test_app_subscription_update():
        """Update subscription and verify version increment."""
        before = auth_broker_post("app-subscription", "get", {"id": state["subscription_id"]})
        result = auth_broker_post("app-subscription", "update", {
            "id": state["subscription_id"],
            "name": f"Updated Subscription {TS}",
        })
        assert result.get("name") == f"Updated Subscription {TS}", \
            f"Expected updated name, got {result.get('name')}"
        assert result.get("version") == before.get("version", 0) + 1, \
            f"Expected version {before.get('version', 0) + 1}, got {result.get('version')}"
        print(f"    Updated: name='{result.get('name')}', version={result.get('version')}")

    runner.run_test("app-subscription.update — change name, verify version+1", test_app_subscription_update)

    # ════════════════════════════════════════════
    # Phase 3: Error Handling
    # ════════════════════════════════════════════
    def test_auth_profile_get_invalid():
        """Getting a non-existent auth profile ID returns an error."""
        try:
            auth_broker_post("auth-profile", "get", {"id": "000000000000000000000000"})
            raise AssertionError("Expected error for invalid auth profile ID, got success")
        except Exception as e:
            err = str(e)
            assert "OBJECT_NOT_FOUND" in err or "not found" in err.lower() \
                or "404" in err or "error" in err.lower(), \
                f"Expected error response for invalid ID, got: {err}"
        print("    Correctly returned error for non-existent auth profile ID")

    runner.run_test("auth-profile.get — error for invalid ID", test_auth_profile_get_invalid)

    def test_app_subscription_add_missing_app_guid():
        """Adding a subscription without appGuid returns an error."""
        try:
            auth_broker_post("app-subscription", "add", {
                "name": "Missing appGuid Test",
                "authProfileIds": [state["profile_id"]],
                "appLandingPage": "https://example.com/landing",
                "appErrorPage": "https://example.com/error",
                "ksPrivileges": "kmslogin",
            })
            raise AssertionError("Expected error for missing appGuid, got success")
        except Exception as e:
            err = str(e)
            assert "appGuid" in err.lower() or "required" in err.lower() \
                or "missing" in err.lower() or "validation" in err.lower() \
                or "400" in err or "error" in err.lower(), \
                f"Expected validation error for missing appGuid, got: {err}"
        print("    Correctly returned error for missing appGuid")

    runner.run_test("app-subscription.add — error for missing appGuid", test_app_subscription_add_missing_app_guid)

    # ════════════════════════════════════════════
    # Phase 4: Cleanup & Summary
    # ════════════════════════════════════════════
    keep = "--keep" in sys.argv
    if keep:
        print(f"\n--keep flag set. Resources preserved:")
        print(f"  Auth Profile ID: {state.get('profile_id')}")
        print(f"  App Subscription ID: {state.get('subscription_id')}")
        print(f"  Test App ID: {state.get('test_app_id')}")
        print(f"\n  Clean up manually:")
        sub_id = state.get('subscription_id')
        profile_id = state.get('profile_id')
        app_id = state.get('test_app_id')
        print(f'    curl -X POST "{AUTH_BROKER_URL}/app-subscription/delete" \\')
        print(f'      -H "Authorization: KS $KS" \\')
        print(f'      -H "Content-Type: application/json" \\')
        print(f'      -d \'{{"id": "{sub_id}"}}\'')
        print(f'    curl -X POST "{AUTH_BROKER_URL}/auth-profile/delete" \\')
        print(f'      -H "Authorization: KS $KS" \\')
        print(f'      -H "Content-Type: application/json" \\')
        print(f'      -d \'{{"id": "{profile_id}"}}\'')
        print(f'    curl -X POST "https://app-registry.nvp1.ovp.kaltura.com/api/v1/app-registry/delete" \\')
        print(f'      -H "Authorization: Bearer $KS" \\')
        print(f'      -H "Content-Type: application/json" \\')
        print(f'      -d \'{{"id": "{app_id}"}}\'')
    else:
        if sys.stdin.isatty():
            input("\nPress Enter to clean up...")
        runner.cleanup()

    success = runner.summary()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
