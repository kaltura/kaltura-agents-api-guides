#!/usr/bin/env python3
"""Playwright E2E validation of the Kaltura LMS Extensions demo app.

Validates:
- Dashboard structure and brand compliance
- LTI launches to all modules (My Media, Media Gallery, Content Picker)
- Course context isolation
- Educational pages (How It Works, Grade Sync, Standalone Embed)
- SIS provisioning API (create course, enroll student)
- Kaltura brand guidelines (Lato font, Stream Blue, Brand Black)
- Non-technical language (no OAuth/HMAC jargon on user-facing pages)

Prerequisites:
    pip install playwright
    python -m playwright install chromium
    # App must be running: python app.py
"""

import json
import os
import time

import requests
from playwright.sync_api import sync_playwright

BASE_URL = os.environ.get("APP_URL", "http://localhost:5050")
PARTNER_ID = os.environ.get("KALTURA_PARTNER_ID", "")
ADMIN_SECRET = os.environ.get("KALTURA_ADMIN_SECRET", "")


def main():
    passed = 0
    failed = 0
    cleanup_ids = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 900})

        def check(name, condition):
            nonlocal passed, failed
            if condition:
                passed += 1
                print(f"  PASS  {name}")
            else:
                failed += 1
                print(f"  FAIL  {name}")

        print("\n" + "=" * 60)
        print("  Kaltura LMS Extensions — Playwright E2E Validation")
        print("=" * 60 + "\n")

        # 1. Dashboard
        page.goto(BASE_URL)
        page.wait_for_load_state("networkidle")
        check("Dashboard title", "Kaltura LMS Extensions" in page.title())
        check("Dashboard has module cards", page.locator(".module-card").count() >= 3)
        check("Dashboard has callout", page.locator(".callout").count() >= 1)

        # 2. Navigation
        check("Navigation links", page.locator(".nav a").count() >= 5)

        # 3. My Media LTI launch
        page.get_by_role("button", name="Launch My Media").click()
        page.wait_for_load_state("networkidle")
        time.sleep(4)
        check("My Media toolbar", page.locator(".toolbar h2").text_content() == "My Media")
        check("My Media role shown", "Instructor" in page.locator(".meta-bar").text_content())

        # 4. Media Gallery
        page.goto(BASE_URL)
        page.wait_for_load_state("networkidle")
        page.locator('select[name="context_id"]').first.select_option("DEMO_CS_201")
        page.get_by_role("button", name="Launch Media Gallery").click()
        page.wait_for_load_state("networkidle")
        time.sleep(3)
        check("Media Gallery name", "Media Gallery" in page.locator(".toolbar h2").text_content())
        check("Course context shown", "CS 201" in page.locator(".meta-bar").text_content())

        # 5. Content Picker
        page.goto(BASE_URL)
        page.wait_for_load_state("networkidle")
        page.get_by_role("button", name="Open Content Picker").click()
        page.wait_for_load_state("networkidle")
        time.sleep(3)
        check("Content Picker name", "Content Picker" in page.locator(".toolbar h2").text_content())

        # 6. How It Works
        page.goto(f"{BASE_URL}/how-it-works")
        page.wait_for_load_state("networkidle")
        content = page.content()
        check("What is LTI section", "What is LTI" in content)
        check("Connection Flow section", "Connection Flow" in content)
        check("Security section", "Security" in content)

        # 7. Grade Sync
        page.goto(f"{BASE_URL}/grade-passback")
        page.wait_for_load_state("networkidle")
        content = page.content()
        check("Grade Sync title", "Grade Sync" in content)
        check("LTI 1.1 outcomes", "Basic Outcomes" in content)
        check("LTI 1.3 AGS", "Assignment and Grade Services" in content)

        # 8. Standalone Embed
        page.goto(f"{BASE_URL}/ks-sso")
        page.wait_for_load_state("networkidle")
        check("Standalone page", "Standalone Embed" in page.content())
        check("Has iframe demo", page.locator("iframe").count() >= 1)

        # 9. Provisioning
        page.goto(f"{BASE_URL}/provisioning")
        page.wait_for_load_state("networkidle")
        check("3-step wizard", page.locator(".step-number").count() == 3)

        # 10. SIS API
        course_name = f"PW_E2E_{int(time.time())}"
        page.fill("#course-name", course_name)
        page.fill("#course-desc", "Automated test")
        page.click('button:has-text("Create Course")')
        time.sleep(5)
        result = json.loads(page.locator("#course-result").text_content())
        check("SIS create course", "id" in result)
        if "id" in result:
            cleanup_ids.append(result["id"])

        page.fill("#enroll-user", "pw_student")
        page.click('button:has-text("Enroll Student")')
        time.sleep(4)
        enroll = json.loads(page.locator("#enroll-result").text_content())
        check("SIS enroll student", enroll.get("userId") == "pw_student")

        # 11. Brand compliance
        page.goto(BASE_URL)
        page.wait_for_load_state("networkidle")
        source = page.content()
        check("Lato font loaded", "Lato" in source)
        check("Stream Blue #006EFA", "006EFA" in source.upper())
        check("Brand Black #282828", "282828" in source)

        # 12. Non-technical language
        body = page.locator("body").text_content().lower()
        check("No OAuth jargon", "oauth" not in body)
        check("No HMAC jargon", "hmac" not in body)

        browser.close()

    # Cleanup
    if cleanup_ids and ADMIN_SECRET:
        ks_resp = requests.post(
            "https://www.kaltura.com/api_v3/service/session/action/start",
            data={
                "format": 1, "partnerId": PARTNER_ID,
                "secret": ADMIN_SECRET, "type": 2,
                "userId": "cleanup", "expiry": 300,
                "privileges": "disableentitlement",
            },
        )
        ks = ks_resp.json()
        for cat_id in cleanup_ids:
            requests.post(
                "https://www.kaltura.com/api_v3/service/category/action/delete",
                data={"format": 1, "ks": ks, "id": cat_id},
            )
            print(f"  Cleaned up category {cat_id}")

    print("\n" + "=" * 60)
    print(f"  RESULTS: {passed} passed, {failed} failed")
    print("=" * 60 + "\n")
    return failed == 0


if __name__ == "__main__":
    import sys
    sys.exit(0 if main() else 1)
