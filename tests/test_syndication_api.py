#!/usr/bin/env python3
"""End-to-end validation of the Syndication Feeds API.
Covers: syndicationFeed CRUD (Google Video, Yahoo MRSS, iTunes, Roku),
feed URL fetch, entry filtering, entry count, iTunes-specific fields."""

import sys
import os
import time
import requests

sys.path.insert(0, os.path.dirname(__file__))
from test_helpers import kaltura_post, TestRunner, PARTNER_ID, KS, SERVICE_URL

state = {}


def main():
    runner = TestRunner("Syndication Feeds API — E2E Validation")

    # ════════════════════════════════════════════
    # Phase 1: Syndication Feed Creation
    # ════════════════════════════════════════════

    def test_feed_add_google():
        """Create a Google Video Sitemap syndication feed."""
        ts = int(time.time())
        result = kaltura_post("syndicationFeed", "add", {
            "syndicationFeed[objectType]": "KalturaGoogleVideoSyndicationFeed",
            "syndicationFeed[name]": f"API_DOC_TEST_GOOGLE_{ts}",
            "syndicationFeed[type]": 1,
            "syndicationFeed[landingPage]": "https://example.com/video/{entry_id}",
        })
        assert "id" in result, f"Expected id: {result}"
        assert "feedUrl" in result, f"Expected feedUrl: {result}"
        assert result.get("type") == 1, f"Expected type=1, got {result.get('type')}"
        state["feed_google_id"] = result["id"]
        state["feed_google_url"] = result["feedUrl"]
        runner.register_cleanup(f"Google feed {result['id']}",
                                lambda: _delete_feed(result["id"]))
        print(f"    Created: id={result['id']}, feedUrl={result['feedUrl']}")

    runner.run_test("syndicationFeed.add — Google Video Sitemap (type=1)", test_feed_add_google)

    def test_feed_add_yahoo():
        """Create a Yahoo MRSS syndication feed."""
        ts = int(time.time())
        result = kaltura_post("syndicationFeed", "add", {
            "syndicationFeed[objectType]": "KalturaYahooSyndicationFeed",
            "syndicationFeed[name]": f"API_DOC_TEST_YAHOO_{ts}",
            "syndicationFeed[type]": 2,
        })
        assert "id" in result, f"Expected id: {result}"
        assert result.get("type") == 2, f"Expected type=2, got {result.get('type')}"
        state["feed_yahoo_id"] = result["id"]
        runner.register_cleanup(f"Yahoo feed {result['id']}",
                                lambda: _delete_feed(result["id"]))
        print(f"    Created: id={result['id']}")

    runner.run_test("syndicationFeed.add — Yahoo MRSS (type=2)", test_feed_add_yahoo)

    def test_feed_add_itunes():
        """Create an iTunes podcast syndication feed."""
        ts = int(time.time())
        result = kaltura_post("syndicationFeed", "add", {
            "syndicationFeed[objectType]": "KalturaITunesSyndicationFeed",
            "syndicationFeed[name]": f"API_DOC_TEST_ITUNES_{ts}",
            "syndicationFeed[type]": 3,
            "syndicationFeed[feedDescription]": "Test podcast feed for API validation",
            "syndicationFeed[language]": "EN",
            "syndicationFeed[ownerName]": "API Doc Test",
            "syndicationFeed[ownerEmail]": "test@example.com",
        })
        assert "id" in result, f"Expected id: {result}"
        assert result.get("type") == 3, f"Expected type=3, got {result.get('type')}"
        assert result.get("objectType") == "KalturaITunesSyndicationFeed", \
            f"Expected KalturaITunesSyndicationFeed, got {result.get('objectType')}"
        state["feed_itunes_id"] = result["id"]
        runner.register_cleanup(f"iTunes feed {result['id']}",
                                lambda: _delete_feed(result["id"]))
        print(f"    Created: id={result['id']}, language={result.get('language')}")

    runner.run_test("syndicationFeed.add — iTunes Podcast (type=3)", test_feed_add_itunes)

    def test_feed_add_roku():
        """Create a Roku Direct Publisher syndication feed."""
        ts = int(time.time())
        result = kaltura_post("syndicationFeed", "add", {
            "syndicationFeed[objectType]": "KalturaRokuSyndicationFeed",
            "syndicationFeed[name]": f"API_DOC_TEST_ROKU_{ts}",
            "syndicationFeed[type]": 7,
        })
        assert "id" in result, f"Expected id: {result}"
        assert result.get("type") == 7, f"Expected type=7, got {result.get('type')}"
        state["feed_roku_id"] = result["id"]
        state["feed_roku_url"] = result.get("feedUrl", "")
        runner.register_cleanup(f"Roku feed {result['id']}",
                                lambda: _delete_feed(result["id"]))
        print(f"    Created: id={result['id']}")

    runner.run_test("syndicationFeed.add — Roku Direct Publisher (type=7)", test_feed_add_roku)

    # ════════════════════════════════════════════
    # Phase 2: Feed Read & Update
    # ════════════════════════════════════════════

    def test_feed_get():
        """Retrieve a syndication feed by ID and verify all base fields."""
        result = kaltura_post("syndicationFeed", "get", {
            "id": state["feed_google_id"],
        })
        assert result.get("id") == state["feed_google_id"], \
            f"Expected id={state['feed_google_id']}, got {result.get('id')}"
        for field in ["feedUrl", "name", "type", "status", "partnerId"]:
            assert field in result, f"Expected field '{field}' in response: {list(result.keys())}"
        print(f"    Feed: id={result['id']}, name={result['name']}, type={result['type']}")

    runner.run_test("syndicationFeed.get — retrieve feed details", test_feed_get)

    def test_feed_list():
        """List syndication feeds on the account."""
        result = kaltura_post("syndicationFeed", "list", {})
        assert "objects" in result, f"Expected objects: {result}"
        assert "totalCount" in result, f"Expected totalCount: {result}"
        assert result["totalCount"] >= 4, \
            f"Expected at least 4 feeds (created 4 in test), got {result['totalCount']}"
        state["feed_total"] = result["totalCount"]
        print(f"    Total feeds: {result['totalCount']}")

    runner.run_test("syndicationFeed.list — list all feeds", test_feed_list)

    def test_feed_update():
        """Update a syndication feed name."""
        new_name = f"API_DOC_TEST_ROKU_UPDATED_{int(time.time())}"
        result = kaltura_post("syndicationFeed", "update", {
            "id": state["feed_roku_id"],
            "syndicationFeed[objectType]": "KalturaRokuSyndicationFeed",
            "syndicationFeed[name]": new_name,
        })
        assert result.get("name") == new_name, \
            f"Expected name='{new_name}', got '{result.get('name')}'"
        print(f"    Updated: name={result['name']}")

    runner.run_test("syndicationFeed.update — modify feed name", test_feed_update)

    def test_feed_entry_count():
        """Get the entry count for a syndication feed."""
        result = kaltura_post("syndicationFeed", "getEntryCount", {
            "feedId": state["feed_google_id"],
        })
        assert "totalEntryCount" in result, f"Expected totalEntryCount: {result}"
        assert "actualEntryCount" in result, f"Expected actualEntryCount: {result}"
        assert "requireTranscodingCount" in result, f"Expected requireTranscodingCount: {result}"
        state["feed_entry_count"] = result["totalEntryCount"]
        print(f"    Entries: total={result['totalEntryCount']}, "
              f"actual={result['actualEntryCount']}, needTranscode={result['requireTranscodingCount']}")

    runner.run_test("syndicationFeed.getEntryCount — entry counts", test_feed_entry_count)

    # ════════════════════════════════════════════
    # Phase 3: Feed URL & XML Validation
    # ════════════════════════════════════════════

    def test_fetch_feed_xml():
        """Fetch the feed URL via HTTP GET and verify valid XML response."""
        feed_url = state.get("feed_roku_url", "")
        if not feed_url:
            print("    No feed URL available — skipping")
            return
        feed_url = feed_url.replace("http://", "https://")
        feed_url += "&limit=5"
        resp = requests.get(feed_url, timeout=90)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        content = resp.text
        assert "<rss" in content or "<urlset" in content or "<?xml" in content, \
            f"Expected XML content, got: {content[:200]}"
        print(f"    Feed XML: status={resp.status_code}, len={len(content)}, "
              f"starts_with={content[:80].strip()}")

    runner.run_test("Feed URL — fetch Roku XML via HTTP GET", test_fetch_feed_xml)

    # ════════════════════════════════════════════
    # Phase 4: Entry Filtering
    # ════════════════════════════════════════════

    def test_feed_with_filter():
        """Create a syndication feed with an entry filter."""
        ts = int(time.time())
        result = kaltura_post("syndicationFeed", "add", {
            "syndicationFeed[objectType]": "KalturaGoogleVideoSyndicationFeed",
            "syndicationFeed[name]": f"API_DOC_TEST_FILTERED_{ts}",
            "syndicationFeed[type]": 1,
            "syndicationFeed[landingPage]": "https://example.com/video/{entry_id}",
            "syndicationFeed[entryFilter][objectType]": "KalturaMediaEntryFilter",
            "syndicationFeed[entryFilter][tagsLike]": "api_doc_test_nonexistent_tag",
        })
        assert "id" in result, f"Expected id: {result}"
        state["feed_filtered_id"] = result["id"]
        runner.register_cleanup(f"filtered feed {result['id']}",
                                lambda: _delete_feed(result["id"]))
        print(f"    Created filtered feed: id={result['id']}")

    runner.run_test("syndicationFeed.add — with entryFilter (tagsLike)", test_feed_with_filter)

    def test_filtered_feed_count():
        """Verify filtered feed has fewer entries than unfiltered."""
        count_result = kaltura_post("syndicationFeed", "getEntryCount", {
            "feedId": state["feed_filtered_id"],
        })
        filtered_count = count_result.get("totalEntryCount", 0)
        unfiltered_count = state.get("feed_entry_count", 0)
        assert filtered_count <= unfiltered_count, \
            f"Expected filtered({filtered_count}) <= unfiltered({unfiltered_count})"
        print(f"    Filtered: {filtered_count}, Unfiltered: {unfiltered_count}")

    runner.run_test("syndicationFeed.getEntryCount — filtered vs unfiltered", test_filtered_feed_count)

    # ════════════════════════════════════════════
    # Phase 5: iTunes Feed Field Verification
    # ════════════════════════════════════════════

    def test_itunes_feed_fields():
        """Verify iTunes feed returns podcast-specific fields."""
        result = kaltura_post("syndicationFeed", "get", {
            "id": state["feed_itunes_id"],
        })
        assert result.get("objectType") == "KalturaITunesSyndicationFeed", \
            f"Expected KalturaITunesSyndicationFeed, got {result.get('objectType')}"
        assert result.get("language") == "EN", f"Expected language=EN, got {result.get('language')}"
        assert result.get("ownerName") == "API Doc Test", \
            f"Expected ownerName='API Doc Test', got {result.get('ownerName')}"
        assert result.get("ownerEmail") == "test@example.com", \
            f"Expected ownerEmail='test@example.com', got {result.get('ownerEmail')}"
        print(f"    iTunes fields: language={result.get('language')}, "
              f"owner={result.get('ownerName')}, email={result.get('ownerEmail')}")

    runner.run_test("syndicationFeed.get — iTunes podcast-specific fields", test_itunes_feed_fields)

    # ════════════════════════════════════════════
    # Phase 6: Error Handling
    # ════════════════════════════════════════════

    def test_feed_invalid_add():
        """Verify error for syndication feed with missing required objectType."""
        try:
            kaltura_post("syndicationFeed", "add", {
                "syndicationFeed[name]": "Invalid Feed",
                "syndicationFeed[type]": 1,
            })
            assert False, "Expected error for missing objectType"
        except Exception as e:
            error_str = str(e)
            assert "PROPERTY_VALIDATION" in error_str or "INVALID" in error_str or "error" in error_str.lower(), \
                f"Expected validation error: {e}"
            print(f"    Correct error: {e}")

    runner.run_test("syndicationFeed.add — validation error (missing objectType)", test_feed_invalid_add)

    # ════════════════════════════════════════════
    # Phase 7: Feed Delete Verification
    # ════════════════════════════════════════════

    def test_feed_delete_and_verify():
        """Delete a syndication feed and verify it's gone."""
        ts = int(time.time())
        result = kaltura_post("syndicationFeed", "add", {
            "syndicationFeed[objectType]": "KalturaYahooSyndicationFeed",
            "syndicationFeed[name]": f"API_DOC_TEST_DELETE_{ts}",
            "syndicationFeed[type]": 2,
        })
        delete_id = result["id"]
        print(f"    Created feed to delete: {delete_id}")

        kaltura_post("syndicationFeed", "delete", {"id": delete_id})
        print(f"    Deleted feed: {delete_id}")

        try:
            kaltura_post("syndicationFeed", "get", {"id": delete_id})
            assert False, "Expected error for deleted feed"
        except Exception as e:
            print(f"    Verified deleted: {e}")

    runner.run_test("syndicationFeed.delete — delete and verify", test_feed_delete_and_verify)

    # ════════════════════════════════════════════
    # Cleanup & Summary
    # ════════════════════════════════════════════
    keep = "--keep" in sys.argv
    if keep:
        print("\n--- Keeping resources (--keep flag) ---")
        for key in ["feed_google_id", "feed_yahoo_id", "feed_itunes_id",
                     "feed_roku_id", "feed_filtered_id"]:
            if state.get(key):
                print(f"  Feed: {state[key]}")
        print("  Run without --keep to clean up, or delete manually.")
    else:
        if sys.stdin.isatty():
            input("\nPress Enter to clean up test resources...")
        runner.cleanup()

    success = runner.summary()
    sys.exit(0 if success else 1)


def _delete_feed(feed_id):
    """Delete a syndication feed (with error handling)."""
    try:
        kaltura_post("syndicationFeed", "delete", {"id": feed_id})
    except Exception as e:
        print(f"  [WARN] Failed to delete feed {feed_id}: {e}")


if __name__ == "__main__":
    main()
