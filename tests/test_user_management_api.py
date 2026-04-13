#!/usr/bin/env python3
"""
End-to-end validation of the User Management API against the live API.

Covers: user CRUD (add/get/list/update/delete), login enable/disable,
userRole CRUD (add/get/list/update/clone/delete), groupUser (add/list/delete),
error handling (duplicate user, invalid user ID, missing filter).
"""

import sys
import os
import time

sys.path.insert(0, os.path.dirname(__file__))
from test_helpers import kaltura_post, TestRunner, PARTNER_ID, KS, SERVICE_URL

TS = int(time.time())
state = {}


def main():
    runner = TestRunner("User Management API — E2E Validation")

    # ════════════════════════════════════════════
    # Phase 1: User CRUD
    # ════════════════════════════════════════════

    def test_user_add():
        """Create a test user and verify defaults."""
        result = kaltura_post("user", "add", {
            "user[objectType]": "KalturaUser",
            "user[id]": f"api_test_user_{TS}",
            "user[firstName]": "APITest",
            "user[lastName]": "User",
            "user[email]": f"api_test_{TS}@example.com",
            "user[type]": 0,
            "user[tags]": "api-test,validation",
        })
        assert result.get("objectType") == "KalturaUser", (
            f"Expected KalturaUser, got {result.get('objectType')}"
        )
        assert result["id"] == f"api_test_user_{TS}"
        assert result["status"] == 1, f"Expected ACTIVE status=1, got {result['status']}"
        assert result["firstName"] == "APITest"
        assert result["lastName"] == "User"
        assert result.get("loginEnabled") is False, "Expected loginEnabled=false for new user"
        state["user_id"] = result["id"]
        runner.register_cleanup(f"user {result['id']}",
                                lambda: _delete_user(result["id"]))
        print(f"    Created: {result['id']}, status={result['status']}")

    runner.run_test("user.add — create test user", test_user_add)

    def test_user_add_duplicate():
        """Adding a user with an existing ID returns USER_ALREADY_EXISTS."""
        try:
            kaltura_post("user", "add", {
                "user[objectType]": "KalturaUser",
                "user[id]": state["user_id"],
            })
            raise AssertionError("Expected error for duplicate user ID")
        except Exception as e:
            err = str(e)
            assert "DUPLICATE" in err.upper() or "ALREADY_EXISTS" in err.upper() or "DUPLICATE_USER" in err.upper(), (
                f"Expected duplicate error, got: {err}"
            )
        print(f"    Correctly rejected duplicate user ID '{state['user_id']}'")

    runner.run_test("user.add — duplicate user ID rejected", test_user_add_duplicate)

    def test_user_get():
        """Retrieve user by ID and verify fields."""
        result = kaltura_post("user", "get", {
            "userId": state["user_id"],
        })
        assert result["id"] == state["user_id"]
        assert result["firstName"] == "APITest"
        assert result["lastName"] == "User"
        assert result.get("objectType") == "KalturaUser"
        print(f"    Got: {result['id']}, fullName={result.get('fullName')}")

    runner.run_test("user.get — retrieve by ID", test_user_get)

    def test_user_get_invalid():
        """Getting a non-existent user returns INVALID_USER_ID."""
        try:
            kaltura_post("user", "get", {
                "userId": f"nonexistent_user_{TS}_xyz",
            })
            raise AssertionError("Expected INVALID_USER_ID")
        except Exception as e:
            assert "INVALID_USER_ID" in str(e), f"Expected INVALID_USER_ID, got: {e}"
        print("    Correctly returned INVALID_USER_ID")

    runner.run_test("user.get — INVALID_USER_ID for non-existent user", test_user_get_invalid)

    def test_user_list_filter():
        """List users with status filter and verify our user is included."""
        result = kaltura_post("user", "list", {
            "filter[objectType]": "KalturaUserFilter",
            "filter[idIn]": state["user_id"],
            "filter[statusEqual]": 1,
        })
        assert result.get("totalCount", 0) >= 1, (
            f"Expected at least 1 user, got {result.get('totalCount')}"
        )
        ids = [u["id"] for u in result.get("objects", [])]
        assert state["user_id"] in ids, f"Expected {state['user_id']} in results"
        print(f"    Listed {result['totalCount']} user(s) matching filter")

    runner.run_test("user.list — filter by ID and status", test_user_list_filter)

    def test_user_list_pagination():
        """List with pageSize=1 returns 1 object but correct totalCount."""
        result = kaltura_post("user", "list", {
            "filter[objectType]": "KalturaUserFilter",
            "filter[statusEqual]": 1,
            "pager[pageSize]": 1,
            "pager[pageIndex]": 1,
        })
        assert len(result.get("objects", [])) == 1, (
            f"Expected 1 object with pageSize=1, got {len(result.get('objects', []))}"
        )
        assert result["totalCount"] > 1, f"Expected totalCount > 1, got {result['totalCount']}"
        print(f"    Pagination: 1 returned, {result['totalCount']} total")

    runner.run_test("user.list — pagination pageSize=1", test_user_list_pagination)

    def test_user_update():
        """Update user fields and verify changes."""
        result = kaltura_post("user", "update", {
            "userId": state["user_id"],
            "user[objectType]": "KalturaUser",
            "user[firstName]": "Updated",
            "user[title]": "Test Engineer",
            "user[company]": "Test Corp",
        })
        assert result["firstName"] == "Updated", (
            f"Expected firstName=Updated, got {result.get('firstName')}"
        )
        assert result.get("title") == "Test Engineer"
        assert result.get("company") == "Test Corp"
        # lastName should be unchanged
        assert result["lastName"] == "User", (
            f"lastName changed unexpectedly: {result.get('lastName')}"
        )
        print(f"    Updated: firstName={result['firstName']}, title={result.get('title')}")

    runner.run_test("user.update — change fields, verify unchanged preserved", test_user_update)

    # ════════════════════════════════════════════
    # Phase 2: Login Enable / Disable
    # ════════════════════════════════════════════

    def test_enable_login():
        """Enable login for the test user."""
        result = kaltura_post("user", "enableLogin", {
            "userId": state["user_id"],
            "loginId": f"api_test_{TS}@example.com",
            "password": "Kaltura1!",
        })
        assert result.get("objectType") == "KalturaUser"
        assert result.get("loginEnabled") is True, (
            f"Expected loginEnabled=true, got {result.get('loginEnabled')}"
        )
        print(f"    Login enabled for {result['id']}")

    runner.run_test("user.enableLogin — grant login credentials", test_enable_login)

    def test_login_by_login_id():
        """Login with the enabled credentials to get a user session."""
        import requests as _req
        resp = _req.post(
            f"{kaltura_post.__module__ and SERVICE_URL}/service/user/action/loginByLoginId",
            data={
                "loginId": f"api_test_{TS}@example.com",
                "password": "Kaltura1!",
                "partnerId": PARTNER_ID,
                "format": 1,
            },
            timeout=30,
        )
        resp.raise_for_status()
        result = resp.json()
        if isinstance(result, str):
            # Success — returns a KS string
            assert len(result) > 20, f"Expected KS string, got: {result[:50]}"
            state["user_ks"] = result
            print(f"    Login successful, KS: {result[:30]}...")
        elif isinstance(result, dict) and result.get("objectType") == "KalturaAPIException":
            raise Exception(f"Login failed: {result.get('message')}")
        else:
            print(f"    Login response: {str(result)[:100]}")

    runner.run_test("user.loginByLoginId — authenticate with credentials", test_login_by_login_id)

    def test_enable_login_already_enabled():
        """Enabling login again returns USER_LOGIN_ALREADY_ENABLED."""
        try:
            kaltura_post("user", "enableLogin", {
                "userId": state["user_id"],
                "loginId": f"api_test_{TS}@example.com",
                "password": "Kaltura1!",
            })
            raise AssertionError("Expected error for already-enabled login")
        except Exception as e:
            err = str(e)
            assert "LOGIN_ALREADY_ENABLED" in err or "ALREADY_ENABLED" in err or "LOGIN_ID_ALREADY_USED" in err, (
                f"Expected login already enabled error, got: {err}"
            )
        print("    Correctly rejected duplicate enableLogin")

    runner.run_test("user.enableLogin — already enabled rejected", test_enable_login_already_enabled)

    def test_disable_login():
        """Disable login for the test user."""
        result = kaltura_post("user", "disableLogin", {
            "userId": state["user_id"],
        })
        assert result.get("objectType") == "KalturaUser"
        assert result.get("loginEnabled") is False, (
            f"Expected loginEnabled=false, got {result.get('loginEnabled')}"
        )
        print(f"    Login disabled for {result['id']}")

    runner.run_test("user.disableLogin — revoke login credentials", test_disable_login)

    # ════════════════════════════════════════════
    # Phase 3: User Role CRUD
    # ════════════════════════════════════════════

    def test_role_add():
        """Create a custom user role."""
        result = kaltura_post("userRole", "add", {
            "userRole[objectType]": "KalturaUserRole",
            "userRole[name]": f"API_Test_Role_{TS}",
            "userRole[description]": "Test role for API doc validation. Safe to delete.",
            "userRole[permissionNames]": "BASE_USER_SESSION_PERMISSION,PLAYBACK_BASE_PERMISSION",
            "userRole[tags]": "api-test",
        })
        assert result.get("objectType") == "KalturaUserRole"
        assert result["name"] == f"API_Test_Role_{TS}"
        assert result["status"] == 1, f"Expected ACTIVE status=1, got {result['status']}"
        assert "BASE_USER_SESSION_PERMISSION" in result["permissionNames"]
        state["role_id"] = result["id"]
        runner.register_cleanup(f"role {result['id']}",
                                lambda: _delete_role(state["role_id"]))
        print(f"    Created role: {result['id']}, name={result['name']}")

    runner.run_test("userRole.add — create custom role", test_role_add)

    def test_role_get():
        """Retrieve role by ID."""
        result = kaltura_post("userRole", "get", {
            "userRoleId": state["role_id"],
        })
        assert result["id"] == state["role_id"]
        assert result["name"] == f"API_Test_Role_{TS}"
        assert result.get("objectType") == "KalturaUserRole"
        print(f"    Got role: {result['id']}, permissions={result.get('permissionNames', '')[:60]}...")

    runner.run_test("userRole.get — retrieve by ID", test_role_get)

    def test_role_list():
        """List roles and verify our custom role is included."""
        result = kaltura_post("userRole", "list", {
            "filter[objectType]": "KalturaUserRoleFilter",
            "filter[statusEqual]": 1,
            "filter[tagsMultiLikeOr]": "api-test",
        })
        assert result.get("totalCount", 0) >= 1, (
            f"Expected at least 1 role, got {result.get('totalCount')}"
        )
        ids = [r["id"] for r in result.get("objects", [])]
        assert state["role_id"] in ids, f"Expected role {state['role_id']} in results"
        print(f"    Listed {result['totalCount']} role(s) with tag 'api-test'")

    runner.run_test("userRole.list — filter by tags", test_role_list)

    def test_role_update():
        """Update role permissions."""
        result = kaltura_post("userRole", "update", {
            "userRoleId": state["role_id"],
            "userRole[objectType]": "KalturaUserRole",
            "userRole[description]": "Updated test role",
            "userRole[permissionNames]": "BASE_USER_SESSION_PERMISSION,PLAYBACK_BASE_PERMISSION,CONTENT_MANAGE_BASE",
        })
        assert "CONTENT_MANAGE_BASE" in result["permissionNames"], (
            f"Expected CONTENT_MANAGE_BASE in permissions"
        )
        assert result["description"] == "Updated test role"
        print(f"    Updated role: permissions now include CONTENT_MANAGE_BASE")

    runner.run_test("userRole.update — add permissions", test_role_update)

    def test_role_clone():
        """Clone a role and verify the copy."""
        result = kaltura_post("userRole", "clone", {
            "userRoleId": state["role_id"],
        })
        assert result.get("objectType") == "KalturaUserRole"
        assert result["id"] != state["role_id"], "Cloned role should have a new ID"
        assert result["permissionNames"] == kaltura_post("userRole", "get", {
            "userRoleId": state["role_id"]
        })["permissionNames"], "Cloned role should have same permissions"
        state["cloned_role_id"] = result["id"]
        runner.register_cleanup(f"cloned role {result['id']}",
                                lambda: _delete_role(state["cloned_role_id"]))
        print(f"    Cloned: {state['role_id']} → {result['id']}")

    runner.run_test("userRole.clone — copy a role", test_role_clone)

    def test_assign_role_to_user():
        """Assign the custom role to the test user."""
        result = kaltura_post("user", "update", {
            "userId": state["user_id"],
            "user[objectType]": "KalturaUser",
            "user[roleIds]": str(state["role_id"]),
        })
        assert str(state["role_id"]) in result.get("roleIds", ""), (
            f"Expected role {state['role_id']} in roleIds, got {result.get('roleIds')}"
        )
        print(f"    Assigned role {state['role_id']} to user {state['user_id']}")

    runner.run_test("user.update — assign role to user", test_assign_role_to_user)

    # ════════════════════════════════════════════
    # Phase 4: Groups (groupUser)
    # ════════════════════════════════════════════

    def test_create_group():
        """Create a group via the group_group service."""
        result = kaltura_post("group_group", "add", {
            "group[objectType]": "KalturaGroup",
            "group[id]": f"api_test_group_{TS}",
            "group[screenName]": f"Test Group {TS}",
            "group[tags]": "api-test,group",
        })
        assert result.get("objectType") == "KalturaGroup", (
            f"Expected KalturaGroup, got {result.get('objectType')}"
        )
        assert result["status"] == 1
        state["group_id"] = result["id"]
        runner.register_cleanup(f"group {result['id']}",
                                lambda: _delete_group(state["group_id"]))
        print(f"    Created group: {result['id']}, objectType={result['objectType']}")

    runner.run_test("group.add — create group (KalturaGroup)", test_create_group)

    def test_group_user_add():
        """Add the test user to the group."""
        result = kaltura_post("groupUser", "add", {
            "groupUser[objectType]": "KalturaGroupUser",
            "groupUser[groupId]": state["group_id"],
            "groupUser[userId]": state["user_id"],
        })
        assert result.get("objectType") == "KalturaGroupUser"
        assert result["userId"] == state["user_id"]
        assert result["groupId"] == state["group_id"]
        print(f"    Added {state['user_id']} to group {state['group_id']}")

    runner.run_test("groupUser.add — add user to group", test_group_user_add)

    def test_group_user_list():
        """List group members."""
        result = kaltura_post("groupUser", "list", {
            "filter[objectType]": "KalturaGroupUserFilter",
            "filter[groupIdEqual]": state["group_id"],
        })
        assert result.get("totalCount", 0) >= 1, (
            f"Expected at least 1 member, got {result.get('totalCount')}"
        )
        user_ids = [gu["userId"] for gu in result.get("objects", [])]
        assert state["user_id"] in user_ids, (
            f"Expected {state['user_id']} in group members"
        )
        print(f"    Group has {result['totalCount']} member(s)")

    runner.run_test("groupUser.list — list group members", test_group_user_list)

    def test_group_user_list_by_user():
        """List groups a user belongs to."""
        result = kaltura_post("groupUser", "list", {
            "filter[objectType]": "KalturaGroupUserFilter",
            "filter[userIdEqual]": state["user_id"],
        })
        assert result.get("totalCount", 0) >= 1, (
            f"Expected at least 1 group, got {result.get('totalCount')}"
        )
        group_ids = [gu["groupId"] for gu in result.get("objects", [])]
        assert state["group_id"] in group_ids, (
            f"Expected {state['group_id']} in user's groups"
        )
        print(f"    User belongs to {result['totalCount']} group(s)")

    runner.run_test("groupUser.list — list user's groups", test_group_user_list_by_user)

    def test_group_user_list_missing_filter():
        """groupUser.list without required filter returns error."""
        try:
            kaltura_post("groupUser", "list", {
                "filter[objectType]": "KalturaGroupUserFilter",
            })
            raise AssertionError("Expected validation error for missing filter")
        except Exception as e:
            assert "PROPERTY_VALIDATION_CANNOT_BE_NULL" in str(e), (
                f"Expected PROPERTY_VALIDATION_CANNOT_BE_NULL, got: {e}"
            )
        print("    Correctly requires groupIdEqual/userIdEqual filter")

    runner.run_test("groupUser.list — missing filter returns validation error", test_group_user_list_missing_filter)

    def test_group_user_delete():
        """Remove user from group."""
        kaltura_post("groupUser", "delete", {
            "userId": state["user_id"],
            "groupId": state["group_id"],
        })
        # Verify removal
        result = kaltura_post("groupUser", "list", {
            "filter[objectType]": "KalturaGroupUserFilter",
            "filter[groupIdEqual]": state["group_id"],
        })
        user_ids = [gu["userId"] for gu in result.get("objects", [])]
        assert state["user_id"] not in user_ids, (
            f"User {state['user_id']} still in group after delete"
        )
        print(f"    Removed {state['user_id']} from group, verified empty")

    runner.run_test("groupUser.delete — remove user from group", test_group_user_delete)

    # ════════════════════════════════════════════
    # Phase 5: User Deletion
    # ════════════════════════════════════════════

    def test_user_delete():
        """Delete the test user and verify soft-delete status."""
        result = kaltura_post("user", "delete", {
            "userId": state["user_id"],
        })
        assert result["status"] == 2, f"Expected DELETED status=2, got {result['status']}"
        # Remove from cleanup since we just deleted it
        runner._cleanup_actions = [
            (label, fn) for label, fn in runner._cleanup_actions
            if f"user {state['user_id']}" not in label
        ]
        print(f"    Deleted user: {result['id']}, status={result['status']}")

    runner.run_test("user.delete — soft-delete (status=2)", test_user_delete)

    def test_role_delete():
        """Delete the custom role and verify status."""
        result = kaltura_post("userRole", "delete", {
            "userRoleId": state["role_id"],
        })
        assert result["status"] == 3, f"Expected DELETED status=3, got {result['status']}"
        runner._cleanup_actions = [
            (label, fn) for label, fn in runner._cleanup_actions
            if f"role {state['role_id']}" not in label
        ]
        print(f"    Deleted role: {result['id']}, status={result['status']}")

    runner.run_test("userRole.delete — soft-delete (status=3)", test_role_delete)

    # ════════════════════════════════════════════
    # Cleanup & Summary
    # ════════════════════════════════════════════
    keep = "--keep" in sys.argv
    if keep:
        print(f"\n--keep flag set. Resources preserved:")
        print(f"  User ID: {state.get('user_id')}")
        print(f"  Group ID: {state.get('group_id')}")
        print(f"  Role ID: {state.get('role_id')}")
        print(f"  Cloned Role ID: {state.get('cloned_role_id')}")
    else:
        if sys.stdin.isatty():
            input("\nPress Enter to clean up...")
        runner.cleanup()

    success = runner.summary()
    sys.exit(0 if success else 1)


def _delete_user(user_id):
    try:
        kaltura_post("user", "delete", {"userId": user_id})
    except Exception:
        pass


def _delete_group(group_id):
    try:
        kaltura_post("group_group", "delete", {"groupId": group_id})
    except Exception:
        pass


def _delete_role(role_id):
    try:
        kaltura_post("userRole", "delete", {"userRoleId": role_id})
    except Exception:
        pass


if __name__ == "__main__":
    print(f"\n{'='*60}")
    print("  KALTURA USER MANAGEMENT — End-to-End Validation")
    print(f"{'='*60}\n")
    main()
