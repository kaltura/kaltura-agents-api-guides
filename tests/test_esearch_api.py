#!/usr/bin/env python3
"""
End-to-end validation of the Kaltura eSearch API against the live API.

Covers: searchEntry (unified, field-specific, starts_with, exact_match, exists,
date range, highlighting, pagination, aggregation, sorting, caption search,
metadata search), searchCategory, searchUser, combined AND/NOT logic,
and error handling.
"""

import sys
import os
import time

sys.path.insert(0, os.path.dirname(__file__))
from test_helpers import kaltura_post, TestRunner, PARTNER_ID, KS, SERVICE_URL

import requests

state = {}


def esearch_post(action, params):
    """POST to eSearch with form-encoded params. Returns parsed JSON."""
    data = {"ks": KS, "format": 1}
    data.update(params)
    resp = requests.post(
        f"{SERVICE_URL}/service/elasticsearch_esearch/action/{action}",
        data=data,
        timeout=30,
    )
    resp.raise_for_status()
    result = resp.json()
    if isinstance(result, dict) and result.get("objectType") == "KalturaAPIException":
        raise Exception(f"eSearch error: {result.get('message')} (code: {result.get('code')})")
    return result


def main():
    runner = TestRunner("eSearch API — E2E Validation")

    # ════════════════════════════════════════════
    # Phase 1: searchEntry — Basic Queries
    # ════════════════════════════════════════════

    def test_unified_search():
        """KalturaESearchUnifiedItem with PARTIAL matching."""
        result = esearch_post("searchEntry", {
            "searchParams[searchOperator][searchItems][0][objectType]": "KalturaESearchUnifiedItem",
            "searchParams[searchOperator][searchItems][0][searchTerm]": "test",
            "searchParams[searchOperator][searchItems][0][itemType]": 2,
            "searchParams[searchOperator][objectType]": "KalturaESearchEntryOperator",
            "searchParams[objectType]": "KalturaESearchEntryParams",
            "pager[pageSize]": 5,
        })
        assert "totalCount" in result, f"Missing totalCount: {list(result.keys())}"
        assert "objects" in result, f"Missing objects: {list(result.keys())}"
        state["has_entries"] = result["totalCount"] > 0
        print(f"    Unified search 'test': totalCount={result['totalCount']}, "
              f"returned={len(result.get('objects', []))}")

    runner.run_test("searchEntry — unified PARTIAL search", test_unified_search)

    def test_unified_with_highlight():
        """Unified search with addHighlight=true returns highlight data."""
        result = esearch_post("searchEntry", {
            "searchParams[searchOperator][searchItems][0][objectType]": "KalturaESearchUnifiedItem",
            "searchParams[searchOperator][searchItems][0][searchTerm]": "test",
            "searchParams[searchOperator][searchItems][0][itemType]": 2,
            "searchParams[searchOperator][searchItems][0][addHighlight]": "true",
            "searchParams[searchOperator][objectType]": "KalturaESearchEntryOperator",
            "searchParams[objectType]": "KalturaESearchEntryParams",
            "pager[pageSize]": 3,
        })
        if result["totalCount"] > 0:
            obj = result["objects"][0]
            assert "object" in obj, f"Missing 'object' in result item: {list(obj.keys())}"
            # Highlight may or may not be present depending on match location
            has_highlight = "highlight" in obj and obj["highlight"]
            has_items_data = "itemsData" in obj and obj["itemsData"]
            print(f"    Highlight present: {has_highlight}, itemsData present: {has_items_data}")
        else:
            print("    No results to check highlights (account may be empty)")

    runner.run_test("searchEntry — unified with highlighting", test_unified_with_highlight)

    def test_field_specific_name():
        """KalturaESearchEntryItem targeting the 'name' field with STARTS_WITH."""
        result = esearch_post("searchEntry", {
            "searchParams[searchOperator][searchItems][0][objectType]": "KalturaESearchEntryItem",
            "searchParams[searchOperator][searchItems][0][searchTerm]": "API",
            "searchParams[searchOperator][searchItems][0][itemType]": 3,  # STARTS_WITH
            "searchParams[searchOperator][searchItems][0][fieldName]": "name",
            "searchParams[searchOperator][objectType]": "KalturaESearchEntryOperator",
            "searchParams[objectType]": "KalturaESearchEntryParams",
            "pager[pageSize]": 5,
        })
        assert "totalCount" in result
        if result["totalCount"] > 0:
            for obj in result["objects"]:
                entry = obj["object"]
                assert "id" in entry, f"Entry missing 'id': {list(entry.keys())}"
                assert "name" in entry, f"Entry missing 'name'"
        print(f"    Field search (name STARTS_WITH 'API'): totalCount={result['totalCount']}")

    runner.run_test("searchEntry — field-specific name STARTS_WITH", test_field_specific_name)

    def test_exact_match():
        """KalturaESearchEntryItem with EXACT_MATCH on description."""
        result = esearch_post("searchEntry", {
            "searchParams[searchOperator][searchItems][0][objectType]": "KalturaESearchEntryItem",
            "searchParams[searchOperator][searchItems][0][searchTerm]": "test",
            "searchParams[searchOperator][searchItems][0][itemType]": 1,  # EXACT_MATCH
            "searchParams[searchOperator][searchItems][0][fieldName]": "description",
            "searchParams[searchOperator][objectType]": "KalturaESearchEntryOperator",
            "searchParams[objectType]": "KalturaESearchEntryParams",
            "pager[pageSize]": 3,
        })
        assert "totalCount" in result
        print(f"    Exact match (description='test'): totalCount={result['totalCount']}")

    runner.run_test("searchEntry — EXACT_MATCH on description field", test_exact_match)

    def test_exists_item_type():
        """itemType=EXISTS checks if a field has any value."""
        result = esearch_post("searchEntry", {
            "searchParams[searchOperator][searchItems][0][objectType]": "KalturaESearchEntryItem",
            "searchParams[searchOperator][searchItems][0][itemType]": 4,  # EXISTS
            "searchParams[searchOperator][searchItems][0][fieldName]": "tags",
            "searchParams[searchOperator][objectType]": "KalturaESearchEntryOperator",
            "searchParams[objectType]": "KalturaESearchEntryParams",
            "pager[pageSize]": 3,
        })
        assert "totalCount" in result
        print(f"    EXISTS (tags field): totalCount={result['totalCount']}")

    runner.run_test("searchEntry — EXISTS item type on tags", test_exists_item_type)

    # ════════════════════════════════════════════
    # Phase 2: Date Range & Combined Logic
    # ════════════════════════════════════════════

    def test_date_range():
        """Range search on created_at field with epoch timestamps."""
        now = int(time.time())
        one_year_ago = now - (365 * 86400)
        result = esearch_post("searchEntry", {
            "searchParams[searchOperator][searchItems][0][objectType]": "KalturaESearchEntryItem",
            "searchParams[searchOperator][searchItems][0][itemType]": 5,  # RANGE
            "searchParams[searchOperator][searchItems][0][fieldName]": "created_at",
            "searchParams[searchOperator][searchItems][0][range][objectType]": "KalturaESearchRange",
            "searchParams[searchOperator][searchItems][0][range][greaterThanOrEqual]": one_year_ago,
            "searchParams[searchOperator][searchItems][0][range][lessThanOrEqual]": now,
            "searchParams[searchOperator][objectType]": "KalturaESearchEntryOperator",
            "searchParams[objectType]": "KalturaESearchEntryParams",
            "pager[pageSize]": 3,
        })
        assert "totalCount" in result
        print(f"    Date range (last year): totalCount={result['totalCount']}")

    runner.run_test("searchEntry — date range on created_at", test_date_range)

    def test_and_operator():
        """AND operator combining two PARTIAL search items."""
        result = esearch_post("searchEntry", {
            "searchParams[searchOperator][operator]": 1,  # AND_OP
            "searchParams[searchOperator][objectType]": "KalturaESearchEntryOperator",
            "searchParams[searchOperator][searchItems][0][objectType]": "KalturaESearchEntryItem",
            "searchParams[searchOperator][searchItems][0][searchTerm]": "test",
            "searchParams[searchOperator][searchItems][0][itemType]": 2,  # PARTIAL
            "searchParams[searchOperator][searchItems][0][fieldName]": "name",
            "searchParams[searchOperator][searchItems][1][objectType]": "KalturaESearchEntryItem",
            "searchParams[searchOperator][searchItems][1][itemType]": 4,  # EXISTS
            "searchParams[searchOperator][searchItems][1][fieldName]": "tags",
            "searchParams[objectType]": "KalturaESearchEntryParams",
            "pager[pageSize]": 3,
        })
        assert "totalCount" in result
        print(f"    AND ('test' in name + tags EXISTS): totalCount={result['totalCount']}")

    runner.run_test("searchEntry — AND operator combining two items", test_and_operator)

    def test_or_operator():
        """OR operator matching entries with either condition."""
        result = esearch_post("searchEntry", {
            "searchParams[searchOperator][operator]": 2,  # OR_OP
            "searchParams[searchOperator][objectType]": "KalturaESearchEntryOperator",
            "searchParams[searchOperator][searchItems][0][objectType]": "KalturaESearchEntryItem",
            "searchParams[searchOperator][searchItems][0][searchTerm]": "test",
            "searchParams[searchOperator][searchItems][0][itemType]": 2,
            "searchParams[searchOperator][searchItems][0][fieldName]": "name",
            "searchParams[searchOperator][searchItems][1][objectType]": "KalturaESearchEntryItem",
            "searchParams[searchOperator][searchItems][1][searchTerm]": "demo",
            "searchParams[searchOperator][searchItems][1][itemType]": 2,
            "searchParams[searchOperator][searchItems][1][fieldName]": "name",
            "searchParams[objectType]": "KalturaESearchEntryParams",
            "pager[pageSize]": 3,
        })
        assert "totalCount" in result
        print(f"    OR ('test' OR 'demo' in name): totalCount={result['totalCount']}")

    runner.run_test("searchEntry — OR operator", test_or_operator)

    def test_not_operator():
        """NOT operator nested inside AND (A AND NOT B pattern)."""
        result = esearch_post("searchEntry", {
            "searchParams[searchOperator][operator]": 1,  # AND
            "searchParams[searchOperator][objectType]": "KalturaESearchEntryOperator",
            # Item 0: entries matching 'test' in name
            "searchParams[searchOperator][searchItems][0][objectType]": "KalturaESearchEntryItem",
            "searchParams[searchOperator][searchItems][0][searchTerm]": "test",
            "searchParams[searchOperator][searchItems][0][itemType]": 2,  # PARTIAL
            "searchParams[searchOperator][searchItems][0][fieldName]": "name",
            # Item 1: NOT operator — exclude entries with 'XYZNONEXISTENT999' in description
            "searchParams[searchOperator][searchItems][1][objectType]": "KalturaESearchEntryOperator",
            "searchParams[searchOperator][searchItems][1][operator]": 3,  # NOT_OP
            "searchParams[searchOperator][searchItems][1][searchItems][0][objectType]": "KalturaESearchEntryItem",
            "searchParams[searchOperator][searchItems][1][searchItems][0][searchTerm]": "XYZNONEXISTENT999",
            "searchParams[searchOperator][searchItems][1][searchItems][0][itemType]": 1,
            "searchParams[searchOperator][searchItems][1][searchItems][0][fieldName]": "description",
            "searchParams[objectType]": "KalturaESearchEntryParams",
            "pager[pageSize]": 3,
        })
        assert "totalCount" in result
        print(f"    AND/NOT ('test' in name AND NOT 'XYZNONEXISTENT999' in desc): totalCount={result['totalCount']}")

    runner.run_test("searchEntry — AND/NOT nested operator", test_not_operator)

    # ════════════════════════════════════════════
    # Phase 3: Pagination, Sorting, Aggregation
    # ════════════════════════════════════════════

    def test_pagination():
        """Pager controls pageIndex and pageSize correctly."""
        result1 = esearch_post("searchEntry", {
            "searchParams[searchOperator][searchItems][0][objectType]": "KalturaESearchUnifiedItem",
            "searchParams[searchOperator][searchItems][0][searchTerm]": "*",
            "searchParams[searchOperator][searchItems][0][itemType]": 2,
            "searchParams[searchOperator][objectType]": "KalturaESearchEntryOperator",
            "searchParams[objectType]": "KalturaESearchEntryParams",
            "pager[pageSize]": 2,
            "pager[pageIndex]": 1,
        })
        assert len(result1.get("objects", [])) <= 2, \
            f"Expected max 2 results, got {len(result1.get('objects', []))}"
        total = result1["totalCount"]

        if total > 2:
            result2 = esearch_post("searchEntry", {
                "searchParams[searchOperator][searchItems][0][objectType]": "KalturaESearchUnifiedItem",
                "searchParams[searchOperator][searchItems][0][searchTerm]": "*",
                "searchParams[searchOperator][searchItems][0][itemType]": 2,
                "searchParams[searchOperator][objectType]": "KalturaESearchEntryOperator",
                "searchParams[objectType]": "KalturaESearchEntryParams",
                "pager[pageSize]": 2,
                "pager[pageIndex]": 2,
            })
            assert result2["totalCount"] == total, "totalCount changed between pages"
            # Page 2 should have different entries
            ids1 = {obj["object"]["id"] for obj in result1["objects"]}
            ids2 = {obj["object"]["id"] for obj in result2.get("objects", [])}
            assert ids1 != ids2 or len(ids2) == 0, "Page 2 returned same entries as page 1"
            print(f"    Page 1: {len(result1['objects'])} items, Page 2: {len(result2.get('objects', []))} items")
        else:
            print(f"    Only {total} total results — pagination verified with single page")

    runner.run_test("searchEntry — pagination (pageSize + pageIndex)", test_pagination)

    def test_sorting():
        """OrderBy sorts results by created_at desc."""
        result = esearch_post("searchEntry", {
            "searchParams[searchOperator][searchItems][0][objectType]": "KalturaESearchUnifiedItem",
            "searchParams[searchOperator][searchItems][0][searchTerm]": "*",
            "searchParams[searchOperator][searchItems][0][itemType]": 2,
            "searchParams[searchOperator][objectType]": "KalturaESearchEntryOperator",
            "searchParams[objectType]": "KalturaESearchEntryParams",
            "searchParams[orderBy][orderItems][0][objectType]": "KalturaESearchEntryOrderByItem",
            "searchParams[orderBy][orderItems][0][sortField]": "created_at",
            "searchParams[orderBy][orderItems][0][sortOrder]": "desc",
            "pager[pageSize]": 5,
        })
        assert "objects" in result
        if len(result["objects"]) >= 2:
            dates = [obj["object"].get("createdAt", 0) for obj in result["objects"]]
            # createdAt should be in descending order
            assert dates == sorted(dates, reverse=True), \
                f"Results not sorted by createdAt desc: {dates}"
            print(f"    Sorted desc by created_at: {dates[:3]}...")
        else:
            print(f"    Only {len(result.get('objects', []))} results — sort order trivially correct")

    runner.run_test("searchEntry — orderBy created_at desc", test_sorting)

    def test_aggregation():
        """Aggregation by media_type returns bucket counts."""
        result = esearch_post("searchEntry", {
            "searchParams[searchOperator][searchItems][0][objectType]": "KalturaESearchUnifiedItem",
            "searchParams[searchOperator][searchItems][0][searchTerm]": "*",
            "searchParams[searchOperator][searchItems][0][itemType]": 2,
            "searchParams[searchOperator][objectType]": "KalturaESearchEntryOperator",
            "searchParams[objectType]": "KalturaESearchEntryParams",
            "searchParams[aggregations][aggregations][0][objectType]": "KalturaESearchEntryAggregationItem",
            "searchParams[aggregations][aggregations][0][fieldName]": "media_type",
            "searchParams[aggregations][aggregations][0][size]": 10,
            "pager[pageSize]": 1,
        })
        assert "aggregations" in result or "objects" in result, \
            f"Expected aggregations in response: {list(result.keys())}"
        if "aggregations" in result and result["aggregations"]:
            agg = result["aggregations"]
            if isinstance(agg, list) and len(agg) > 0:
                buckets = agg[0].get("buckets", [])
                print(f"    Aggregation by media_type: {len(buckets)} bucket(s)")
                for b in buckets[:3]:
                    print(f"      media_type={b.get('value')}: count={b.get('count')}")
            else:
                print(f"    Aggregation response shape: {type(agg)}")
        else:
            print("    Aggregations not in response (may need entries with varied media types)")

    runner.run_test("searchEntry — aggregation by media_type", test_aggregation)

    # ════════════════════════════════════════════
    # Phase 4: Caption & Metadata Search
    # ════════════════════════════════════════════

    def test_caption_search():
        """KalturaESearchCaptionItem searches caption content."""
        result = esearch_post("searchEntry", {
            "searchParams[searchOperator][searchItems][0][objectType]": "KalturaESearchCaptionItem",
            "searchParams[searchOperator][searchItems][0][searchTerm]": "the",
            "searchParams[searchOperator][searchItems][0][itemType]": 2,  # PARTIAL
            "searchParams[searchOperator][searchItems][0][fieldName]": "content",
            "searchParams[searchOperator][searchItems][0][addHighlight]": "true",
            "searchParams[searchOperator][objectType]": "KalturaESearchEntryOperator",
            "searchParams[objectType]": "KalturaESearchEntryParams",
            "pager[pageSize]": 3,
        })
        assert "totalCount" in result
        if result["totalCount"] > 0 and result.get("objects"):
            obj = result["objects"][0]
            items_data = obj.get("itemsData", [])
            if items_data:
                for item_data in items_data:
                    if item_data.get("itemsType") == "caption":
                        caption_items = item_data.get("items", [])
                        print(f"    Caption matches: {len(caption_items)} caption line(s)")
                        break
                else:
                    print(f"    Caption search returned {result['totalCount']} entries (itemsData present)")
            else:
                print(f"    Caption search: {result['totalCount']} entries (no itemsData detail)")
        else:
            print("    No captioned entries found (REACH captions may not be available)")

    runner.run_test("searchEntry — caption content search", test_caption_search)

    def test_metadata_search():
        """KalturaESearchEntryMetadataItem searches custom metadata (may return 0 if no profiles)."""
        result = esearch_post("searchEntry", {
            "searchParams[searchOperator][searchItems][0][objectType]": "KalturaESearchEntryMetadataItem",
            "searchParams[searchOperator][searchItems][0][searchTerm]": "test",
            "searchParams[searchOperator][searchItems][0][itemType]": 2,
            "searchParams[searchOperator][objectType]": "KalturaESearchEntryOperator",
            "searchParams[objectType]": "KalturaESearchEntryParams",
            "pager[pageSize]": 3,
        })
        assert "totalCount" in result
        print(f"    Metadata search 'test': totalCount={result['totalCount']}")

    runner.run_test("searchEntry — metadata search", test_metadata_search)

    # ════════════════════════════════════════════
    # Phase 5: searchCategory & searchUser
    # ════════════════════════════════════════════

    def test_search_category():
        """searchCategory with PARTIAL search on name returns category objects."""
        result = esearch_post("searchCategory", {
            "searchParams[searchOperator][searchItems][0][objectType]": "KalturaESearchCategoryItem",
            "searchParams[searchOperator][searchItems][0][searchTerm]": "*",
            "searchParams[searchOperator][searchItems][0][itemType]": 2,  # PARTIAL
            "searchParams[searchOperator][searchItems][0][fieldName]": "name",
            "searchParams[searchOperator][objectType]": "KalturaESearchCategoryOperator",
            "searchParams[objectType]": "KalturaESearchCategoryParams",
            "pager[pageSize]": 5,
        })
        assert "totalCount" in result, f"Missing totalCount: {list(result.keys())}"
        assert "objects" in result
        if result["totalCount"] > 0:
            cat = result["objects"][0]["object"]
            assert "id" in cat, f"Category missing id: {list(cat.keys())}"
            print(f"    Categories found: totalCount={result['totalCount']}, first={cat.get('name', '?')}")
        else:
            print("    No categories found (account may not have categories)")

    runner.run_test("searchCategory — PARTIAL search on name", test_search_category)

    def test_search_user():
        """searchUser with PARTIAL search returns user objects."""
        result = esearch_post("searchUser", {
            "searchParams[searchOperator][searchItems][0][objectType]": "KalturaESearchUserItem",
            "searchParams[searchOperator][searchItems][0][searchTerm]": "*",
            "searchParams[searchOperator][searchItems][0][itemType]": 2,  # PARTIAL
            "searchParams[searchOperator][searchItems][0][fieldName]": "screen_name",
            "searchParams[searchOperator][objectType]": "KalturaESearchUserOperator",
            "searchParams[objectType]": "KalturaESearchUserParams",
            "pager[pageSize]": 5,
        })
        assert "totalCount" in result
        assert "objects" in result
        if result["totalCount"] > 0:
            user = result["objects"][0]["object"]
            assert "id" in user, f"User missing id: {list(user.keys())}"
            print(f"    Users found: totalCount={result['totalCount']}, first={user.get('id', '?')}")
        else:
            print("    No users found")

    runner.run_test("searchUser — PARTIAL search on screen_name", test_search_user)

    # ════════════════════════════════════════════
    # Phase 6: Response Structure Validation
    # ════════════════════════════════════════════

    def test_response_structure():
        """Validate the response structure matches documented format."""
        result = esearch_post("searchEntry", {
            "searchParams[searchOperator][searchItems][0][objectType]": "KalturaESearchUnifiedItem",
            "searchParams[searchOperator][searchItems][0][searchTerm]": "*",
            "searchParams[searchOperator][searchItems][0][itemType]": 2,
            "searchParams[searchOperator][objectType]": "KalturaESearchEntryOperator",
            "searchParams[objectType]": "KalturaESearchEntryParams",
            "pager[pageSize]": 1,
        })
        assert isinstance(result.get("totalCount"), int), \
            f"totalCount should be int, got {type(result.get('totalCount'))}"
        assert isinstance(result.get("objects"), list), \
            f"objects should be list, got {type(result.get('objects'))}"
        if result["objects"]:
            obj = result["objects"][0]
            assert "object" in obj, f"Result item missing 'object' key: {list(obj.keys())}"
            entry = obj["object"]
            required_fields = ["id", "name", "objectType"]
            for field in required_fields:
                assert field in entry, f"Entry missing '{field}': {list(entry.keys())}"
        print(f"    Response structure validated (totalCount={result['totalCount']})")

    runner.run_test("searchEntry — response structure matches docs", test_response_structure)

    # ════════════════════════════════════════════
    # Phase 7: Abstract vs Concrete Types, JSON Body, Caption Timestamps
    # ════════════════════════════════════════════

    def test_abstract_orderby_fails():
        """Abstract KalturaESearchOrderByItem returns OBJECT_TYPE_ABSTRACT error."""
        data = {"ks": KS, "format": 1}
        data.update({
            "searchParams[searchOperator][searchItems][0][objectType]": "KalturaESearchUnifiedItem",
            "searchParams[searchOperator][searchItems][0][searchTerm]": "test",
            "searchParams[searchOperator][searchItems][0][itemType]": 2,
            "searchParams[searchOperator][objectType]": "KalturaESearchEntryOperator",
            "searchParams[objectType]": "KalturaESearchEntryParams",
            "searchParams[orderBy][orderItems][0][objectType]": "KalturaESearchOrderByItem",
            "searchParams[orderBy][orderItems][0][sortField]": "created_at",
            "searchParams[orderBy][orderItems][0][sortOrder]": "desc",
        })
        resp = requests.post(
            f"{SERVICE_URL}/service/elasticsearch_esearch/action/searchEntry",
            data=data, timeout=30,
        )
        result = resp.json()
        assert result.get("code") == "OBJECT_TYPE_ABSTRACT", \
            f"Expected OBJECT_TYPE_ABSTRACT, got: {result.get('code', result)}"
        print(f"    Abstract type correctly rejected: {result['message']}")

    runner.run_test("orderBy — abstract KalturaESearchOrderByItem fails", test_abstract_orderby_fails)

    def test_concrete_orderby_works():
        """Concrete KalturaESearchEntryOrderByItem succeeds for entry search."""
        result = esearch_post("searchEntry", {
            "searchParams[searchOperator][searchItems][0][objectType]": "KalturaESearchUnifiedItem",
            "searchParams[searchOperator][searchItems][0][searchTerm]": "test",
            "searchParams[searchOperator][searchItems][0][itemType]": 2,
            "searchParams[searchOperator][objectType]": "KalturaESearchEntryOperator",
            "searchParams[objectType]": "KalturaESearchEntryParams",
            "searchParams[orderBy][orderItems][0][objectType]": "KalturaESearchEntryOrderByItem",
            "searchParams[orderBy][orderItems][0][sortField]": "created_at",
            "searchParams[orderBy][orderItems][0][sortOrder]": "desc",
            "pager[pageSize]": 2,
        })
        assert "totalCount" in result, f"Expected results, got error: {result}"
        print(f"    Concrete EntryOrderByItem: totalCount={result['totalCount']}")

    runner.run_test("orderBy — concrete KalturaESearchEntryOrderByItem works", test_concrete_orderby_works)

    def test_aggregation_correct_path():
        """Aggregations require double nesting: searchParams[aggregations][aggregations][0]."""
        result = esearch_post("searchEntry", {
            "searchParams[searchOperator][searchItems][0][objectType]": "KalturaESearchEntryItem",
            "searchParams[searchOperator][searchItems][0][itemType]": 4,
            "searchParams[searchOperator][searchItems][0][fieldName]": "tags",
            "searchParams[searchOperator][objectType]": "KalturaESearchEntryOperator",
            "searchParams[objectType]": "KalturaESearchEntryParams",
            "searchParams[aggregations][aggregations][0][objectType]": "KalturaESearchEntryAggregationItem",
            "searchParams[aggregations][aggregations][0][fieldName]": "media_type",
            "searchParams[aggregations][aggregations][0][size]": 10,
            "pager[pageSize]": 1,
        })
        assert "aggregations" in result and result["aggregations"], \
            f"Aggregations missing with correct path: {list(result.keys())}"
        buckets = result["aggregations"][0].get("buckets", [])
        assert len(buckets) > 0, "Expected at least one aggregation bucket"
        print(f"    Correct aggregation path: {len(buckets)} bucket(s)")

    runner.run_test("aggregations — correct double-nested path returns buckets", test_aggregation_correct_path)

    def test_aggregation_wrong_path_silent():
        """Single-level aggregation path silently returns no aggregations."""
        result = esearch_post("searchEntry", {
            "searchParams[searchOperator][searchItems][0][objectType]": "KalturaESearchEntryItem",
            "searchParams[searchOperator][searchItems][0][itemType]": 4,
            "searchParams[searchOperator][searchItems][0][fieldName]": "tags",
            "searchParams[searchOperator][objectType]": "KalturaESearchEntryOperator",
            "searchParams[objectType]": "KalturaESearchEntryParams",
            "searchParams[aggregations][0][objectType]": "KalturaESearchEntryAggregationItem",
            "searchParams[aggregations][0][fieldName]": "media_type",
            "searchParams[aggregations][0][size]": 10,
            "pager[pageSize]": 1,
        })
        has_aggs = "aggregations" in result and result["aggregations"]
        assert not has_aggs, \
            f"Single-level aggregation path should return no aggregations, but got: {result.get('aggregations')}"
        print("    Wrong path (single-level) correctly returns no aggregations")

    runner.run_test("aggregations — wrong single-level path returns nothing", test_aggregation_wrong_path_silent)

    def test_caption_timestamps():
        """Caption search returns startsAt/endsAt as integers in milliseconds."""
        result = esearch_post("searchEntry", {
            "searchParams[searchOperator][searchItems][0][objectType]": "KalturaESearchCaptionItem",
            "searchParams[searchOperator][searchItems][0][searchTerm]": "the",
            "searchParams[searchOperator][searchItems][0][itemType]": 2,
            "searchParams[searchOperator][searchItems][0][fieldName]": "content",
            "searchParams[searchOperator][searchItems][0][addHighlight]": "true",
            "searchParams[searchOperator][objectType]": "KalturaESearchEntryOperator",
            "searchParams[objectType]": "KalturaESearchEntryParams",
            "pager[pageSize]": 1,
        })
        if result["totalCount"] > 0 and result.get("objects"):
            obj = result["objects"][0]
            for item_data in obj.get("itemsData", []):
                if item_data.get("itemsType") == "caption":
                    items = item_data.get("items", [])
                    if items:
                        item = items[0]
                        starts_at = item.get("startsAt")
                        ends_at = item.get("endsAt")
                        assert isinstance(starts_at, int), \
                            f"startsAt should be int, got {type(starts_at).__name__}: {starts_at}"
                        assert isinstance(ends_at, int), \
                            f"endsAt should be int, got {type(ends_at).__name__}: {ends_at}"
                        assert ends_at > starts_at, \
                            f"endsAt ({ends_at}) should be > startsAt ({starts_at})"
                        print(f"    Caption timestamps: startsAt={starts_at}ms ({starts_at/1000:.1f}s), "
                              f"endsAt={ends_at}ms ({ends_at/1000:.1f}s)")
                    break
            else:
                print("    No caption itemsData found")
        else:
            print("    No captioned entries found (skipping timestamp validation)")

    runner.run_test("caption search — startsAt/endsAt are int milliseconds", test_caption_timestamps)

    def test_json_body_search():
        """JSON body with Content-Type: application/json produces identical results."""
        import json as json_mod
        json_body = {
            "ks": KS,
            "format": 1,
            "searchParams": {
                "objectType": "KalturaESearchEntryParams",
                "searchOperator": {
                    "objectType": "KalturaESearchEntryOperator",
                    "operator": 2,
                    "searchItems": [{
                        "objectType": "KalturaESearchUnifiedItem",
                        "searchTerm": "test",
                        "itemType": 2
                    }]
                }
            },
            "pager": {"pageSize": 3}
        }
        resp = requests.post(
            f"{SERVICE_URL}/service/elasticsearch_esearch/action/searchEntry",
            json=json_body, timeout=30,
        )
        resp.raise_for_status()
        result = resp.json()
        assert "totalCount" in result, f"JSON body failed: {result}"
        assert result.get("objectType") != "KalturaAPIException", \
            f"JSON body returned error: {result.get('message')}"
        print(f"    JSON body: totalCount={result['totalCount']}")

    runner.run_test("searchEntry — JSON body (Content-Type: application/json)", test_json_body_search)

    # ════════════════════════════════════════════
    # Phase 8: Error Handling
    # ════════════════════════════════════════════

    def test_invalid_object_type():
        """Invalid objectType in searchParams returns an error."""
        try:
            esearch_post("searchEntry", {
                "searchParams[searchOperator][searchItems][0][objectType]": "KalturaInvalidType",
                "searchParams[searchOperator][searchItems][0][searchTerm]": "test",
                "searchParams[searchOperator][searchItems][0][itemType]": 2,
                "searchParams[searchOperator][objectType]": "KalturaESearchEntryOperator",
                "searchParams[objectType]": "KalturaESearchEntryParams",
            })
            # Some invalid types may be silently ignored
            print("    Invalid objectType was silently accepted (server may ignore unknown types)")
        except Exception as e:
            assert "error" in str(e).lower() or "invalid" in str(e).lower() or "not_valid" in str(e).lower(), \
                f"Expected validation error, got: {e}"
            print(f"    Invalid objectType correctly rejected: {e}")

    runner.run_test("Error handling — invalid objectType", test_invalid_object_type)

    def test_empty_search_operator():
        """Search with no searchItems returns an error or empty results."""
        try:
            result = esearch_post("searchEntry", {
                "searchParams[searchOperator][objectType]": "KalturaESearchEntryOperator",
                "searchParams[objectType]": "KalturaESearchEntryParams",
                "pager[pageSize]": 1,
            })
            # May return empty results
            assert "totalCount" in result
            print(f"    Empty search operator: totalCount={result['totalCount']}")
        except Exception as e:
            print(f"    Empty search operator rejected: {e}")

    runner.run_test("Error handling — empty search operator", test_empty_search_operator)

    # ════════════════════════════════════════════
    # Summary (no cleanup needed — read-only)
    # ════════════════════════════════════════════

    success = runner.summary()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    print(f"\n{'='*60}")
    print("  KALTURA ESEARCH API — End-to-End Validation")
    print(f"{'='*60}\n")
    main()
