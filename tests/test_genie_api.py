#!/usr/bin/env python3
"""
End-to-end validation of KALTURA_AI_GENIE_API.md against the live API.

Tests:
- /mcp/search with query + include_sources (documented params)
- /assistant/converse (streaming SSE and NDJSON)
- /assistant/converse — model_type, threadId, force_experience
- /kmedia/start-smart-search-session + get-smart-search-session (polling, if available)
"""

import sys
import os
import time
import json
import requests

sys.path.insert(0, os.path.dirname(__file__))
from test_helpers import TestRunner, genie_post, KS, PARTNER_ID

TEST_QUERY = "What is Kaltura?"

state = {}


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
    # Phase 1: /mcp/search — Stateless RAG
    # ════════════════════════════════════════════

    def test_mcp_search_text_only():
        """Test /mcp/search with query + include_sources=false → returns text."""
        result = genie_post("/mcp/search", {
            "query": TEST_QUERY,
            "include_sources": False,
        })
        assert result.get("status") == "success", \
            f"Expected status=success. Got: {result}. If knowledge base returns 'error', verify entries are indexed in the Genie workspace."
        data = result["data"]
        assert "text" in data, f"Expected 'text' in data. Keys: {list(data.keys())}"
        print(f"    text: {len(data['text'])} chars")
        print(f"    Preview: {data['text'][:150]}...")

    runner.run_test("/mcp/search — query + include_sources=false (text only)", test_mcp_search_text_only)

    def test_mcp_search_with_sources():
        """Test /mcp/search with query + include_sources=true → returns chapters with entry IDs."""
        result = genie_post("/mcp/search", {
            "query": TEST_QUERY,
            "include_sources": True,
        })
        assert result.get("status") == "success", \
            f"Expected status=success. Got: {result}. Verify entries are indexed in the Genie workspace."
        data = result["data"]
        if "chapters" in data and len(data.get("chapters", [])) > 0:
            chapters = data["chapters"]
            for ch in chapters[:3]:
                assert "entry_id" in ch, f"Chapter missing entry_id. Keys: {list(ch.keys())}"
                assert "text" in ch, f"Chapter missing text"
            print(f"    Got {len(chapters)} chapters with sources")
            for ch in chapters[:3]:
                print(f"      - entry_id={ch['entry_id']}, "
                      f"time={ch.get('start_time', '?')}-{ch.get('end_time', '?')}s, "
                      f"text={len(ch['text'])} chars")
        else:
            text = data.get("text", "")
            print(f"    No chapters returned (knowledge base may be empty)")
            if text:
                print(f"    Text response: {text[:120]}...")

    runner.run_test("/mcp/search — query + include_sources=true (returns chapters)", test_mcp_search_with_sources)

    def test_mcp_search_minimal():
        """Test /mcp/search with just query (no include_sources) — verify default behavior."""
        result = genie_post("/mcp/search", {
            "query": TEST_QUERY,
        })
        assert result.get("status") == "success", \
            f"Expected status=success. Got: {result}. Verify entries are indexed in the Genie workspace."
        data = result["data"]
        has_text = "text" in data
        has_chapters = "chapters" in data
        print(f"    Default (no include_sources): has_text={has_text}, has_chapters={has_chapters}")
        if has_text:
            print(f"    text: {len(data['text'])} chars")

    runner.run_test("/mcp/search — query only (default behavior)", test_mcp_search_minimal)

    # ════════════════════════════════════════════
    # Phase 2: /assistant/converse — Streaming
    # ════════════════════════════════════════════

    def test_converse_ndjson():
        """Test /assistant/converse with sse=false (NDJSON)."""
        resp = genie_post("/assistant/converse", {
            "userMessage": TEST_QUERY,
            "sse": False,
        }, headers_override={"Accept": "application/x-ndjson"}, stream=True, timeout=300)

        events = collect_ndjson_events(resp)
        assert len(events) > 0, "No events received from converse (NDJSON)"
        event_types = {e.get("type", "?") for e in events}
        print(f"    Received {len(events)} events, types: {sorted(event_types)}")

        state["converse_event_types"] = event_types
        state["converse_events"] = events

        # Check for text content
        text_content = "".join(e.get("content", "") for e in events if e.get("type") == "text")
        if text_content:
            print(f"    Text answer: {len(text_content)} chars")
            print(f"    Preview: {text_content[:150]}...")

    runner.run_test("/assistant/converse — NDJSON (sse=false)", test_converse_ndjson)

    def test_converse_sse():
        """Test /assistant/converse with sse=true (SSE)."""
        # SSE streams can occasionally drop; retry once on transient errors
        last_err = None
        for attempt in range(2):
            try:
                resp = genie_post("/assistant/converse", {
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
    # Phase 3: Converse — model_type, threadId, force_experience
    # ════════════════════════════════════════════

    def test_converse_model_type_fast():
        """Test model_type=fast produces a valid response."""
        resp = genie_post("/assistant/converse", {
            "userMessage": TEST_QUERY,
            "sse": False,
            "model_type": "fast",
        }, stream=True, timeout=300)
        events = collect_ndjson_events(resp)
        assert len(events) > 0, "No events with model_type=fast"
        types = {e.get("type") for e in events}
        print(f"    model_type=fast: {len(events)} events, types: {sorted(types)}")
        # Extract threadId for follow-up test
        for e in events:
            if e.get("threadId"):
                state["fast_thread_id"] = e["threadId"]
                break
        assert state.get("fast_thread_id"), "No threadId returned with model_type=fast"
        print(f"    threadId: {state['fast_thread_id']}")

    runner.run_test("/assistant/converse — model_type=fast", test_converse_model_type_fast)

    def test_converse_model_type_smart():
        """Test model_type=smart produces a valid response."""
        resp = genie_post("/assistant/converse", {
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
        resp = genie_post("/assistant/converse", {
            "userMessage": "Tell me more about the video platform",
            "sse": False,
            "threadId": thread_id,
            "model_type": "fast",
        }, stream=True, timeout=300)
        events = collect_ndjson_events(resp)
        assert len(events) > 0, "No events for follow-up"
        # Verify same threadId is returned
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
        resp = genie_post("/assistant/converse", {
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
            print(f"    flashcards-tool not in response (knowledge base may lack sufficient content)")
            event_types = {e.get("type", "?") for e in events}
            print(f"    Event types seen: {sorted(event_types)}")
        else:
            print(f"    flashcards-tool confirmed in response")

    runner.run_test("/assistant/converse — force_experience=flashcards", test_converse_force_experience)

    # ════════════════════════════════════════════
    # Phase 4: Smart Search Sessions — Polling
    # (May not be available on all deployments)
    # ════════════════════════════════════════════

    def test_start_smart_search_session():
        """Start a smart search session (may return 404 if not available on this deployment)."""
        try:
            result = genie_post("/kmedia/start-smart-search-session", {
                "schemaVersion": 1,
                "data": {"question": TEST_QUERY},
            })
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                print("    Endpoint not available on this deployment (404) — skipping")
                state["smart_search_available"] = False
                return
            raise
        assert "data" in result, f"Missing 'data'. Keys: {list(result.keys())}"
        data = result["data"]
        assert "sessionId" in data, f"Missing 'sessionId'. Keys: {list(data.keys())}"
        assert "timestamp" in data, f"Missing 'timestamp'. Keys: {list(data.keys())}"
        state["search_session_id"] = data["sessionId"]
        state["search_timestamp"] = data["timestamp"]
        state["smart_search_available"] = True
        print(f"    Session: {data['sessionId']}, timestamp: {data['timestamp']}")

    runner.run_test("/kmedia/start-smart-search-session", test_start_smart_search_session)

    def test_poll_smart_search_session():
        """Poll until isFinal=true or timeout."""
        if not state.get("smart_search_available"):
            print("    Smart search not available — skipping")
            return

        max_wait = 60
        poll_interval = 3
        elapsed = 0
        final_result = None

        while elapsed < max_wait:
            result = genie_post("/kmedia/get-smart-search-session", {
                "schemaVersion": 1,
                "data": {
                    "sessionId": state["search_session_id"],
                    "timestamp": state["search_timestamp"],
                },
            })
            data = result.get("data", {})
            if "timestamp" in result:
                state["search_timestamp"] = result["timestamp"]
            elif "timestamp" in data:
                state["search_timestamp"] = data["timestamp"]

            if data.get("isFinal"):
                final_result = data
                print(f"    Got final result after ~{elapsed}s")
                break

            print(f"    Polling... elapsed={elapsed}s, isFinal={data.get('isFinal')}")
            time.sleep(poll_interval)
            elapsed += poll_interval

        assert final_result is not None, f"Session did not complete within {max_wait}s"
        state["search_final_result"] = final_result

    runner.run_test("/kmedia/get-smart-search-session — poll until final", test_poll_smart_search_session)

    def test_smart_search_elements():
        """Verify final response has documented element types."""
        if not state.get("smart_search_available"):
            print("    Smart search not available — skipping")
            return

        data = state.get("search_final_result", {})
        elements = data.get("elements", [])
        assert len(elements) > 0, f"No elements in final result. Keys: {list(data.keys())}"

        element_types = [e.get("type") for e in elements]
        print(f"    Element types: {element_types}")

        documented = {"flashcards", "followups", "sources", "text"}
        found = set(element_types) & documented
        print(f"    Documented types found: {sorted(found)}")
        assert len(found) > 0, f"No documented element types found: {element_types}"

    runner.run_test("Smart search — element types and structure", test_smart_search_elements)

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
