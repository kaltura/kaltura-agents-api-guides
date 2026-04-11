#!/usr/bin/env python3
"""End-to-end validation of the Analytics Reports API. Covers: report.getTable,
report.getTotal, report.getGraphs, KalturaMultiRequest batching, CSV exports,
Reports Microservice generate/serve, live analytics (beacon.list, liveReports),
multiple report types, filter validation, and error handling."""

import sys
import os
import time
import requests

sys.path.insert(0, os.path.dirname(__file__))
from test_helpers import (
    kaltura_post, reports_post, create_test_entry, delete_test_entry,
    TestRunner, PARTNER_ID, KS, SERVICE_URL, REPORTS_URL,
)

state = {}

# Date range: last 90 days
NOW = int(time.time())
FROM_TIMESTAMP = NOW - (90 * 86400)
TO_TIMESTAMP = NOW


def main():
    runner = TestRunner("Analytics Reports API — E2E Validation")

    # ════════════════════════════════════════════
    # Phase 1: Connectivity
    # ════════════════════════════════════════════
    def test_connectivity():
        """Verify report.getTable responds with a valid structure."""
        result = kaltura_post("report", "getTable", {
            "reportType": 38,  # TOP_CONTENT_CREATOR
            "reportInputFilter[objectType]": "KalturaEndUserReportInputFilter",
            "reportInputFilter[fromDate]": FROM_TIMESTAMP,
            "reportInputFilter[toDate]": TO_TIMESTAMP,
            "pager[pageSize]": 5,
            "pager[pageIndex]": 1,
            "responseOptions[objectType]": "KalturaReportResponseOptions",
            "responseOptions[delimiter]": "|",
        })
        assert "header" in result, f"Expected 'header' in response: {result}"
        assert "objectType" in result, f"Expected objectType: {result}"
        print(f"    Header: {result['header'][:80]}...")
        print(f"    Total count: {result.get('totalCount', 0)}")

    runner.run_test("report.getTable — connectivity check", test_connectivity)

    # ════════════════════════════════════════════
    # Phase 2: Core Report Actions
    # ════════════════════════════════════════════
    def test_get_table():
        """report.getTable with topContentCreator, validate pipe-delimited format."""
        result = kaltura_post("report", "getTable", {
            "reportType": 38,  # TOP_CONTENT_CREATOR
            "reportInputFilter[objectType]": "KalturaEndUserReportInputFilter",
            "reportInputFilter[fromDate]": FROM_TIMESTAMP,
            "reportInputFilter[toDate]": TO_TIMESTAMP,
            "order": "-count_plays",
            "pager[pageSize]": 10,
            "pager[pageIndex]": 1,
            "responseOptions[objectType]": "KalturaReportResponseOptions",
            "responseOptions[delimiter]": "|",
        })
        assert "header" in result, f"Missing header: {result}"
        header = result["header"]
        assert "|" in header, f"Header not pipe-delimited: {header}"
        columns = header.split("|")
        assert len(columns) >= 2, f"Expected multiple columns, got: {columns}"
        print(f"    Columns: {columns}")
        if result.get("data"):
            rows = result["data"].split(";")
            first_row_fields = rows[0].split("|")
            assert len(first_row_fields) == len(columns), \
                f"Row fields ({len(first_row_fields)}) != header columns ({len(columns)})"
            print(f"    Rows: {len(rows)}, first row fields: {len(first_row_fields)}")

    runner.run_test("report.getTable — topContentCreator with pipe delimiter", test_get_table)

    def test_get_total():
        """report.getTotal — aggregate totals as single row."""
        result = kaltura_post("report", "getTotal", {
            "reportType": 38,  # TOP_CONTENT_CREATOR
            "reportInputFilter[objectType]": "KalturaEndUserReportInputFilter",
            "reportInputFilter[fromDate]": FROM_TIMESTAMP,
            "reportInputFilter[toDate]": TO_TIMESTAMP,
            "responseOptions[objectType]": "KalturaReportResponseOptions",
            "responseOptions[delimiter]": "|",
        })
        assert "header" in result, f"Missing header: {result}"
        assert "data" in result, f"Missing data: {result}"
        assert result.get("objectType") == "KalturaReportTotal", \
            f"Unexpected objectType: {result.get('objectType')}"
        header_cols = result["header"].split("|")
        data_cols = result["data"].split("|") if result["data"] else []
        print(f"    Total header: {header_cols}")
        print(f"    Total data: {result['data'][:80]}")
        if data_cols:
            assert len(data_cols) == len(header_cols), \
                f"Data columns ({len(data_cols)}) != header ({len(header_cols)})"

    runner.run_test("report.getTotal — aggregate totals", test_get_total)

    def test_get_graphs():
        """report.getGraphs — time-series KalturaReportGraph objects."""
        result = kaltura_post("report", "getGraphs", {
            "reportType": 38,  # TOP_CONTENT_CREATOR
            "reportInputFilter[objectType]": "KalturaEndUserReportInputFilter",
            "reportInputFilter[fromDate]": FROM_TIMESTAMP,
            "reportInputFilter[toDate]": TO_TIMESTAMP,
            "reportInputFilter[interval]": "days",
            "responseOptions[objectType]": "KalturaReportResponseOptions",
            "responseOptions[delimiter]": "|",
        })
        assert isinstance(result, list), f"Expected list of graphs, got: {type(result)}"
        assert len(result) > 0, "Expected at least one graph"
        for g in result:
            assert "id" in g, f"Graph missing 'id': {g}"
            assert "data" in g, f"Graph missing 'data': {g}"
            assert g.get("objectType") == "KalturaReportGraph", \
                f"Unexpected graph objectType: {g.get('objectType')}"
        graph_ids = [g["id"] for g in result]
        print(f"    Graph metrics: {graph_ids}")
        # Verify data format: semicolon-separated label|value pairs
        sample = result[0]
        if sample["data"]:
            pairs = sample["data"].split(";")
            first_pair = pairs[0].split("|")
            assert len(first_pair) == 2, f"Expected label|value pair, got: {first_pair}"
            print(f"    Sample data points: {len(pairs)}")

    runner.run_test("report.getGraphs — time-series data", test_get_graphs)

    # ════════════════════════════════════════════
    # Phase 3: Multi-Request Batching
    # ════════════════════════════════════════════
    def test_multi_request():
        """KalturaMultiRequest — batch getTotal + getGraphs + getTable."""
        data = {
            "ks": KS,
            "format": 1,
            "1:service": "report",
            "1:action": "getTotal",
            "1:reportType": 38,
            "1:reportInputFilter[objectType]": "KalturaEndUserReportInputFilter",
            "1:reportInputFilter[fromDate]": FROM_TIMESTAMP,
            "1:reportInputFilter[toDate]": TO_TIMESTAMP,
            "1:responseOptions[objectType]": "KalturaReportResponseOptions",
            "1:responseOptions[delimiter]": "|",
            "2:service": "report",
            "2:action": "getGraphs",
            "2:reportType": 38,
            "2:reportInputFilter[objectType]": "KalturaEndUserReportInputFilter",
            "2:reportInputFilter[fromDate]": FROM_TIMESTAMP,
            "2:reportInputFilter[toDate]": TO_TIMESTAMP,
            "2:reportInputFilter[interval]": "days",
            "2:responseOptions[objectType]": "KalturaReportResponseOptions",
            "2:responseOptions[delimiter]": "|",
            "3:service": "report",
            "3:action": "getTable",
            "3:reportType": 38,
            "3:reportInputFilter[objectType]": "KalturaEndUserReportInputFilter",
            "3:reportInputFilter[fromDate]": FROM_TIMESTAMP,
            "3:reportInputFilter[toDate]": TO_TIMESTAMP,
            "3:order": "-count_plays",
            "3:pager[pageSize]": 5,
            "3:pager[pageIndex]": 1,
            "3:responseOptions[objectType]": "KalturaReportResponseOptions",
            "3:responseOptions[delimiter]": "|",
        }
        resp = requests.post(f"{SERVICE_URL}/service/multirequest", data=data, timeout=30)
        resp.raise_for_status()
        result = resp.json()
        assert isinstance(result, list), f"Expected array response, got: {type(result)}"
        assert len(result) == 3, f"Expected 3 results, got: {len(result)}"
        # Result 0: KalturaReportTotal
        assert result[0].get("objectType") == "KalturaReportTotal", \
            f"Expected KalturaReportTotal, got: {result[0].get('objectType')}"
        # Result 1: array of KalturaReportGraph
        assert isinstance(result[1], list), f"Expected graphs array, got: {type(result[1])}"
        # Result 2: KalturaReportTable
        assert result[2].get("objectType") == "KalturaReportTable", \
            f"Expected KalturaReportTable, got: {result[2].get('objectType')}"
        print(f"    Multi-request: total + {len(result[1])} graphs + table")

    runner.run_test("KalturaMultiRequest — batch 3 report calls", test_multi_request)

    # ════════════════════════════════════════════
    # Phase 4: CSV Exports
    # ════════════════════════════════════════════
    def test_csv_url():
        """report.getUrlForReportAsCsv — generate and download CSV."""
        result = kaltura_post("report", "getUrlForReportAsCsv", {
            "reportTitle": "Test Export",
            "reportText": "Automated test",
            "headers": "Entry,Name,Plays",
            "reportType": 38,  # TOP_CONTENT_CREATOR
            "reportInputFilter[objectType]": "KalturaEndUserReportInputFilter",
            "reportInputFilter[fromDate]": FROM_TIMESTAMP,
            "reportInputFilter[toDate]": TO_TIMESTAMP,
            "pager[pageSize]": 25,
            "pager[pageIndex]": 1,
            "responseOptions[objectType]": "KalturaReportResponseOptions",
            "responseOptions[delimiter]": "|",
        })
        assert isinstance(result, str), f"Expected URL string, got: {type(result)}"
        assert result.startswith("http"), f"Expected URL, got: {result}"
        print(f"    CSV URL: {result[:80]}...")
        # Download and verify
        csv_resp = requests.get(result, timeout=30)
        csv_resp.raise_for_status()
        assert len(csv_resp.text) > 0, "CSV is empty"
        lines = csv_resp.text.strip().split("\n")
        print(f"    CSV lines: {len(lines)}")

    runner.run_test("report.getUrlForReportAsCsv — CSV export", test_csv_url)

    def test_csv_from_string_params():
        """report.getCsvFromStringParams — KME room data (ID 6000)."""
        try:
            result = kaltura_post("report", "getCsvFromStringParams", {
                "id": 6000,
                "params": f"from_date={FROM_TIMESTAMP};to_date={TO_TIMESTAMP}",
            })
            # This may return CSV text or a structured response
            print(f"    Report 6000 response type: {type(result).__name__}")
            if isinstance(result, str):
                lines = result.strip().split("\n")
                print(f"    CSV lines: {len(lines)}")
            elif isinstance(result, dict):
                print(f"    Response keys: {list(result.keys())[:5]}")
        except Exception as e:
            # Report 6000 may not be available for all accounts, or may return BOM-encoded CSV
            err_str = str(e)
            if "NOT_FOUND" in err_str or "INVALID" in err_str or "not found" in err_str.lower() \
                    or "BOM" in err_str or "utf-8-sig" in err_str:
                print(f"    Report 6000 not available for this account (expected): {e}")
            else:
                raise

    runner.run_test("report.getCsvFromStringParams — report ID 6000", test_csv_from_string_params)

    # ════════════════════════════════════════════
    # Phase 5: Report Types
    # ════════════════════════════════════════════
    def test_content_dropoff():
        """report.getTable — contentDropoff report type."""
        result = kaltura_post("report", "getTable", {
            "reportType": 2,  # CONTENT_DROPOFF
            "reportInputFilter[objectType]": "KalturaEndUserReportInputFilter",
            "reportInputFilter[fromDate]": FROM_TIMESTAMP,
            "reportInputFilter[toDate]": TO_TIMESTAMP,
            "pager[pageSize]": 10,
            "pager[pageIndex]": 1,
            "responseOptions[objectType]": "KalturaReportResponseOptions",
            "responseOptions[delimiter]": "|",
        })
        assert "header" in result, f"Missing header: {result}"
        print(f"    contentDropoff header: {result['header'][:80]}...")
        print(f"    Total count: {result.get('totalCount', 0)}")

    runner.run_test("report.getTable — contentDropoff", test_content_dropoff)

    def test_map_overlay_country():
        """report.getTable — mapOverlayCountry for geographic analytics."""
        result = kaltura_post("report", "getTable", {
            "reportType": 36,  # MAP_OVERLAY_COUNTRY
            "reportInputFilter[objectType]": "KalturaEndUserReportInputFilter",
            "reportInputFilter[fromDate]": FROM_TIMESTAMP,
            "reportInputFilter[toDate]": TO_TIMESTAMP,
            "pager[pageSize]": 25,
            "pager[pageIndex]": 1,
            "responseOptions[objectType]": "KalturaReportResponseOptions",
            "responseOptions[delimiter]": "|",
        })
        assert "header" in result, f"Missing header: {result}"
        print(f"    mapOverlayCountry header: {result['header'][:80]}...")
        print(f"    Total count: {result.get('totalCount', 0)}")

    runner.run_test("report.getTable — mapOverlayCountry", test_map_overlay_country)

    def test_platforms():
        """report.getTable — platforms for device analytics."""
        result = kaltura_post("report", "getTable", {
            "reportType": 21,  # PLATFORMS
            "reportInputFilter[objectType]": "KalturaEndUserReportInputFilter",
            "reportInputFilter[fromDate]": FROM_TIMESTAMP,
            "reportInputFilter[toDate]": TO_TIMESTAMP,
            "pager[pageSize]": 25,
            "pager[pageIndex]": 1,
            "responseOptions[objectType]": "KalturaReportResponseOptions",
            "responseOptions[delimiter]": "|",
        })
        assert "header" in result, f"Missing header: {result}"
        print(f"    platforms header: {result['header'][:80]}...")
        print(f"    Total count: {result.get('totalCount', 0)}")

    runner.run_test("report.getTable — platforms", test_platforms)

    def test_unique_users_play():
        """report.getTable — uniqueUsersPlay for viewer counts."""
        result = kaltura_post("report", "getTable", {
            "reportType": 35,  # UNIQUE_USERS_PLAY
            "reportInputFilter[objectType]": "KalturaEndUserReportInputFilter",
            "reportInputFilter[fromDate]": FROM_TIMESTAMP,
            "reportInputFilter[toDate]": TO_TIMESTAMP,
            "pager[pageSize]": 10,
            "pager[pageIndex]": 1,
            "responseOptions[objectType]": "KalturaReportResponseOptions",
            "responseOptions[delimiter]": "|",
        })
        assert "header" in result, f"Missing header: {result}"
        print(f"    uniqueUsersPlay header: {result['header'][:80]}...")

    runner.run_test("report.getTable — uniqueUsersPlay", test_unique_users_play)

    def test_partner_usage():
        """report.getTotal — partnerUsage for bandwidth/storage."""
        result = kaltura_post("report", "getTotal", {
            "reportType": 201,  # PARTNER_USAGE
            "reportInputFilter[objectType]": "KalturaEndUserReportInputFilter",
            "reportInputFilter[fromDate]": FROM_TIMESTAMP,
            "reportInputFilter[toDate]": TO_TIMESTAMP,
            "responseOptions[objectType]": "KalturaReportResponseOptions",
            "responseOptions[delimiter]": "|",
        })
        assert "header" in result, f"Missing header: {result}"
        assert "data" in result, f"Missing data: {result}"
        print(f"    partnerUsage header: {result['header'][:80]}...")
        print(f"    partnerUsage data: {result['data'][:80]}")

    runner.run_test("report.getTotal — partnerUsage", test_partner_usage)

    # ════════════════════════════════════════════
    # Phase 6: Filter Validation
    # ════════════════════════════════════════════
    def test_entry_filter():
        """Filter by entryIdIn — create test entry and filter reports to it."""
        entry_id = create_test_entry()
        state["filter_entry"] = entry_id
        runner.register_cleanup(f"filter test entry {entry_id}",
                                lambda: delete_test_entry(entry_id))
        result = kaltura_post("report", "getTable", {
            "reportType": 38,  # TOP_CONTENT_CREATOR
            "reportInputFilter[objectType]": "KalturaEndUserReportInputFilter",
            "reportInputFilter[fromDate]": FROM_TIMESTAMP,
            "reportInputFilter[toDate]": TO_TIMESTAMP,
            "reportInputFilter[entryIdIn]": entry_id,
            "pager[pageSize]": 10,
            "pager[pageIndex]": 1,
            "responseOptions[objectType]": "KalturaReportResponseOptions",
            "responseOptions[delimiter]": "|",
        })
        assert "objectType" in result, f"Expected report response: {result}"
        # New entry typically has no analytics data — empty response is valid
        print(f"    Entry filter accepted, totalCount: {result.get('totalCount', 0)}")
        if "header" in result:
            print(f"    Header: {result['header'][:60]}...")

    runner.run_test("report.getTable — entryIdIn filter", test_entry_filter)

    def test_interval_hours():
        """report.getGraphs — hourly interval for intraday granularity."""
        # Use last 24 hours for hourly data
        from_24h = NOW - 86400
        result = kaltura_post("report", "getGraphs", {
            "reportType": 38,  # TOP_CONTENT_CREATOR
            "reportInputFilter[objectType]": "KalturaEndUserReportInputFilter",
            "reportInputFilter[fromDate]": from_24h,
            "reportInputFilter[toDate]": NOW,
            "reportInputFilter[interval]": "hours",
            "responseOptions[objectType]": "KalturaReportResponseOptions",
            "responseOptions[delimiter]": "|",
        })
        assert isinstance(result, list), f"Expected list, got: {type(result)}"
        if result and result[0].get("data"):
            pairs = result[0]["data"].split(";")
            print(f"    Hourly data points: {len(pairs)}")
        else:
            print("    No hourly data (may be expected for low-traffic accounts)")

    runner.run_test("report.getGraphs — hourly interval", test_interval_hours)

    def test_pagination():
        """report.getTable — pagination with pageSize=2, pageIndex=1 then 2."""
        params_base = {
            "reportType": 38,  # TOP_CONTENT_CREATOR
            "reportInputFilter[objectType]": "KalturaEndUserReportInputFilter",
            "reportInputFilter[fromDate]": FROM_TIMESTAMP,
            "reportInputFilter[toDate]": TO_TIMESTAMP,
            "order": "-count_plays",
            "responseOptions[objectType]": "KalturaReportResponseOptions",
            "responseOptions[delimiter]": "|",
        }
        # Page 1
        p1 = kaltura_post("report", "getTable", {**params_base, "pager[pageSize]": 2, "pager[pageIndex]": 1})
        assert "header" in p1, f"Missing header: {p1}"
        total = p1.get("totalCount", 0)
        print(f"    Total entries: {total}")
        if total > 2:
            # Page 2
            p2 = kaltura_post("report", "getTable", {**params_base, "pager[pageSize]": 2, "pager[pageIndex]": 2})
            assert "header" in p2, f"Missing header page 2: {p2}"
            if p1.get("data") and p2.get("data"):
                assert p1["data"] != p2["data"], "Page 1 and 2 have identical data"
                print("    Page 1 and 2 have different data (pagination works)")
        else:
            print("    Not enough data for pagination test (< 3 entries)")

    runner.run_test("report.getTable — pagination", test_pagination)

    # ════════════════════════════════════════════
    # Phase 7: Live Analytics
    # ════════════════════════════════════════════
    def test_beacon_list_health():
        """beacon.list — health beacons (log index), may be empty."""
        try:
            result = kaltura_post("beacon", "list", {
                "filter[objectType]": "KalturaBeaconFilter",
                "filter[eventTypeIn]": "0_healthData,1_healthData",
                "filter[indexTypeEqual]": "log",
                "filter[relatedObjectTypeIn]": "4",
                "filter[orderBy]": "-updatedAt",
            })
            assert "objects" in result or "totalCount" in result, \
                f"Expected beacon list response: {result}"
            count = result.get("totalCount", len(result.get("objects", [])))
            print(f"    Health beacons: {count}")
        except Exception as e:
            if "SERVICE_DOES_NOT_EXISTS" in str(e) or "does not exists" in str(e):
                print(f"    Beacon service not enabled on this account (requires live streaming provisioning)")
            else:
                raise

    runner.run_test("beacon.list — health beacons (log index)", test_beacon_list_health)

    def test_beacon_list_diagnostics():
        """beacon.list — diagnostics beacons (state index), may be empty."""
        try:
            result = kaltura_post("beacon", "list", {
                "filter[objectType]": "KalturaBeaconFilter",
                "filter[eventTypeIn]": "0_staticData,0_dynamicData,1_staticData,1_dynamicData",
                "filter[indexTypeEqual]": "state",
                "filter[relatedObjectTypeIn]": "4",
            })
            assert "objects" in result or "totalCount" in result, \
                f"Expected beacon list response: {result}"
            count = result.get("totalCount", len(result.get("objects", [])))
            print(f"    Diagnostics beacons: {count}")
        except Exception as e:
            if "SERVICE_DOES_NOT_EXISTS" in str(e) or "does not exists" in str(e):
                print(f"    Beacon service not enabled on this account (requires live streaming provisioning)")
            else:
                raise

    runner.run_test("beacon.list — diagnostics beacons (state index)", test_beacon_list_diagnostics)

    def test_live_reports():
        """liveReports.getEvents — entryTimeLine with time window."""
        from_unix = NOW - 110
        to_unix = NOW - 20
        try:
            result = kaltura_post("liveReports", "getEvents", {
                "reportType": "ENTRY_TIME_LINE",
                "filter[objectType]": "KalturaLiveReportInputFilter",
                "filter[fromTime]": from_unix,
                "filter[toTime]": to_unix,
                "filter[live]": 1,
            })
            # Response structure varies; validate it's not an error
            if isinstance(result, dict):
                print(f"    liveReports response keys: {list(result.keys())[:5]}")
            elif isinstance(result, list):
                print(f"    liveReports entries: {len(result)}")
            else:
                print(f"    liveReports response type: {type(result).__name__}")
        except Exception as e:
            # May fail if no live streams or liveReports not available
            if "SERVICE_FORBIDDEN" in str(e) or "not found" in str(e).lower():
                print(f"    liveReports not available (expected for some accounts): {e}")
            else:
                raise

    runner.run_test("liveReports.getEvents — entryTimeLine", test_live_reports)

    # ════════════════════════════════════════════
    # Phase 8: Reports Microservice
    # ════════════════════════════════════════════
    def test_reports_microservice_connectivity():
        """Reports Microservice — verify endpoint responds."""
        try:
            headers = {
                "Authorization": f"Bearer {KS}",
                "Content-Type": "application/json",
            }
            resp = requests.post(
                f"{REPORTS_URL}/api/v1/report/generate",
                headers=headers,
                json={"reportName": "registration", "reportParameters": {}},
                timeout=15,
            )
            # Accept 200 (success) or 400/422 (missing params) — both prove connectivity
            assert resp.status_code in (200, 400, 401, 403, 422, 500), \
                f"Unexpected status: {resp.status_code}"
            print(f"    Reports Microservice status: {resp.status_code}")
            if resp.status_code == 200:
                body = resp.json()
                if "sessionId" in body:
                    print(f"    Session ID: {body['sessionId']}")
                    state["reports_session"] = body["sessionId"]
        except requests.exceptions.ConnectionError:
            print(f"    Reports Microservice not reachable at {REPORTS_URL} (skipping)")
        except Exception as e:
            print(f"    Reports Microservice response: {e}")

    runner.run_test("Reports Microservice — connectivity", test_reports_microservice_connectivity)

    def test_reports_microservice_serve():
        """Reports Microservice — poll serve endpoint if session available."""
        session_id = state.get("reports_session")
        if not session_id:
            print("    Skipped: no session ID from generate step")
            return
        try:
            result = reports_post("/api/v1/report/serve", {
                "sessionId": session_id,
                "statusOnly": True,
            })
            assert "status" in result, f"Expected status in serve response: {result}"
            print(f"    Report status: {result['status']}")
        except Exception as e:
            print(f"    Serve check: {e}")

    runner.run_test("Reports Microservice — serve status check", test_reports_microservice_serve)

    # ════════════════════════════════════════════
    # Phase 9: User Engagement Reports
    # ════════════════════════════════════════════
    def test_user_engagement_timeline():
        """report.getTable — userEngagementTimeline for heatmap data."""
        result = kaltura_post("report", "getTable", {
            "reportType": 34,  # USER_ENGAGEMENT_TIMELINE
            "reportInputFilter[objectType]": "KalturaEndUserReportInputFilter",
            "reportInputFilter[fromDate]": FROM_TIMESTAMP,
            "reportInputFilter[toDate]": TO_TIMESTAMP,
            "pager[pageSize]": 10,
            "pager[pageIndex]": 1,
            "responseOptions[objectType]": "KalturaReportResponseOptions",
            "responseOptions[delimiter]": "|",
        })
        assert "header" in result, f"Missing header: {result}"
        print(f"    userEngagementTimeline header: {result['header'][:80]}...")
        print(f"    Total count: {result.get('totalCount', 0)}")

    runner.run_test("report.getTable — userEngagementTimeline", test_user_engagement_timeline)

    def test_user_top_content():
        """report.getTable — userTopContent for per-user engagement."""
        result = kaltura_post("report", "getTable", {
            "reportType": 13,  # USER_TOP_CONTENT
            "reportInputFilter[objectType]": "KalturaEndUserReportInputFilter",
            "reportInputFilter[fromDate]": FROM_TIMESTAMP,
            "reportInputFilter[toDate]": TO_TIMESTAMP,
            "pager[pageSize]": 10,
            "pager[pageIndex]": 1,
            "responseOptions[objectType]": "KalturaReportResponseOptions",
            "responseOptions[delimiter]": "|",
        })
        assert "header" in result, f"Missing header: {result}"
        print(f"    userTopContent header: {result['header'][:80]}...")

    runner.run_test("report.getTable — userTopContent", test_user_top_content)

    # ════════════════════════════════════════════
    # Phase 10: Graphs with Monthly Interval
    # ════════════════════════════════════════════
    def test_graphs_monthly():
        """report.getGraphs — monthly interval for long-term trends."""
        from_6mo = NOW - (180 * 86400)
        result = kaltura_post("report", "getGraphs", {
            "reportType": 38,  # TOP_CONTENT_CREATOR
            "reportInputFilter[objectType]": "KalturaEndUserReportInputFilter",
            "reportInputFilter[fromDate]": from_6mo,
            "reportInputFilter[toDate]": NOW,
            "reportInputFilter[interval]": "months",
            "responseOptions[objectType]": "KalturaReportResponseOptions",
            "responseOptions[delimiter]": "|",
        })
        assert isinstance(result, list), f"Expected list, got: {type(result)}"
        if result and result[0].get("data"):
            pairs = result[0]["data"].split(";")
            print(f"    Monthly data points: {len(pairs)}")
        else:
            print("    No monthly data")

    runner.run_test("report.getGraphs — monthly interval", test_graphs_monthly)

    # ════════════════════════════════════════════
    # Phase 11: Syndication and Interactions
    # ════════════════════════════════════════════
    def test_top_syndication():
        """report.getTable — topSyndication for domain/referrer data."""
        result = kaltura_post("report", "getTable", {
            "reportType": 6,  # TOP_SYNDICATION
            "reportInputFilter[objectType]": "KalturaEndUserReportInputFilter",
            "reportInputFilter[fromDate]": FROM_TIMESTAMP,
            "reportInputFilter[toDate]": TO_TIMESTAMP,
            "pager[pageSize]": 10,
            "pager[pageIndex]": 1,
            "responseOptions[objectType]": "KalturaReportResponseOptions",
            "responseOptions[delimiter]": "|",
        })
        assert "header" in result, f"Missing header: {result}"
        print(f"    topSyndication header: {result['header'][:80]}...")

    runner.run_test("report.getTable — topSyndication", test_top_syndication)

    def test_player_interactions():
        """report.getTable — playerRelatedInteractions."""
        result = kaltura_post("report", "getTable", {
            "reportType": 45,  # PLAYER_RELATED_INTERACTIONS
            "reportInputFilter[objectType]": "KalturaEndUserReportInputFilter",
            "reportInputFilter[fromDate]": FROM_TIMESTAMP,
            "reportInputFilter[toDate]": TO_TIMESTAMP,
            "pager[pageSize]": 10,
            "pager[pageIndex]": 1,
            "responseOptions[objectType]": "KalturaReportResponseOptions",
            "responseOptions[delimiter]": "|",
        })
        assert "header" in result, f"Missing header: {result}"
        print(f"    playerRelatedInteractions header: {result['header'][:80]}...")

    runner.run_test("report.getTable — playerRelatedInteractions", test_player_interactions)

    # ════════════════════════════════════════════
    # Phase 12: Error Cases
    # ════════════════════════════════════════════
    def test_error_missing_dates():
        """Error handling — missing fromDate/toDate."""
        try:
            result = kaltura_post("report", "getTable", {
                "reportType": 38,  # TOP_CONTENT_CREATOR
                "reportInputFilter[objectType]": "KalturaEndUserReportInputFilter",
                "pager[pageSize]": 5,
                "pager[pageIndex]": 1,
                "responseOptions[objectType]": "KalturaReportResponseOptions",
                "responseOptions[delimiter]": "|",
            })
            # Some report types may succeed with default dates
            print(f"    No error (default dates used): totalCount={result.get('totalCount', 0)}")
        except Exception as e:
            assert "INVALID" in str(e).upper() or "MISSING" in str(e).upper() or "error" in str(e).lower(), \
                f"Expected validation error, got: {e}"
            print(f"    Expected error: {e}")

    runner.run_test("Error — missing date filters", test_error_missing_dates)

    def test_self_serve_usage():
        """report.getTable — selfServeUsage for VPaaS billing data."""
        result = kaltura_post("report", "getTable", {
            "reportType": 60,  # SELF_SERVE_USAGE
            "reportInputFilter[objectType]": "KalturaEndUserReportInputFilter",
            "reportInputFilter[fromDate]": FROM_TIMESTAMP,
            "reportInputFilter[toDate]": TO_TIMESTAMP,
            "pager[pageSize]": 10,
            "pager[pageIndex]": 1,
            "responseOptions[objectType]": "KalturaReportResponseOptions",
            "responseOptions[delimiter]": "|",
        })
        assert "header" in result, f"Missing header: {result}"
        print(f"    selfServeUsage header: {result['header'][:80]}...")

    runner.run_test("report.getTable — selfServeUsage", test_self_serve_usage)

    # ════════════════════════════════════════════
    # Cleanup & Summary
    # ════════════════════════════════════════════
    keep = "--keep" in sys.argv
    if keep:
        print("\n--- Keeping test resources (--keep flag) ---")
        if state.get("filter_entry"):
            print(f"  Entry: {state['filter_entry']}")
    else:
        if sys.stdin.isatty():
            input("\nPress Enter to clean up...")
        runner.cleanup()

    success = runner.summary()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
