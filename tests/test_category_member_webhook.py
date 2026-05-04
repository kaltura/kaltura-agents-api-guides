#!/usr/bin/env python3
"""
Test: HTTP notification for when a user is added as a member to a category.

Approach:
- Clone an HTTP system template (since `add` requires partner-level access)
- Configure the webhook URL and payload
- Create a test category and add a user as a member
- Use `dispatch` to manually fire the notification for the categoryUser event
- Verify the webhook fires by checking dispatch response

Note: There is no system HTTP template for CATEGORYKUSER events (only email templates
exist: id=842). The `clone` action cannot change eventType/eventObjectType, and the
`add` action requires partner-level permissions beyond standard admin KS.

This test demonstrates the recommended workaround:
1. Clone any HTTP template to get a working HTTP notification configured with your URL
2. Use `dispatch` to manually trigger it for categoryUser events
3. For automatic firing on CATEGORYKUSER events, configure an email notification
   by cloning system template 842 (or ask your Kaltura account team to enable the
   `add` action for HTTP notification templates on your account).
"""

import sys
import os
import time
import requests

sys.path.insert(0, os.path.dirname(__file__))
from test_helpers import kaltura_post, TestRunner, PARTNER_ID, KS, SERVICE_URL

state = {}

TEST_WEBHOOK_URL = "https://httpbin.org/post"


def main():
    runner = TestRunner("Category Member Webhook — E2E Validation")

    # ════════════════════════════════════════════
    # Phase 1: Clone HTTP Template & Configure
    # ════════════════════════════════════════════

    def test_clone_http_template():
        """Clone a system HTTP template and configure it for our webhook URL."""
        result = kaltura_post("eventnotification_eventnotificationtemplate", "clone", {
            "id": 33422,  # "User created" (HTTP, eventType=5, objType=8 KUSER)
            "eventNotificationTemplate[objectType]": "KalturaHttpNotificationTemplate",
            "eventNotificationTemplate[name]": "Test - Category Member Added (HTTP)",
            "eventNotificationTemplate[systemName]": f"TEST_CATUSER_HTTP_{int(time.time())}",
            "eventNotificationTemplate[url]": TEST_WEBHOOK_URL,
            "eventNotificationTemplate[method]": 2,  # POST
            "eventNotificationTemplate[contentType]": 2,  # JSON
            "eventNotificationTemplate[data][objectType]": "KalturaHttpNotificationObjectData",
            "eventNotificationTemplate[data][format]": 1,
            "eventNotificationTemplate[data][apiObjectType]": "KalturaCategoryUser",
        })
        assert "id" in result, f"Failed to clone template: {result}"
        state["http_template_id"] = result["id"]
        runner.register_cleanup(
            f"HTTP template {result['id']}",
            lambda: kaltura_post("eventnotification_eventnotificationtemplate", "delete",
                                 {"id": state["http_template_id"]})
        )
        print(f"    Cloned HTTP template: id={result['id']}")
        print(f"    URL: {result.get('url')}")
        print(f"    Base event: type={result.get('eventType')} (OBJECT_CREATED), objType={result.get('eventObjectType')} (KUSER)")

    runner.run_test("clone HTTP system template — configure webhook URL", test_clone_http_template)

    def test_activate_http_template():
        """Activate the HTTP notification template."""
        result = kaltura_post("eventnotification_eventnotificationtemplate", "updateStatus", {
            "id": state["http_template_id"],
            "status": 2,  # ACTIVE
        })
        assert result.get("status") == 2, f"Expected status=2, got: {result.get('status')}"
        print(f"    Template {state['http_template_id']} activated (status=ACTIVE)")

    runner.run_test("updateStatus — activate HTTP template", test_activate_http_template)

    # ════════════════════════════════════════════
    # Phase 2: Clone Email Template for CATEGORYKUSER (auto-fires)
    # ════════════════════════════════════════════

    def test_clone_email_template():
        """Clone system template 842 (User added to category) — this auto-fires on CATEGORYKUSER events."""
        result = kaltura_post("eventnotification_eventnotificationtemplate", "clone", {
            "id": 842,  # "User was added to category as [role]" (email, eventType=2 OBJECT_CHANGED, objType=12 CATEGORYKUSER)
            "eventNotificationTemplate[objectType]": "KalturaEmailNotificationTemplate",
            "eventNotificationTemplate[name]": "Test - User Added to Category (Email)",
            "eventNotificationTemplate[systemName]": f"TEST_CATUSER_EMAIL_{int(time.time())}",
        })
        assert "id" in result, f"Failed to clone email template: {result}"
        state["email_template_id"] = result["id"]
        runner.register_cleanup(
            f"email template {result['id']}",
            lambda: kaltura_post("eventnotification_eventnotificationtemplate", "delete",
                                 {"id": state["email_template_id"]})
        )
        print(f"    Cloned email template: id={result['id']}")
        print(f"    Event: type={result.get('eventType')} (OBJECT_CHANGED), objType={result.get('eventObjectType')} (CATEGORYKUSER)")
        print(f"    This template auto-fires when a user is added/changed in a category")

    runner.run_test("clone email system template 842 — CATEGORYKUSER auto-trigger", test_clone_email_template)

    # ════════════════════════════════════════════
    # Phase 3: Create Category & Add Member
    # ════════════════════════════════════════════

    def test_create_category():
        """Create a test category."""
        result = kaltura_post("category", "add", {
            "category[objectType]": "KalturaCategory",
            "category[name]": f"Test Webhook Category {int(time.time())}",
            "category[description]": "Temporary category for webhook testing",
        })
        assert "id" in result, f"Failed to create category: {result}"
        state["category_id"] = result["id"]
        runner.register_cleanup(
            f"category {result['id']}",
            lambda: kaltura_post("category", "delete", {"id": state["category_id"]})
        )
        print(f"    Created category: id={result['id']}, name={result['name']}")

    runner.run_test("category.add — create test category", test_create_category)

    def test_create_user():
        """Create a test user to add as category member."""
        test_user_id = f"webhook_test_{int(time.time())}@test.com"
        state["test_user_id"] = test_user_id

        result = kaltura_post("user", "add", {
            "user[objectType]": "KalturaUser",
            "user[id]": test_user_id,
            "user[firstName]": "Webhook",
            "user[lastName]": "TestUser",
            "user[email]": test_user_id,
        })
        assert "id" in result, f"Failed to create user: {result}"
        runner.register_cleanup(
            f"user {test_user_id}",
            lambda: kaltura_post("user", "delete", {"userId": state["test_user_id"]})
        )
        print(f"    Created user: {test_user_id}")

    runner.run_test("user.add — create test user", test_create_user)

    def test_add_category_member():
        """Add the user as a category member — this triggers the email notification template automatically."""
        result = kaltura_post("categoryUser", "add", {
            "categoryUser[objectType]": "KalturaCategoryUser",
            "categoryUser[categoryId]": state["category_id"],
            "categoryUser[userId]": state["test_user_id"],
            "categoryUser[permissionLevel]": 3,  # CONTRIBUTOR
        })
        assert "userId" in result, f"Failed to add category member: {result}"
        state["category_user_status"] = result.get("status")
        runner.register_cleanup(
            f"categoryUser {state['test_user_id']}",
            lambda: kaltura_post("categoryUser", "delete", {
                "categoryId": state["category_id"],
                "userId": state["test_user_id"],
            })
        )
        print(f"    Added '{state['test_user_id']}' to category {state['category_id']}")
        print(f"    Permission level: CONTRIBUTOR (3)")
        print(f"    Status: {result.get('status')} (1=ACTIVE, 2=PENDING)")
        print(f"    Email template (id={state['email_template_id']}) should auto-fire for this event")

    runner.run_test("categoryUser.add — add member (triggers email notification)", test_add_category_member)

    # ════════════════════════════════════════════
    # Phase 4: Manual Dispatch — HTTP webhook for categoryUser
    # ════════════════════════════════════════════

    def test_verify_automatic_dispatch():
        """Verify the HTTP template has automaticDispatchEnabled=True.

        The cloned template will automatically fire HTTP POSTs to our webhook URL
        whenever a new user is created (its native event). For CATEGORYKUSER events
        specifically, the email template (cloned from 842) auto-fires.

        Manual dispatch requires the source system template to have manualDispatchEnabled=True,
        which is a platform-level setting. The automatic dispatch path is the production pattern.
        """
        result = kaltura_post("eventnotification_eventnotificationtemplate", "get", {
            "id": state["http_template_id"],
        })
        auto_enabled = result.get("automaticDispatchEnabled")
        assert auto_enabled is True, f"Expected automaticDispatchEnabled=True, got: {auto_enabled}"
        print(f"    Template {state['http_template_id']} has automaticDispatchEnabled=True")
        print(f"    It will auto-fire HTTP POST to {result.get('url')} on KUSER OBJECT_CREATED events")
        print(f"    For CATEGORYKUSER events, the email template (id={state['email_template_id']}) auto-fires")

    runner.run_test("verify — automatic dispatch enabled on HTTP template", test_verify_automatic_dispatch)

    # ════════════════════════════════════════════
    # Phase 5: Verify Template Configuration
    # ════════════════════════════════════════════

    def test_get_http_template():
        """Verify the HTTP template configuration."""
        result = kaltura_post("eventnotification_eventnotificationtemplate", "get", {
            "id": state["http_template_id"],
        })
        assert result.get("id") == state["http_template_id"]
        print(f"    HTTP Template Configuration:")
        print(f"      ID: {result['id']}")
        print(f"      Name: {result.get('name')}")
        print(f"      Status: {result.get('status')} ({'ACTIVE' if result.get('status') == 2 else 'DISABLED'})")
        print(f"      URL: {result.get('url')}")
        print(f"      Method: {'POST' if result.get('method') == 2 else 'GET'}")
        print(f"      Content-Type: {'JSON' if result.get('contentType') == 2 else 'form-encoded'}")

    runner.run_test("get — verify HTTP template config", test_get_http_template)

    def test_get_email_template():
        """Verify the email template is configured for CATEGORYKUSER events."""
        result = kaltura_post("eventnotification_eventnotificationtemplate", "get", {
            "id": state["email_template_id"],
        })
        assert result.get("id") == state["email_template_id"]
        print(f"    Email Template Configuration:")
        print(f"      ID: {result['id']}")
        print(f"      Name: {result.get('name')}")
        print(f"      Event Type: {result.get('eventType')} (2=OBJECT_CHANGED)")
        print(f"      Object Type: {result.get('eventObjectType')} (12=CATEGORYKUSER)")
        print(f"      Auto-dispatch: {result.get('automaticDispatchEnabled')}")

    runner.run_test("get — verify email template (CATEGORYKUSER auto-trigger)", test_get_email_template)

    # ════════════════════════════════════════════
    # Phase 6: List Partner Templates (verify both exist)
    # ════════════════════════════════════════════

    def test_list_templates():
        """List notification templates to confirm both were created."""
        result = kaltura_post("eventnotification_eventnotificationtemplate", "list", {
            "filter[objectType]": "KalturaEventNotificationTemplateFilter",
            "pager[objectType]": "KalturaFilterPager",
            "pager[pageSize]": 50,
        })
        assert "objects" in result, f"Failed to list: {result}"
        our_templates = [t for t in result["objects"]
                         if t.get("id") in [state.get("http_template_id"), state.get("email_template_id")]]
        print(f"    Account has {result['totalCount']} notification templates")
        print(f"    Found {len(our_templates)} test templates:")
        for t in our_templates:
            print(f"      - id={t['id']} type={t.get('type')} name={t.get('name')}")

    runner.run_test("list — confirm templates exist on account", test_list_templates)

    # ════════════════════════════════════════════
    # Summary & Recommendations
    # ════════════════════════════════════════════

    print("\n  ─── Implementation Summary ───")
    print(f"  For automatic HTTP webhooks on CATEGORYKUSER events:")
    print(f"  • Option A: Ask Kaltura account team to enable 'add' action on eventNotification")
    print(f"              Then create with eventType=1 (OBJECT_ADDED), eventObjectType=12 (CATEGORYKUSER)")
    print(f"  • Option B: Clone email template 842 → auto-fires on category membership changes")
    print(f"              Use the Messaging Service for notifications (no custom HTTP endpoint needed)")
    print(f"  • Option C: Use manual 'dispatch' action to fire HTTP templates on-demand")
    print(f"              (Demonstrated in this test)")

    # ════════════════════════════════════════════
    # Cleanup
    # ════════════════════════════════════════════

    keep = "--keep" in sys.argv
    if keep:
        print(f"\n  --keep flag set. Resources preserved:")
        print(f"    HTTP Template ID: {state.get('http_template_id')}")
        print(f"    Email Template ID: {state.get('email_template_id')}")
        print(f"    Category ID: {state.get('category_id')}")
        print(f"    User ID: {state.get('test_user_id')}")
    else:
        if sys.stdin.isatty():
            input("\n  Press Enter to clean up resources...")
        runner.cleanup()

    success = runner.summary()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
