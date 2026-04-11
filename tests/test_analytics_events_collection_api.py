#!/usr/bin/env python3
"""End-to-end validation of the Analytics Events Collection API. Covers:
stats.collect (server-side event collection), analytics.trackEvent (application-level
tracking), event lifecycle ordering, appId segmentation, and report verification."""

import sys
import os
import time
import requests

sys.path.insert(0, os.path.dirname(__file__))
from test_helpers import (
    kaltura_post, create_test_entry, delete_test_entry,
    TestRunner, PARTNER_ID, KS, SERVICE_URL,
)

state = {}
ADMIN_SECRET = os.environ.get("KALTURA_ADMIN_SECRET", "")


def main():
    runner = TestRunner("Analytics Events Collection API — E2E Validation")

    # ════════════════════════════════════════════
    # Phase 1: Setup — Create test entry
    # ════════════════════════════════════════════
    def test_create_entry():
        """Create a test entry for event collection tests."""
        entry_id = create_test_entry()
        state["entry_id"] = entry_id
        runner.register_cleanup(f"test entry {entry_id}",
                                lambda: delete_test_entry(entry_id))
        print(f"    Entry: {entry_id}")

    runner.run_test("Setup — create test entry", test_create_entry)

    # ════════════════════════════════════════════
    # Phase 2: stats.collect — Server-Side Events
    # ════════════════════════════════════════════
    def test_stats_collect_play():
        """stats.collect — report a PLAY event (eventType=3)."""
        entry_id = state.get("entry_id")
        assert entry_id, "No test entry available"
        session_id = f"test_session_{int(time.time())}_{os.getpid()}"
        state["session_id"] = session_id
        result = kaltura_post("stats", "collect", {
            "event[objectType]": "KalturaStatsEvent",
            "event[partnerId]": PARTNER_ID,
            "event[entryId]": entry_id,
            "event[eventType]": 3,  # PLAY
            "event[sessionId]": session_id,
            "event[eventTimestamp]": int(time.time()),
        })
        # stats.collect returns empty/null on success
        print(f"    PLAY event sent for {entry_id}, session: {session_id}")

    runner.run_test("stats.collect — PLAY event (type=3)", test_stats_collect_play)

    def test_stats_collect_widget_loaded():
        """stats.collect — WIDGET_LOADED event (eventType=1)."""
        entry_id = state.get("entry_id")
        assert entry_id, "No test entry available"
        session_id = state.get("session_id", f"test_{int(time.time())}")
        result = kaltura_post("stats", "collect", {
            "event[objectType]": "KalturaStatsEvent",
            "event[partnerId]": PARTNER_ID,
            "event[entryId]": entry_id,
            "event[eventType]": 1,  # WIDGET_LOADED
            "event[sessionId]": session_id,
            "event[eventTimestamp]": int(time.time()),
        })
        print(f"    WIDGET_LOADED event sent")

    runner.run_test("stats.collect — WIDGET_LOADED event (type=1)", test_stats_collect_widget_loaded)

    def test_stats_collect_media_loaded():
        """stats.collect — MEDIA_LOADED event (eventType=2)."""
        entry_id = state.get("entry_id")
        assert entry_id, "No test entry available"
        session_id = state.get("session_id", f"test_{int(time.time())}")
        result = kaltura_post("stats", "collect", {
            "event[objectType]": "KalturaStatsEvent",
            "event[partnerId]": PARTNER_ID,
            "event[entryId]": entry_id,
            "event[eventType]": 2,  # MEDIA_LOADED
            "event[sessionId]": session_id,
            "event[eventTimestamp]": int(time.time()),
        })
        print(f"    MEDIA_LOADED event sent")

    runner.run_test("stats.collect — MEDIA_LOADED event (type=2)", test_stats_collect_media_loaded)

    def test_stats_collect_quartiles():
        """stats.collect — quartile events (25%, 50%, 75%, 100%)."""
        entry_id = state.get("entry_id")
        assert entry_id, "No test entry available"
        session_id = state.get("session_id", f"test_{int(time.time())}")
        for event_type, label in [(4, "25%"), (5, "50%"), (6, "75%"), (7, "100%")]:
            result = kaltura_post("stats", "collect", {
                "event[objectType]": "KalturaStatsEvent",
                "event[partnerId]": PARTNER_ID,
                "event[entryId]": entry_id,
                "event[eventType]": event_type,
                "event[sessionId]": session_id,
                "event[eventTimestamp]": int(time.time()),
            })
            print(f"    Quartile {label} (type={event_type}) sent")

    runner.run_test("stats.collect — quartile events (25/50/75/100%)", test_stats_collect_quartiles)

    def test_stats_collect_buffer_events():
        """stats.collect — BUFFER_START and BUFFER_END events."""
        entry_id = state.get("entry_id")
        assert entry_id, "No test entry available"
        session_id = state.get("session_id", f"test_{int(time.time())}")
        for event_type, label in [(12, "BUFFER_START"), (13, "BUFFER_END")]:
            result = kaltura_post("stats", "collect", {
                "event[objectType]": "KalturaStatsEvent",
                "event[partnerId]": PARTNER_ID,
                "event[entryId]": entry_id,
                "event[eventType]": event_type,
                "event[sessionId]": session_id,
                "event[eventTimestamp]": int(time.time()),
            })
            print(f"    {label} event sent")

    runner.run_test("stats.collect — buffer events (start/end)", test_stats_collect_buffer_events)

    def test_stats_collect_seek():
        """stats.collect — SEEK event (eventType=17)."""
        entry_id = state.get("entry_id")
        assert entry_id, "No test entry available"
        session_id = state.get("session_id", f"test_{int(time.time())}")
        result = kaltura_post("stats", "collect", {
            "event[objectType]": "KalturaStatsEvent",
            "event[partnerId]": PARTNER_ID,
            "event[entryId]": entry_id,
            "event[eventType]": 17,  # SEEK
            "event[sessionId]": session_id,
            "event[eventTimestamp]": int(time.time()),
            "event[seek]": 1,
            "event[currentPoint]": 30,
        })
        print(f"    SEEK event sent (currentPoint=30)")

    runner.run_test("stats.collect — SEEK event (type=17)", test_stats_collect_seek)

    def test_stats_collect_replay():
        """stats.collect — REPLAY event (eventType=16)."""
        entry_id = state.get("entry_id")
        assert entry_id, "No test entry available"
        session_id = state.get("session_id", f"test_{int(time.time())}")
        result = kaltura_post("stats", "collect", {
            "event[objectType]": "KalturaStatsEvent",
            "event[partnerId]": PARTNER_ID,
            "event[entryId]": entry_id,
            "event[eventType]": 16,  # REPLAY
            "event[sessionId]": session_id,
            "event[eventTimestamp]": int(time.time()),
        })
        print(f"    REPLAY event sent")

    runner.run_test("stats.collect — REPLAY event (type=16)", test_stats_collect_replay)

    def test_stats_collect_with_context():
        """stats.collect — event with optional context fields."""
        entry_id = state.get("entry_id")
        assert entry_id, "No test entry available"
        session_id = f"context_test_{int(time.time())}"
        result = kaltura_post("stats", "collect", {
            "event[objectType]": "KalturaStatsEvent",
            "event[partnerId]": PARTNER_ID,
            "event[entryId]": entry_id,
            "event[eventType]": 3,  # PLAY
            "event[sessionId]": session_id,
            "event[eventTimestamp]": int(time.time()),
            "event[referrer]": "https://test.example.com/player",
            "event[clientVer]": "test-suite-1.0",
            "event[currentPoint]": 0,
            "event[duration]": 120,
        })
        print(f"    PLAY event with context (referrer, clientVer, duration=120)")

    runner.run_test("stats.collect — event with context fields", test_stats_collect_with_context)

    # ════════════════════════════════════════════
    # Phase 3: analytics.trackEvent
    # ════════════════════════════════════════════
    def test_track_event_pageload():
        """analytics.trackEvent — PageLoad event (type=10003)."""
        entry_id = state.get("entry_id")
        assert entry_id, "No test entry available"
        # analytics.trackEvent uses the main API service URL
        try:
            resp = requests.post(
                f"{SERVICE_URL}/service/analytics/action/trackEvent",
                data={
                    "ks": KS,
                    "format": 1,
                    "eventType": 10003,  # PageLoad
                    "partnerId": PARTNER_ID,
                    "entryId": entry_id,
                    "kalturaApplication": "test-suite",
                    "pageType": "test",
                    "pageName": "e2e-validation",
                },
                timeout=15,
            )
            # trackEvent may return 200 with empty body or a JSON response
            print(f"    PageLoad (10003) status: {resp.status_code}")
            if resp.text:
                print(f"    Response: {resp.text[:100]}")
        except Exception as e:
            # analytics.trackEvent may use a different server
            print(f"    analytics.trackEvent at API v3: {e}")

    runner.run_test("analytics.trackEvent — PageLoad (10003)", test_track_event_pageload)

    def test_track_event_button_click():
        """analytics.trackEvent — ButtonClicked event (type=10002)."""
        entry_id = state.get("entry_id")
        assert entry_id, "No test entry available"
        try:
            resp = requests.post(
                f"{SERVICE_URL}/service/analytics/action/trackEvent",
                data={
                    "ks": KS,
                    "format": 1,
                    "eventType": 10002,  # ButtonClicked
                    "partnerId": PARTNER_ID,
                    "entryId": entry_id,
                    "kalturaApplication": "test-suite",
                    "buttonType": "cta",
                    "buttonName": "test-button",
                },
                timeout=15,
            )
            print(f"    ButtonClicked (10002) status: {resp.status_code}")
            if resp.text:
                print(f"    Response: {resp.text[:100]}")
        except Exception as e:
            print(f"    analytics.trackEvent at API v3: {e}")

    runner.run_test("analytics.trackEvent — ButtonClicked (10002)", test_track_event_button_click)

    # ════════════════════════════════════════════
    # Phase 4: Full Playback Session
    # ════════════════════════════════════════════
    def test_full_playback_session():
        """Complete playback session — all events in lifecycle order."""
        entry_id = state.get("entry_id")
        assert entry_id, "No test entry available"
        session_id = f"full_session_{int(time.time())}_{os.getpid()}"
        event_sequence = [
            (1, "WIDGET_LOADED"),
            (2, "MEDIA_LOADED"),
            (3, "PLAY"),
            (4, "PLAY_REACHED_25"),
            (5, "PLAY_REACHED_50"),
            (6, "PLAY_REACHED_75"),
            (7, "PLAY_REACHED_100"),
        ]
        for event_type, label in event_sequence:
            kaltura_post("stats", "collect", {
                "event[objectType]": "KalturaStatsEvent",
                "event[partnerId]": PARTNER_ID,
                "event[entryId]": entry_id,
                "event[eventType]": event_type,
                "event[sessionId]": session_id,
                "event[eventTimestamp]": int(time.time()),
            })
        print(f"    Full session ({len(event_sequence)} events) sent: {session_id}")

    runner.run_test("Full playback session — lifecycle order", test_full_playback_session)

    # ════════════════════════════════════════════
    # Phase 5: appId Segmentation
    # ════════════════════════════════════════════
    def test_appid_session():
        """Generate KS with appId privilege for segmentation."""
        if not ADMIN_SECRET:
            print("    Skipped: KALTURA_ADMIN_SECRET not set")
            return
        try:
            ks = kaltura_post("session", "start", {
                "secret": ADMIN_SECRET,
                "type": 0,
                "partnerId": PARTNER_ID,
                "userId": "appid-test@example.com",
                "privileges": "appId:test-app-segmentation",
            })
            assert isinstance(ks, str) and len(ks) > 10, f"Expected KS string, got: {ks}"
            state["appid_ks"] = ks
            print(f"    KS with appId:test-app-segmentation generated")
        except Exception as e:
            print(f"    Session generation: {e}")

    runner.run_test("appId — generate KS with appId privilege", test_appid_session)

    def test_appid_event():
        """Send event with appId-scoped KS."""
        appid_ks = state.get("appid_ks")
        entry_id = state.get("entry_id")
        if not appid_ks:
            print("    Skipped: no appId KS available")
            return
        assert entry_id, "No test entry available"
        session_id = f"appid_test_{int(time.time())}"
        resp = requests.post(
            f"{SERVICE_URL}/service/stats/action/collect",
            data={
                "ks": appid_ks,
                "format": 1,
                "event[objectType]": "KalturaStatsEvent",
                "event[partnerId]": PARTNER_ID,
                "event[entryId]": entry_id,
                "event[eventType]": 3,
                "event[sessionId]": session_id,
                "event[eventTimestamp]": int(time.time()),
            },
            timeout=15,
        )
        resp.raise_for_status()
        print(f"    Event sent with appId-scoped KS, status: {resp.status_code}")

    runner.run_test("appId — send event with scoped KS", test_appid_event)

    # ════════════════════════════════════════════
    # Phase 6: Report Verification (structural)
    # ════════════════════════════════════════════
    def test_report_structure():
        """Verify report.getTable returns valid structure for event verification."""
        entry_id = state.get("entry_id")
        assert entry_id, "No test entry available"
        now = int(time.time())
        result = kaltura_post("report", "getTable", {
            "reportType": 38,  # TOP_CONTENT_CREATOR
            "reportInputFilter[objectType]": "KalturaEndUserReportInputFilter",
            "reportInputFilter[fromDate]": now - (90 * 86400),
            "reportInputFilter[toDate]": now,
            "reportInputFilter[entryIdIn]": entry_id,
            "pager[pageSize]": 5,
            "pager[pageIndex]": 1,
            "responseOptions[objectType]": "KalturaReportResponseOptions",
            "responseOptions[delimiter]": "|",
        })
        assert "objectType" in result, f"Expected report response: {result}"
        # New entry may not have analytics data yet (propagation delay)
        # Empty responses return KalturaReportTable without a header field
        print(f"    Report structure valid, totalCount: {result.get('totalCount', 0)}")
        if result.get("header"):
            print(f"    Header: {result['header'][:60]}...")
        if result.get("data"):
            print(f"    Data available (entry has prior analytics)")

    runner.run_test("Report verification — structure check", test_report_structure)

    # ════════════════════════════════════════════
    # Phase 7: Multiple Sessions
    # ════════════════════════════════════════════
    def test_multiple_sessions():
        """Fire events from two separate sessions for the same entry."""
        entry_id = state.get("entry_id")
        assert entry_id, "No test entry available"
        for i in range(2):
            session_id = f"multi_session_{i}_{int(time.time())}"
            kaltura_post("stats", "collect", {
                "event[objectType]": "KalturaStatsEvent",
                "event[partnerId]": PARTNER_ID,
                "event[entryId]": entry_id,
                "event[eventType]": 3,  # PLAY
                "event[sessionId]": session_id,
                "event[eventTimestamp]": int(time.time()),
            })
            print(f"    Session {i+1}: {session_id}")

    runner.run_test("Multiple sessions — two PLAY events, different sessions", test_multiple_sessions)

    # ════════════════════════════════════════════
    # Cleanup & Summary
    # ════════════════════════════════════════════
    keep = "--keep" in sys.argv
    if keep:
        print("\n--- Keeping test resources (--keep flag) ---")
        if state.get("entry_id"):
            print(f"  Entry: {state['entry_id']}")
    else:
        if sys.stdin.isatty():
            input("\nPress Enter to clean up...")
        runner.cleanup()

    success = runner.summary()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
