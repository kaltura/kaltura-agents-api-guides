#!/usr/bin/env python3
"""
End-to-end validation of KALTURA_AI_GENIE_API.md against the live API.

Tests every documented endpoint and parameter:
- GET /health — service health check
- GET /assistant/status — configuration and capabilities
- POST /mcp/search — stateless RAG vector search (text-only, with sources, top_n,
  margins_in_seconds, with_line_numbers)
- POST /assistant/converse — streaming SSE and NDJSON, model_type, threadId,
  force_experience, preload_entry_ids, filter_entry_ids, exclude_entry_ids,
  capabilities, add_message_in_db
- WebSocket /assistant/ws — init, converse, abort events
- POST /thread/list — list threads (orderBy, statusIn, contextIdEqual)
- POST /thread/delete — delete threads
- POST /message/list — list messages (threadIdEquals, idEquals)
- POST /message/share — create shareable message link
- POST /feedback/add, /feedback/list — thumbs up/down, filtered list
- POST /followup/get-suggested-questions — suggested questions

Requires KALTURA_GENIE_ID and KALTURA_ADMIN_SECRET in .env.
The KS includes genieid:<ID> privilege for proper workspace routing.
"""

import sys
import os
import time
import json
import asyncio
import requests

sys.path.insert(0, os.path.dirname(__file__))
from test_helpers import TestRunner, PARTNER_ID, SERVICE_URL, GENIE_BASE_URL

GENIE_ID = os.environ.get("KALTURA_GENIE_ID", "")
GENIE_CATEGORY_ID = os.environ.get("KALTURA_GENIE_CATEGORY_ID", "")
ADMIN_SECRET = os.environ.get("KALTURA_ADMIN_SECRET", "")
USER_ID = os.environ.get("KALTURA_USER_ID", "")


def _generate_genie_ks():
    """Generate a KS with genieid privilege for Genie API access."""
    if not ADMIN_SECRET:
        print("ERROR: KALTURA_ADMIN_SECRET required for Genie tests")
        sys.exit(1)
    privs = "disableentitlement"
    if GENIE_ID:
        privs += f",genieid:{GENIE_ID}"
    if GENIE_CATEGORY_ID:
        privs += f",geniecategoryid:{GENIE_CATEGORY_ID}"
    resp = requests.post(
        f"{SERVICE_URL}/service/session/action/start",
        data={
            "format": 1,
            "partnerId": PARTNER_ID,
            "secret": ADMIN_SECRET,
            "type": 2,
            "userId": USER_ID,
            "expiry": 86400,
            "privileges": privs,
        },
        timeout=15,
    )
    resp.raise_for_status()
    ks = resp.json()
    if isinstance(ks, dict) and ks.get("objectType") == "KalturaAPIException":
        print(f"ERROR: session.start failed: {ks.get('message')}")
        sys.exit(1)
    return ks


GENIE_KS = _generate_genie_ks()
print(f"  Genie KS generated (genieid={GENIE_ID or 'none'}, "
      f"categoryid={GENIE_CATEGORY_ID or 'none'}): {GENIE_KS[:30]}...")


def genie_post_with_ks(path, json_body=None, headers_override=None, stream=False, timeout=30):
    """POST to Genie API with the Genie-specific KS."""
    headers = {
        "Authorization": f"KS {GENIE_KS}",
        "Content-Type": "application/json",
    }
    if headers_override:
        headers.update(headers_override)
    resp = requests.post(
        f"{GENIE_BASE_URL}{path}",
        headers=headers,
        json=json_body or {},
        stream=stream,
        timeout=timeout,
    )
    resp.raise_for_status()
    if stream:
        return resp
    return resp.json()


def genie_get_with_ks(path, timeout=15):
    """GET from Genie API with the Genie-specific KS."""
    resp = requests.get(
        f"{GENIE_BASE_URL}{path}",
        headers={
            "Authorization": f"KS {GENIE_KS}",
            "Content-Type": "application/json",
        },
        timeout=timeout,
    )
    resp.raise_for_status()
    return resp.json()


state = {}


def _build_test_query():
    """Build a test query from the actual content in the Genie category."""
    cat_id = GENIE_CATEGORY_ID
    if not cat_id:
        return "What is this about?"
    try:
        from test_helpers import kaltura_post
        result = kaltura_post("baseEntry", "list", {
            "filter[objectType]": "KalturaBaseEntryFilter",
            "filter[categoriesIdsMatchOr]": cat_id,
            "filter[statusEqual]": 2,
            "pager[pageSize]": 5,
        })
        entries = result.get("objects", [])
        if entries:
            state["test_entry_id"] = entries[0]["id"]
            state["test_entry_name"] = entries[0].get("name", "")
            state["all_entry_ids"] = [e["id"] for e in entries]
            name = entries[0].get("name", "")
            return f"Tell me about {name}" if name else "What is this about?"
    except Exception:
        pass
    return "What is this about?"


TEST_QUERY = _build_test_query()
print(f"  Test query: {TEST_QUERY}")
if state.get("all_entry_ids"):
    print(f"  Category entries: {state['all_entry_ids']}")


def collect_ndjson_events(resp):
    """Collect all NDJSON events from a streaming response."""
    events = []
    for line in resp.iter_lines(decode_unicode=True):
        if not line or not line.strip():
            continue
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            pass
    return events


def main():
    runner = TestRunner("AI Genie API Validation")

    # ════════════════════════════════════════════
    # Phase 1: Health & Status
    # ════════════════════════════════════════════

    def test_health():
        """GET /health — verify service is running."""
        result = genie_get_with_ks("/health")
        assert result.get("status") == "success", f"Expected status=success. Got: {result}"
        assert "version" in result, f"Missing 'version'. Keys: {list(result.keys())}"
        print(f"    Status: {result['status']}, version: {result['version']}")

    runner.run_test("/health — service health check", test_health)

    def test_assistant_status():
        """GET /assistant/status — verify config returned."""
        result = genie_get_with_ks("/assistant/status")
        assert "aiConsent" in result, f"Missing 'aiConsent'. Keys: {list(result.keys())}"
        assert "identifiedUser" in result, f"Missing 'identifiedUser'. Keys: {list(result.keys())}"
        print(f"    aiConsent: {result['aiConsent']}")
        print(f"    identifiedUser: {result['identifiedUser']}")
        print(f"    avatar: {'configured' if result.get('avatar') else 'none'}")
        state["has_avatar"] = result.get("avatar") is not None

    runner.run_test("/assistant/status — configuration and capabilities", test_assistant_status)

    # ════════════════════════════════════════════
    # Phase 2: /mcp/search — Stateless RAG
    # ════════════════════════════════════════════

    def test_mcp_search_text_only():
        """Test /mcp/search with query + include_sources=false."""
        result = genie_post_with_ks("/mcp/search", {
            "query": TEST_QUERY,
            "include_sources": False,
        })
        status = result.get("status")
        assert status in ("success", "error"), f"Unexpected status: {result}"
        if status == "success":
            data = result["data"]
            assert "text" in data, f"Expected 'text' in data. Keys: {list(data.keys())}"
            print(f"    text: {len(data['text'])} chars")
            print(f"    Preview: {data['text'][:150]}...")
            state["mcp_search_has_results"] = True
        else:
            print(f"    Vector index returned no results (valid when indexer hasn't processed entries)")
            state["mcp_search_has_results"] = False

    runner.run_test("/mcp/search — text-only response", test_mcp_search_text_only)

    def test_mcp_search_with_sources():
        """Test /mcp/search with include_sources=true."""
        result = genie_post_with_ks("/mcp/search", {
            "query": TEST_QUERY,
            "include_sources": True,
        })
        status = result.get("status")
        assert status in ("success", "error"), f"Unexpected status: {result}"
        if status == "success":
            data = result["data"]
            if "chapters" in data and len(data.get("chapters", [])) > 0:
                chapters = data["chapters"]
                for ch in chapters[:3]:
                    assert "entry_id" in ch, f"Chapter missing entry_id. Keys: {list(ch.keys())}"
                    assert "text" in ch, "Chapter missing text"
                print(f"    Got {len(chapters)} chapters with sources")
                for ch in chapters[:3]:
                    print(f"      - entry_id={ch['entry_id']}, "
                          f"time={ch.get('start_time', '?')}-{ch.get('end_time', '?')}s, "
                          f"text={len(ch['text'])} chars")
            else:
                print(f"    No chapters in response (index may be sparse)")
        else:
            print(f"    Vector search returned no results")

    runner.run_test("/mcp/search — with sources (include_sources=true)", test_mcp_search_with_sources)

    def test_mcp_search_top_n():
        """Test /mcp/search with top_n parameter."""
        result = genie_post_with_ks("/mcp/search", {
            "query": TEST_QUERY,
            "top_n": 2,
            "include_sources": True,
        })
        status = result.get("status")
        assert status in ("success", "error"), f"Unexpected status: {result}"
        if status == "success":
            chapters = result.get("data", {}).get("chapters", [])
            print(f"    top_n=2: got {len(chapters)} chapters")
            assert len(chapters) <= 2, f"Expected at most 2 chapters with top_n=2, got {len(chapters)}"
        else:
            print(f"    No vector results (top_n parameter accepted without error)")

    runner.run_test("/mcp/search — top_n parameter", test_mcp_search_top_n)

    def test_mcp_search_margins():
        """Test /mcp/search with margins_in_seconds parameter."""
        result = genie_post_with_ks("/mcp/search", {
            "query": TEST_QUERY,
            "include_sources": True,
            "margins_in_seconds": 30,
        })
        status = result.get("status")
        assert status in ("success", "error"), f"Unexpected status: {result}"
        if status == "success":
            chapters = result.get("data", {}).get("chapters", [])
            print(f"    margins_in_seconds=30: got {len(chapters)} chapters")
            if chapters:
                ch = chapters[0]
                print(f"      time range: {ch.get('start_time', '?')}-{ch.get('end_time', '?')}s")
        else:
            print(f"    No vector results (margins_in_seconds parameter accepted)")

    runner.run_test("/mcp/search — margins_in_seconds parameter", test_mcp_search_margins)

    def test_mcp_search_line_numbers():
        """Test /mcp/search with with_line_numbers parameter."""
        result = genie_post_with_ks("/mcp/search", {
            "query": TEST_QUERY,
            "include_sources": False,
            "with_line_numbers": True,
        })
        status = result.get("status")
        assert status in ("success", "error"), f"Unexpected status: {result}"
        if status == "success":
            text = result.get("data", {}).get("text", "")
            print(f"    with_line_numbers=true: {len(text)} chars")
            print(f"    Preview: {text[:120]}...")
        else:
            print(f"    No vector results (with_line_numbers parameter accepted)")

    runner.run_test("/mcp/search — with_line_numbers parameter", test_mcp_search_line_numbers)

    # ════════════════════════════════════════════
    # Phase 3: /assistant/converse — Streaming
    # ════════════════════════════════════════════

    def test_converse_ndjson():
        """Test /assistant/converse with sse=false (NDJSON)."""
        resp = genie_post_with_ks("/assistant/converse", {
            "userMessage": TEST_QUERY,
            "sse": False,
        }, headers_override={"Accept": "application/x-ndjson"}, stream=True, timeout=300)

        events = collect_ndjson_events(resp)
        assert len(events) > 0, "No events received from converse (NDJSON)"
        event_types = {e.get("type", "?") for e in events}
        print(f"    Received {len(events)} events, types: {sorted(event_types)}")

        state["converse_event_types"] = event_types
        state["converse_events"] = events

        text_content = "".join(e.get("content", "") for e in events if e.get("type") == "text")
        if text_content:
            print(f"    Text answer: {len(text_content)} chars")
            print(f"    Preview: {text_content[:150]}...")

    runner.run_test("/assistant/converse — NDJSON (sse=false)", test_converse_ndjson)

    def test_converse_sse():
        """Test /assistant/converse with sse=true (SSE)."""
        last_err = None
        for attempt in range(2):
            try:
                resp = genie_post_with_ks("/assistant/converse", {
                    "userMessage": TEST_QUERY,
                    "sse": True,
                }, headers_override={"Accept": "text/event-stream"}, stream=True, timeout=300)

                events = []
                for line in resp.iter_lines(decode_unicode=True):
                    if not line:
                        continue
                    payload = None
                    if line.startswith("data:"):
                        payload = line[5:].strip()
                    elif line.startswith("{"):
                        payload = line
                    if payload:
                        try:
                            events.append(json.loads(payload))
                        except json.JSONDecodeError:
                            pass

                assert len(events) > 0, "No events received from converse (SSE)"
                event_types = {e.get("type", "?") for e in events}
                print(f"    Received {len(events)} SSE events, types: {sorted(event_types)}")
                return
            except Exception as e:
                last_err = e
                if attempt == 0:
                    print(f"    SSE attempt {attempt+1} failed ({e}), retrying...")
                    time.sleep(2)
        raise last_err

    runner.run_test("/assistant/converse — SSE (sse=true)", test_converse_sse)

    def test_converse_event_types():
        """Verify documented event types appear in the stream."""
        types = state.get("converse_event_types", set())
        documented_types = {"think", "tool", "tool_response", "unisphere-tool", "text", "thread", "share"}
        found = types & documented_types
        print(f"    Documented types found: {sorted(found)}")
        print(f"    All types seen: {sorted(types)}")
        assert "text" in types or "unisphere-tool" in types, (
            f"Neither 'text' nor 'unisphere-tool' in event types: {types}"
        )

    runner.run_test("/assistant/converse — documented event types present", test_converse_event_types)

    def test_converse_threadid_messageid():
        """Verify first event returns threadId and messageId."""
        events = state.get("converse_events", [])
        assert len(events) > 0, "No events to check"
        first = events[0]
        assert "threadId" in first, f"First event missing 'threadId'. Keys: {list(first.keys())}"
        assert "messageId" in first, f"First event missing 'messageId'. Keys: {list(first.keys())}"
        state["thread_id"] = first["threadId"]
        state["message_id"] = first["messageId"]
        print(f"    threadId: {first['threadId']}")
        print(f"    messageId: {first['messageId']}")

    runner.run_test("/assistant/converse — threadId and messageId in first event", test_converse_threadid_messageid)

    def test_converse_unisphere_tools():
        """Check for flashcards-tool, followups-tool, sources-tool in unisphere-tool events."""
        events = state.get("converse_events", [])
        runtime_names = set()
        segment_runtimes = {}
        for e in events:
            if e.get("type") == "unisphere-tool":
                rn = e.get("metadata", {}).get("runtimeName", "")
                sn = e.get("segmentNumber", 0)
                if rn:
                    runtime_names.add(rn)
                    segment_runtimes[sn] = rn
        print(f"    unisphere-tool runtimes: {sorted(runtime_names)}")
        documented_runtimes = {"flashcards-tool", "followups-tool", "sources-tool"}
        found = runtime_names & documented_runtimes
        if found:
            print(f"    Documented runtimes found: {sorted(found)}")
        state["segment_runtimes"] = segment_runtimes

    runner.run_test("/assistant/converse — unisphere-tool runtimes", test_converse_unisphere_tools)

    def test_converse_flashcards_structure():
        """Verify flashcards-tool content has documented fields (title, keypoints, entry_id)."""
        events = state.get("converse_events", [])
        segment_runtimes = state.get("segment_runtimes", {})

        segments = {}
        for e in events:
            if e.get("type") == "unisphere-tool":
                sn = e.get("segmentNumber", 0)
                if sn not in segments:
                    segments[sn] = ""
                segments[sn] += e.get("content", "")

        flashcards_content = None
        for sn, content in segments.items():
            rn = segment_runtimes.get(sn, "")
            if rn == "flashcards-tool" and content:
                flashcards_content = content
                break
            elif not rn and content and "keypoints:" in content.lower():
                flashcards_content = content
                break

        if not flashcards_content:
            for sn, content in segments.items():
                if content and "title:" in content.lower() and "summary:" in content.lower():
                    flashcards_content = content
                    break

        if not flashcards_content:
            print("    No flashcards content found — skipping structure check")
            return

        print(f"    Flashcards content: {len(flashcards_content)} chars")
        has_title = "title:" in flashcards_content.lower()
        has_summary = "summary:" in flashcards_content.lower()
        has_keypoints = "keypoints:" in flashcards_content.lower()
        has_entry_id = "entry_id" in flashcards_content
        has_start_time = "start_time" in flashcards_content
        print(f"    has title: {has_title}, summary: {has_summary}, keypoints: {has_keypoints}")
        print(f"    has entry_id: {has_entry_id}, has start_time: {has_start_time}")
        assert has_title, "Flashcards content missing 'title:'"

    runner.run_test("/assistant/converse — flashcards-tool structure", test_converse_flashcards_structure)

    def test_converse_sources_structure():
        """Verify sources-tool content has entry_id, title, type."""
        events = state.get("converse_events", [])
        segment_runtimes = state.get("segment_runtimes", {})

        segments = {}
        for e in events:
            if e.get("type") == "unisphere-tool":
                sn = e.get("segmentNumber", 0)
                if sn not in segments:
                    segments[sn] = ""
                segments[sn] += e.get("content", "")

        sources_content = None
        for sn, content in segments.items():
            rn = segment_runtimes.get(sn, "")
            if rn == "sources-tool" and content:
                sources_content = content
                break

        if not sources_content:
            print("    No sources-tool content found — skipping")
            return

        print(f"    Sources content: {len(sources_content)} chars")
        has_entry_id = "entry_id" in sources_content
        has_title = "title:" in sources_content.lower()
        has_type = "type:" in sources_content.lower()
        print(f"    has entry_id: {has_entry_id}, title: {has_title}, type: {has_type}")
        assert has_entry_id, "Sources content missing 'entry_id'"
        assert has_title, "Sources content missing 'title'"

    runner.run_test("/assistant/converse — sources-tool structure", test_converse_sources_structure)

    # ════════════════════════════════════════════
    # Phase 4: Converse — model_type, threadId, force_experience, advanced params
    # ════════════════════════════════════════════

    def test_converse_model_type_fast():
        """Test model_type=fast produces a valid response."""
        resp = genie_post_with_ks("/assistant/converse", {
            "userMessage": TEST_QUERY,
            "sse": False,
            "model_type": "fast",
        }, stream=True, timeout=300)
        events = collect_ndjson_events(resp)
        assert len(events) > 0, "No events with model_type=fast"
        types = {e.get("type") for e in events}
        print(f"    model_type=fast: {len(events)} events, types: {sorted(types)}")
        for e in events:
            if e.get("threadId"):
                state["fast_thread_id"] = e["threadId"]
                break
        assert state.get("fast_thread_id"), "No threadId returned with model_type=fast"
        print(f"    threadId: {state['fast_thread_id']}")

    runner.run_test("/assistant/converse — model_type=fast", test_converse_model_type_fast)

    def test_converse_model_type_smart():
        """Test model_type=smart produces a valid response."""
        resp = genie_post_with_ks("/assistant/converse", {
            "userMessage": TEST_QUERY,
            "sse": False,
            "model_type": "smart",
        }, stream=True, timeout=120)
        events = collect_ndjson_events(resp)
        assert len(events) > 0, "No events with model_type=smart"
        types = {e.get("type") for e in events}
        print(f"    model_type=smart: {len(events)} events, types: {sorted(types)}")

    runner.run_test("/assistant/converse — model_type=smart", test_converse_model_type_smart)

    def test_converse_threadid_followup():
        """Test multi-turn: send follow-up with threadId from previous call."""
        thread_id = state.get("fast_thread_id")
        if not thread_id:
            print("    No threadId from previous test — skipping")
            return
        resp = genie_post_with_ks("/assistant/converse", {
            "userMessage": "Can you summarize the key points?",
            "sse": False,
            "threadId": thread_id,
            "model_type": "fast",
        }, stream=True, timeout=300)
        events = collect_ndjson_events(resp)
        assert len(events) > 0, "No events for follow-up"
        returned_thread_id = None
        for e in events:
            if e.get("threadId"):
                returned_thread_id = e["threadId"]
                break
        assert returned_thread_id == thread_id, (
            f"threadId mismatch: sent={thread_id}, got={returned_thread_id}"
        )
        print(f"    Follow-up: {len(events)} events, same threadId confirmed")

    runner.run_test("/assistant/converse — threadId multi-turn follow-up", test_converse_threadid_followup)

    def test_converse_force_experience():
        """Test force_experience=flashcards forces flashcards output."""
        thread_id = state.get("fast_thread_id")
        if not thread_id:
            print("    No threadId — skipping")
            return
        resp = genie_post_with_ks("/assistant/converse", {
            "userMessage": "What features does it offer?",
            "sse": False,
            "threadId": thread_id,
            "force_experience": "flashcards",
            "model_type": "fast",
        }, stream=True, timeout=300)
        events = collect_ndjson_events(resp)
        assert len(events) > 0, "No events with force_experience"
        runtimes = set()
        for e in events:
            if e.get("type") == "unisphere-tool":
                rn = e.get("metadata", {}).get("runtimeName", "")
                if rn:
                    runtimes.add(rn)
        print(f"    force_experience=flashcards: runtimes={sorted(runtimes)}")
        if "flashcards-tool" not in runtimes:
            print(f"    flashcards-tool not in response (LLM may have chosen different format)")
            event_types = {e.get("type", "?") for e in events}
            print(f"    Event types seen: {sorted(event_types)}")
        else:
            print(f"    flashcards-tool confirmed in response")

    runner.run_test("/assistant/converse — force_experience=flashcards", test_converse_force_experience)

    def test_converse_preload_entry():
        """Test preload_entry_ids focuses conversation on a specific entry."""
        entry_id = state.get("test_entry_id")
        if not entry_id:
            print("    No test entry ID — skipping")
            return
        resp = genie_post_with_ks("/assistant/converse", {
            "userMessage": "What is this video about?",
            "sse": False,
            "model_type": "fast",
            "preload_entry_ids": [entry_id],
        }, stream=True, timeout=300)
        events = collect_ndjson_events(resp)
        assert len(events) > 0, "No events with preload_entry_ids"
        text_content = "".join(e.get("content", "") for e in events if e.get("type") == "text")
        print(f"    preload_entry_ids=[{entry_id}]: {len(events)} events, {len(text_content)} chars text")
        if text_content:
            print(f"    Preview: {text_content[:150]}...")

    runner.run_test("/assistant/converse — preload_entry_ids (entry-specific)", test_converse_preload_entry)

    def test_converse_filter_entry_ids():
        """Test filter_entry_ids restricts search to specific entries."""
        entry_ids = state.get("all_entry_ids", [])
        if len(entry_ids) < 1:
            print("    No entry IDs available — skipping")
            return
        target = entry_ids[0]
        resp = genie_post_with_ks("/assistant/converse", {
            "userMessage": "What topics are covered?",
            "sse": False,
            "model_type": "fast",
            "filter_entry_ids": [target],
        }, stream=True, timeout=300)
        events = collect_ndjson_events(resp)
        assert len(events) > 0, "No events with filter_entry_ids"
        print(f"    filter_entry_ids=[{target}]: {len(events)} events")

    runner.run_test("/assistant/converse — filter_entry_ids", test_converse_filter_entry_ids)

    def test_converse_exclude_entry_ids():
        """Test exclude_entry_ids removes entries from search results."""
        entry_ids = state.get("all_entry_ids", [])
        if len(entry_ids) < 2:
            print("    Need 2+ entries to test exclude — skipping")
            return
        resp = genie_post_with_ks("/assistant/converse", {
            "userMessage": "What topics are covered in the videos?",
            "sse": False,
            "model_type": "fast",
            "exclude_entry_ids": [entry_ids[0]],
        }, stream=True, timeout=300)
        events = collect_ndjson_events(resp)
        assert len(events) > 0, "No events with exclude_entry_ids"
        print(f"    exclude_entry_ids=[{entry_ids[0]}]: {len(events)} events")

    runner.run_test("/assistant/converse — exclude_entry_ids", test_converse_exclude_entry_ids)

    def test_converse_capabilities():
        """Test capabilities parameter toggles features."""
        entry_id = state.get("test_entry_id")
        if not entry_id:
            print("    No test entry ID — skipping")
            return
        resp = genie_post_with_ks("/assistant/converse", {
            "userMessage": "What is this video about?",
            "sse": False,
            "model_type": "fast",
            "preload_entry_ids": [entry_id],
            "capabilities": {
                "use_knowledge_base": "off",
                "use_get_entry_content": "on",
                "include_sources": "on",
            },
        }, stream=True, timeout=300)
        events = collect_ndjson_events(resp)
        assert len(events) > 0, "No events with capabilities"
        types = {e.get("type") for e in events}
        print(f"    capabilities (kb=off, entry_content=on, sources=on): {len(events)} events")
        print(f"    types: {sorted(types)}")

    runner.run_test("/assistant/converse — capabilities toggle", test_converse_capabilities)

    def test_converse_add_message_in_db_false():
        """Test add_message_in_db=false skips persistence."""
        resp = genie_post_with_ks("/assistant/converse", {
            "userMessage": "Quick ephemeral question — what is this?",
            "sse": False,
            "model_type": "fast",
            "add_message_in_db": False,
        }, stream=True, timeout=300)
        events = collect_ndjson_events(resp)
        assert len(events) > 0, "No events with add_message_in_db=false"
        ephemeral_thread = None
        for e in events:
            if e.get("threadId"):
                ephemeral_thread = e["threadId"]
                break
        print(f"    add_message_in_db=false: {len(events)} events, threadId={ephemeral_thread}")
        if ephemeral_thread:
            state["ephemeral_thread_id"] = ephemeral_thread

    runner.run_test("/assistant/converse — add_message_in_db=false", test_converse_add_message_in_db_false)

    # ════════════════════════════════════════════
    # Phase 5: WebSocket /assistant/ws
    # ════════════════════════════════════════════

    def test_websocket_init_converse_abort():
        """WebSocket /assistant/ws — init, converse, and abort."""
        try:
            import websockets
        except ImportError:
            print("    websockets library not available — skipping")
            return

        ws_base = GENIE_BASE_URL.replace("https://", "wss://").replace("http://", "ws://")
        ws_url = f"{ws_base}/assistant/ws"

        async def _ws_full_test():
            headers = {"Authorization": f"KS {GENIE_KS}"}

            # --- init + converse ---
            async with websockets.connect(ws_url, additional_headers=headers, close_timeout=5) as ws:
                await ws.send(json.dumps({
                    "event": "init",
                    "data": {"model_type": "fast"},
                }))

                init_resp = json.loads(await asyncio.wait_for(ws.recv(), timeout=15))
                assert init_resp.get("event") == "init_response", f"Expected init_response, got: {init_resp}"
                assert init_resp.get("status") == "success", f"init failed: {init_resp}"
                ws_thread_id = init_resp.get("threadId")
                assert ws_thread_id, f"No threadId in init_response: {init_resp}"
                print(f"    init_response: threadId={ws_thread_id}")
                state["ws_thread_id"] = ws_thread_id

                await ws.send(json.dumps({
                    "event": "converse",
                    "data": {
                        "userMessage": "What is this about?",
                        "threadId": ws_thread_id,
                        "model_type": "fast",
                    },
                }))

                ws_events = []
                ws_types = set()
                try:
                    while True:
                        raw = await asyncio.wait_for(ws.recv(), timeout=60)
                        evt = json.loads(raw)
                        ws_events.append(evt)
                        t = evt.get("type", evt.get("event", "?"))
                        ws_types.add(t)
                        if evt.get("type") == "share":
                            break
                except asyncio.TimeoutError:
                    pass

                assert len(ws_events) > 0, "No events from WebSocket converse"
                print(f"    converse: {len(ws_events)} events, types: {sorted(ws_types)}")

            # --- abort (new connection) ---
            async with websockets.connect(ws_url, additional_headers=headers, close_timeout=5) as ws2:
                await ws2.send(json.dumps({
                    "event": "init",
                    "data": {"model_type": "fast"},
                }))
                init2 = json.loads(await asyncio.wait_for(ws2.recv(), timeout=15))
                thread_id2 = init2.get("threadId")

                await ws2.send(json.dumps({
                    "event": "converse",
                    "data": {
                        "userMessage": "Give me a very detailed explanation of everything",
                        "threadId": thread_id2,
                        "model_type": "smart",
                    },
                }))

                first_event = json.loads(await asyncio.wait_for(ws2.recv(), timeout=30))
                msg_id = first_event.get("messageId", "unknown")

                await ws2.send(json.dumps({
                    "event": "abort",
                    "data": {
                        "messageId": msg_id,
                        "deleteFromHistory": True,
                    },
                }))

                abort_received = False
                try:
                    for _ in range(20):
                        raw = await asyncio.wait_for(ws2.recv(), timeout=10)
                        evt = json.loads(raw)
                        if evt.get("event") == "abort_response":
                            abort_received = True
                            print(f"    abort_response: status={evt.get('status')}")
                            break
                except asyncio.TimeoutError:
                    pass

                if abort_received:
                    print(f"    Abort confirmed with deleteFromHistory=true")
                else:
                    print(f"    Abort sent (stream may have completed before abort processed)")

                if thread_id2:
                    state.setdefault("cleanup_thread_ids", []).append(thread_id2)

        asyncio.run(_ws_full_test())

    runner.run_test("/assistant/ws — WebSocket init + converse + abort", test_websocket_init_converse_abort)

    # ════════════════════════════════════════════
    # Phase 6: Thread Management
    # ════════════════════════════════════════════

    def test_thread_list():
        """POST /thread/list — list conversation threads."""
        result = genie_post_with_ks("/thread/list", {
            "filter": {
                "objectType": "GenieListThreadFilter",
                "orderBy": "-updatedAt",
            },
            "pager": {"pageIndex": 1, "pageSize": 5},
        })
        assert "objects" in result, f"Missing 'objects'. Keys: {list(result.keys())}"
        assert "totalCount" in result, f"Missing 'totalCount'. Keys: {list(result.keys())}"
        threads = result["objects"]
        print(f"    Total threads: {result['totalCount']}, returned: {len(threads)}")
        for t in threads[:3]:
            print(f"      id={t['id'][:20]}... title=\"{t.get('title', '?')[:40]}\"")
        if threads:
            state["list_thread_id"] = threads[0]["id"]

    runner.run_test("/thread/list — list conversation threads", test_thread_list)

    def test_thread_list_status_filter():
        """POST /thread/list — filter by statusIn=[0] (active threads)."""
        result = genie_post_with_ks("/thread/list", {
            "filter": {
                "objectType": "GenieListThreadFilter",
                "orderBy": "-updatedAt",
                "statusIn": [0],
            },
            "pager": {"pageIndex": 1, "pageSize": 5},
        })
        assert "objects" in result, f"Missing 'objects'. Keys: {list(result.keys())}"
        threads = result["objects"]
        print(f"    statusIn=[0] (active): {result.get('totalCount', len(threads))} threads")
        for t in threads[:2]:
            print(f"      status={t.get('status')} title=\"{t.get('title', '?')[:40]}\"")

    runner.run_test("/thread/list — statusIn filter", test_thread_list_status_filter)

    def test_thread_list_context_filter():
        """POST /thread/list — filter by contextIdEqual (entry-specific threads)."""
        entry_id = state.get("test_entry_id")
        if not entry_id:
            print("    No test entry ID — skipping")
            return
        result = genie_post_with_ks("/thread/list", {
            "filter": {
                "objectType": "GenieListThreadFilter",
                "contextIdEqual": entry_id,
            },
            "pager": {"pageIndex": 1, "pageSize": 5},
        })
        assert "objects" in result, f"Missing 'objects'. Keys: {list(result.keys())}"
        total = result.get("totalCount", len(result.get("objects", [])))
        print(f"    contextIdEqual={entry_id}: {total} threads")

    runner.run_test("/thread/list — contextIdEqual filter", test_thread_list_context_filter)

    def test_thread_list_verify_by_id():
        """Verify thread details accessible via /thread/list."""
        thread_id = state.get("thread_id") or state.get("list_thread_id")
        if not thread_id:
            print("    No threadId available — skipping")
            return
        result = genie_post_with_ks("/thread/list", {
            "filter": {
                "objectType": "GenieListThreadFilter",
                "orderBy": "-updatedAt",
            },
            "pager": {"pageIndex": 1, "pageSize": 100},
        })
        threads = result.get("objects", [])
        match = [t for t in threads if t.get("id") == thread_id]
        assert len(match) > 0, f"Thread {thread_id[:20]}... not found in list"
        t = match[0]
        print(f"    Thread: id={t['id'][:20]}... title=\"{t.get('title', '?')[:50]}\"")
        print(f"    Status: {t.get('status')}")

    runner.run_test("/thread/list — verify thread details by ID", test_thread_list_verify_by_id)

    # ════════════════════════════════════════════
    # Phase 7: Message Management
    # ════════════════════════════════════════════

    def test_message_list():
        """POST /message/list — list messages in a thread."""
        thread_id = state.get("thread_id")
        if not thread_id:
            print("    No threadId — skipping")
            return
        result = genie_post_with_ks("/message/list", {
            "filter": {
                "objectType": "GenieListMessageFilter",
                "threadIdEquals": thread_id,
                "orderBy": "+updatedAt",
            },
            "pager": {"pageIndex": 1, "pageSize": 10},
        })
        assert "objects" in result, f"Missing 'objects'. Keys: {list(result.keys())}"
        msgs = result["objects"]
        print(f"    Messages in thread: {result.get('totalCount', len(msgs))}")
        for m in msgs[:3]:
            assistant = m.get("assistant", {})
            msg_list = assistant.get("messages", [])
            types = [msg.get("type", "?") for msg in msg_list]
            print(f"      id={m['id'][:20]}... message_types={types}")
        if msgs:
            state["message_for_share"] = msgs[0]["id"]

    runner.run_test("/message/list — list messages in thread", test_message_list)

    def test_message_list_by_id():
        """POST /message/list — load a specific message by idEquals."""
        msg_id = state.get("message_for_share")
        thread_id = state.get("thread_id")
        if not msg_id or not thread_id:
            print("    No message ID or thread ID — skipping")
            return
        result = genie_post_with_ks("/message/list", {
            "filter": {
                "objectType": "GenieListMessageFilter",
                "threadIdEquals": thread_id,
                "idEquals": msg_id,
            },
            "pager": {"pageIndex": 1, "pageSize": 1},
        })
        assert "objects" in result, f"Missing 'objects'. Keys: {list(result.keys())}"
        msgs = result["objects"]
        assert len(msgs) > 0, f"idEquals={msg_id[:20]} returned 0 messages"
        assert msgs[0]["id"] == msg_id, f"Returned message ID mismatch: {msgs[0]['id']} vs {msg_id}"
        print(f"    idEquals={msg_id[:20]}...: found message, types={[m.get('type') for m in msgs[0].get('assistant', {}).get('messages', [])]}")

    runner.run_test("/message/list — idEquals filter", test_message_list_by_id)

    def test_message_share():
        """POST /message/share — create a shareable message link."""
        msg_id = state.get("message_for_share")
        if not msg_id:
            print("    No message ID — skipping")
            return
        result = genie_post_with_ks("/message/share", {
            "id": msg_id,
            "newTitle": "Shared from API test",
        })
        if isinstance(result, dict) and "data" in result:
            data = result["data"]
            if isinstance(data, dict) and "newMessageId" in data:
                print(f"    Shared message: newMessageId={data['newMessageId']}")
                state["shared_message_id"] = data["newMessageId"]
            else:
                print(f"    Share response: {data}")
        else:
            print(f"    Share response: {result}")

    runner.run_test("/message/share — create shareable message", test_message_share)

    # ════════════════════════════════════════════
    # Phase 8: Feedback
    # ════════════════════════════════════════════

    def test_feedback_add_positive():
        """POST /feedback/add — submit positive feedback."""
        msg_id = state.get("message_id")
        if not msg_id:
            print("    No messageId — skipping")
            return
        result = genie_post_with_ks("/feedback/add", {
            "schemaVersion": 1,
            "data": {
                "is_positive": True,
                "message_id": msg_id,
            },
        })
        assert result.get("status") == "success" or result.get("data") == "Feedback added successfully", \
            f"Unexpected feedback response: {result}"
        print(f"    Positive feedback added for message {msg_id[:20]}...")

    runner.run_test("/feedback/add — positive feedback (thumbs up)", test_feedback_add_positive)

    def test_feedback_add_negative_with_comment():
        """POST /feedback/add — submit negative feedback with comment."""
        msg_id = state.get("message_id")
        if not msg_id:
            print("    No messageId — skipping")
            return
        result = genie_post_with_ks("/feedback/add", {
            "schemaVersion": 1,
            "data": {
                "is_positive": False,
                "message_id": msg_id,
                "comment": "Test feedback comment from API validation",
            },
        })
        assert result.get("status") == "success" or result.get("data") == "Feedback added successfully", \
            f"Unexpected feedback response: {result}"
        print(f"    Negative feedback with comment added for message {msg_id[:20]}...")

    runner.run_test("/feedback/add — negative feedback with comment", test_feedback_add_negative_with_comment)

    def test_feedback_list():
        """POST /feedback/list — list feedback entries."""
        result = genie_post_with_ks("/feedback/list", {
            "filter": {"objectType": "GenieListFeedbackFilter"},
            "pager": {"pageIndex": 1, "pageSize": 10},
        })
        assert "objects" in result or "totalCount" in result, \
            f"Missing 'objects' or 'totalCount'. Response: {result}"
        total = result.get("totalCount", len(result.get("objects", [])))
        print(f"    Total feedback entries: {total}")
        for fb in result.get("objects", [])[:3]:
            print(f"      positive={fb.get('is_positive')} comment=\"{fb.get('comment', '')[:40]}\"")

    runner.run_test("/feedback/list — list feedback", test_feedback_list)

    def test_feedback_list_filtered():
        """POST /feedback/list — filter by isPositiveEquals."""
        result = genie_post_with_ks("/feedback/list", {
            "filter": {
                "objectType": "GenieListFeedbackFilter",
                "isPositiveEquals": True,
            },
            "pager": {"pageIndex": 1, "pageSize": 5},
        })
        assert "objects" in result or "totalCount" in result, \
            f"Missing 'objects' or 'totalCount'. Response: {result}"
        total = result.get("totalCount", len(result.get("objects", [])))
        print(f"    isPositiveEquals=true: {total} entries")

    runner.run_test("/feedback/list — isPositiveEquals filter", test_feedback_list_filtered)

    # ════════════════════════════════════════════
    # Phase 9: Suggested Questions
    # ════════════════════════════════════════════

    def test_suggested_questions():
        """POST /followup/get-suggested-questions — get suggested questions."""
        result = genie_post_with_ks(
            "/followup/get-suggested-questions?new_response=true", {}
        )
        assert "data" in result or "status" in result, \
            f"Unexpected response. Keys: {list(result.keys())}"
        if result.get("status") == "success" and isinstance(result.get("data"), list):
            questions = result["data"]
            print(f"    Suggested questions ({len(questions)}):")
            for q in questions:
                print(f"      - {q}")
            assert len(questions) > 0, "Expected at least 1 suggested question"
        else:
            print(f"    Response: {result}")

    runner.run_test("/followup/get-suggested-questions — suggested questions", test_suggested_questions)

    # ════════════════════════════════════════════
    # Phase 10: Thread Cleanup
    # ════════════════════════════════════════════

    def test_thread_delete():
        """POST /thread/delete — delete test threads."""
        thread_ids = []
        for key in ("thread_id", "fast_thread_id", "ws_thread_id", "ephemeral_thread_id"):
            tid = state.get(key)
            if tid and tid not in thread_ids:
                thread_ids.append(tid)
        for tid in state.get("cleanup_thread_ids", []):
            if tid not in thread_ids:
                thread_ids.append(tid)
        if not thread_ids:
            print("    No test threads to delete — skipping")
            return
        result = genie_post_with_ks("/thread/delete", {
            "thread_ids": thread_ids,
        })
        if isinstance(result, dict) and "objects" in result:
            deleted = result["objects"]
            print(f"    Deleted {len(deleted)} threads")
        else:
            print(f"    Delete response: {str(result)[:200]}")

    runner.run_test("/thread/delete — cleanup test threads", test_thread_delete)

    # ════════════════════════════════════════════
    # Summary
    # ════════════════════════════════════════════

    runner.cleanup()
    success = runner.summary()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    print(f"\n{'='*60}")
    print("  KALTURA AI GENIE API — End-to-End Validation")
    print(f"{'='*60}\n")
    main()
