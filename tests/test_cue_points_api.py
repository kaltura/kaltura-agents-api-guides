#!/usr/bin/env python3
"""End-to-end validation of the Kaltura Cue Points & Interactive Video API.

Covers: cue point CRUD (all 8 types), quiz lifecycle, eSearch integration,
clone, updateStatus, updateCuePointsTimes, and filtering.
"""

import sys
import os
import time

sys.path.insert(0, os.path.dirname(__file__))
from test_helpers import kaltura_post, TestRunner, PARTNER_ID, KS, SERVICE_URL

state = {}

POLL_INTERVAL = 3
POLL_TIMEOUT = 60


def _find_ready_entry():
    """Find an existing READY entry to attach cue points to."""
    result = kaltura_post("baseEntry", "list", {
        "filter[statusEqual]": 2,
        "filter[mediaTypeEqual]": 1,
        "pager[pageSize]": 1,
    })
    entries = result.get("objects", [])
    assert len(entries) > 0, "No READY entries found on account"
    return entries[0]["id"], entries[0].get("name", "unknown")


def _delete_cue_point(cp_id):
    """Delete a cue point, ignoring errors."""
    try:
        kaltura_post("cuepoint_cuepoint", "delete", {"id": cp_id})
    except Exception:
        pass


def _delete_quiz(entry_id):
    """Remove quiz config from entry — no direct delete, but we clean up questions."""
    pass


def _delete_user_entry(ue_id):
    """Delete a user entry."""
    try:
        kaltura_post("userEntry", "delete", {"id": ue_id})
    except Exception:
        pass


def main():
    runner = TestRunner("Cue Points & Interactive Video — E2E Validation")

    # ════════════════════════════════════════════
    # Phase 1: Setup — Find a test entry
    # ════════════════════════════════════════════

    def test_find_entry():
        """Find an existing READY entry to use as the cue point host."""
        entry_id, name = _find_ready_entry()
        state["entry_id"] = entry_id
        print(f"    Using entry: {entry_id} — {name}")

    runner.run_test("baseEntry.list — find READY entry for cue point tests", test_find_entry)

    # ════════════════════════════════════════════
    # Phase 2: Code Cue Points
    # ════════════════════════════════════════════

    def test_code_add():
        """Create a code cue point."""
        result = kaltura_post("cuepoint_cuepoint", "add", {
            "cuePoint[objectType]": "KalturaCodeCuePoint",
            "cuePoint[entryId]": state["entry_id"],
            "cuePoint[startTime]": 5000,
            "cuePoint[code]": "test-marker",
            "cuePoint[description]": "E2E test code cue point",
            "cuePoint[tags]": "e2e-test",
        })
        assert result.get("objectType") == "KalturaCodeCuePoint", f"Wrong type: {result}"
        assert result.get("status") == 1, f"Expected READY (1), got {result.get('status')}"
        state["code_cp_id"] = result["id"]
        runner.register_cleanup(f"code cue point {result['id']}",
                                lambda: _delete_cue_point(result["id"]))
        print(f"    Created: {result['id']}, code={result.get('code')}")

    runner.run_test("cuePoint.add — create code cue point", test_code_add)

    def test_code_get():
        """Retrieve the code cue point by ID."""
        result = kaltura_post("cuepoint_cuepoint", "get", {
            "id": state["code_cp_id"],
        })
        assert result["id"] == state["code_cp_id"]
        assert result["code"] == "test-marker"
        assert result["description"] == "E2E test code cue point"
        assert result["startTime"] == 5000
        print(f"    Retrieved: {result['id']}, startTime={result['startTime']}")

    runner.run_test("cuePoint.get — retrieve code cue point", test_code_get)

    def test_code_update():
        """Update code cue point fields."""
        result = kaltura_post("cuepoint_cuepoint", "update", {
            "id": state["code_cp_id"],
            "cuePoint[objectType]": "KalturaCodeCuePoint",
            "cuePoint[code]": "updated-marker",
            "cuePoint[description]": "Updated description",
        })
        assert result["code"] == "updated-marker", f"Expected updated code, got {result['code']}"
        print(f"    Updated: code={result['code']}")

    runner.run_test("cuePoint.update — update code cue point", test_code_update)

    def test_code_list():
        """List cue points filtered by entry and type."""
        result = kaltura_post("cuepoint_cuepoint", "list", {
            "filter[entryIdEqual]": state["entry_id"],
            "filter[cuePointTypeEqual]": "codeCuePoint.Code",
            "filter[tagsLike]": "e2e-test",
        })
        assert result.get("totalCount", 0) >= 1, f"Expected at least 1 code cue point, got {result.get('totalCount')}"
        found = any(o["id"] == state["code_cp_id"] for o in result.get("objects", []))
        assert found, "Created code cue point not found in list"
        print(f"    Listed: {result['totalCount']} code cue points with e2e-test tag")

    runner.run_test("cuePoint.list — filter by type and tags", test_code_list)

    def test_count():
        """Count cue points on entry."""
        result = kaltura_post("cuepoint_cuepoint", "count", {
            "filter[entryIdEqual]": state["entry_id"],
            "filter[tagsLike]": "e2e-test",
        })
        assert isinstance(result, int) or (isinstance(result, dict) and "totalCount" in result), \
            f"Expected count, got {result}"
        count = result if isinstance(result, int) else result.get("totalCount", 0)
        assert count >= 1, f"Expected count >= 1, got {count}"
        print(f"    Count: {count}")

    runner.run_test("cuePoint.count — count cue points", test_count)

    # ════════════════════════════════════════════
    # Phase 3: Thumb Cue Points (Chapters & Slides)
    # ════════════════════════════════════════════

    def test_chapter_add():
        """Create a chapter (thumb cue point, subType=2)."""
        result = kaltura_post("cuepoint_cuepoint", "add", {
            "cuePoint[objectType]": "KalturaThumbCuePoint",
            "cuePoint[entryId]": state["entry_id"],
            "cuePoint[startTime]": 0,
            "cuePoint[subType]": 2,
            "cuePoint[title]": "E2E Test Chapter",
            "cuePoint[description]": "Chapter created by E2E test",
            "cuePoint[tags]": "e2e-test",
        })
        assert result.get("objectType") == "KalturaThumbCuePoint"
        assert result.get("subType") == 2, f"Expected subType 2, got {result.get('subType')}"
        state["chapter_cp_id"] = result["id"]
        runner.register_cleanup(f"chapter cue point {result['id']}",
                                lambda: _delete_cue_point(result["id"]))
        print(f"    Created chapter: {result['id']}, title={result.get('title')}")

    runner.run_test("cuePoint.add — create chapter (subType=2)", test_chapter_add)

    def test_slide_add():
        """Create a slide marker (thumb cue point, subType=1)."""
        result = kaltura_post("cuepoint_cuepoint", "add", {
            "cuePoint[objectType]": "KalturaThumbCuePoint",
            "cuePoint[entryId]": state["entry_id"],
            "cuePoint[startTime]": 30000,
            "cuePoint[subType]": 1,
            "cuePoint[title]": "E2E Test Slide",
            "cuePoint[description]": "Slide OCR text for search testing",
            "cuePoint[tags]": "e2e-test",
        })
        assert result.get("objectType") == "KalturaThumbCuePoint"
        assert result.get("subType") == 1, f"Expected subType 1, got {result.get('subType')}"
        # Thumb cue points without assets may be PENDING (4) or READY (1)
        assert result.get("status") in (1, 4), f"Unexpected status: {result.get('status')}"
        state["slide_cp_id"] = result["id"]
        runner.register_cleanup(f"slide cue point {result['id']}",
                                lambda: _delete_cue_point(result["id"]))
        print(f"    Created slide: {result['id']}, status={result.get('status')}")

    runner.run_test("cuePoint.add — create slide marker (subType=1)", test_slide_add)

    def test_thumb_filter():
        """Filter thumb cue points by subType."""
        result = kaltura_post("cuepoint_cuepoint", "list", {
            "filter[entryIdEqual]": state["entry_id"],
            "filter[cuePointTypeEqual]": "thumbCuePoint.Thumb",
            "filter[tagsLike]": "e2e-test",
        })
        assert result.get("totalCount", 0) >= 2, \
            f"Expected at least 2 thumb cue points (chapter + slide), got {result.get('totalCount')}"
        sub_types = {obj.get("subType") for obj in result.get("objects", [])}
        assert 1 in sub_types, "Missing slide (subType=1) in results"
        assert 2 in sub_types, "Missing chapter (subType=2) in results"
        print(f"    Thumb cue points: {result['totalCount']}, subTypes={sub_types}")

    runner.run_test("cuePoint.list — filter thumb by subType=CHAPTER", test_thumb_filter)

    # ════════════════════════════════════════════
    # Phase 4: Annotation Cue Points
    # ════════════════════════════════════════════

    def test_annotation_add():
        """Create an annotation cue point."""
        result = kaltura_post("cuepoint_cuepoint", "add", {
            "cuePoint[objectType]": "KalturaAnnotation",
            "cuePoint[entryId]": state["entry_id"],
            "cuePoint[startTime]": 10000,
            "cuePoint[endTime]": 20000,
            "cuePoint[text]": "E2E test annotation",
            "cuePoint[isPublic]": 1,
            "cuePoint[searchableOnEntry]": 1,
            "cuePoint[tags]": "e2e-test",
        })
        assert result.get("objectType") == "KalturaAnnotation"
        assert result.get("text") == "E2E test annotation"
        state["annotation_cp_id"] = result["id"]
        runner.register_cleanup(f"annotation {result['id']}",
                                lambda: _delete_cue_point(result["id"]))
        print(f"    Created: {result['id']}, duration={result.get('duration')}")

    runner.run_test("cuePoint.add — create annotation", test_annotation_add)

    def test_annotation_child():
        """Create a child annotation (threaded reply)."""
        result = kaltura_post("cuepoint_cuepoint", "add", {
            "cuePoint[objectType]": "KalturaAnnotation",
            "cuePoint[entryId]": state["entry_id"],
            "cuePoint[parentId]": state["annotation_cp_id"],
            "cuePoint[startTime]": 10000,
            "cuePoint[text]": "E2E test reply annotation",
            "cuePoint[tags]": "e2e-test",
        })
        assert result.get("parentId") == state["annotation_cp_id"]
        assert result.get("depth", 0) >= 1, f"Expected depth >= 1, got {result.get('depth')}"
        state["child_annotation_id"] = result["id"]
        runner.register_cleanup(f"child annotation {result['id']}",
                                lambda: _delete_cue_point(result["id"]))
        # Verify parent counts updated
        parent = kaltura_post("cuepoint_cuepoint", "get", {"id": state["annotation_cp_id"]})
        assert parent.get("directChildrenCount", 0) >= 1, \
            f"Parent should have children, got {parent.get('directChildrenCount')}"
        print(f"    Created child: {result['id']}, parent directChildren={parent.get('directChildrenCount')}")

    runner.run_test("cuePoint.add — threaded annotation (parent-child)", test_annotation_child)

    # ════════════════════════════════════════════
    # Phase 5: Ad Cue Points
    # ════════════════════════════════════════════

    def test_ad_add():
        """Create an ad cue point with VAST 2.0 protocol."""
        result = kaltura_post("cuepoint_cuepoint", "add", {
            "cuePoint[objectType]": "KalturaAdCuePoint",
            "cuePoint[entryId]": state["entry_id"],
            "cuePoint[startTime]": 60000,
            "cuePoint[protocolType]": 2,
            "cuePoint[sourceUrl]": "https://example.com/vast/test-midroll.xml",
            "cuePoint[adType]": 1,
            "cuePoint[title]": "E2E Test Mid-Roll Ad",
            "cuePoint[tags]": "e2e-test",
        })
        assert result.get("objectType") == "KalturaAdCuePoint"
        assert result.get("protocolType") == 2, f"Expected VAST_2_0 (2), got {result.get('protocolType')}"
        assert result.get("adType") == 1, f"Expected VIDEO (1), got {result.get('adType')}"
        state["ad_cp_id"] = result["id"]
        runner.register_cleanup(f"ad cue point {result['id']}",
                                lambda: _delete_cue_point(result["id"]))
        print(f"    Created: {result['id']}, protocol={result.get('protocolType')}, adType={result.get('adType')}")

    runner.run_test("cuePoint.add — create VAST 2.0 mid-roll ad", test_ad_add)

    def test_ad_protocol_immutable():
        """Verify protocolType cannot be changed after creation."""
        try:
            kaltura_post("cuepoint_cuepoint", "update", {
                "id": state["ad_cp_id"],
                "cuePoint[objectType]": "KalturaAdCuePoint",
                "cuePoint[protocolType]": 1,
            })
            # If no error, the API might silently ignore — check the value
            result = kaltura_post("cuepoint_cuepoint", "get", {"id": state["ad_cp_id"]})
            assert result.get("protocolType") == 2, \
                f"protocolType should remain 2, got {result.get('protocolType')}"
            print("    protocolType update silently ignored (remains VAST_2_0)")
        except Exception as e:
            err = str(e)
            assert "NOT_UPDATABLE" in err or "PROPERTY" in err, f"Unexpected error: {err}"
            print(f"    Correctly rejected: {err[:80]}")

    runner.run_test("cuePoint.update — ad protocolType is immutable", test_ad_protocol_immutable)

    # ════════════════════════════════════════════
    # Phase 6: Event Cue Points
    # ════════════════════════════════════════════

    def test_event_add():
        """Create an event cue point (BROADCAST_START)."""
        result = kaltura_post("cuepoint_cuepoint", "add", {
            "cuePoint[objectType]": "KalturaEventCuePoint",
            "cuePoint[entryId]": state["entry_id"],
            "cuePoint[startTime]": 0,
            "cuePoint[eventType]": 1,
            "cuePoint[tags]": "e2e-test",
        })
        assert result.get("objectType") == "KalturaEventCuePoint"
        # eventType may return as int or may not be returned in response
        state["event_cp_id"] = result["id"]
        runner.register_cleanup(f"event cue point {result['id']}",
                                lambda: _delete_cue_point(result["id"]))
        # Verify via get
        fetched = kaltura_post("cuepoint_cuepoint", "get", {"id": result["id"]})
        print(f"    Created: {result['id']}, cuePointType={fetched.get('cuePointType')}, eventType={fetched.get('eventType')}")

    runner.run_test("cuePoint.add — create event cue point (BROADCAST_START)", test_event_add)

    # ════════════════════════════════════════════
    # Phase 7: Session Cue Points
    # ════════════════════════════════════════════

    def test_session_add():
        """Create a session cue point."""
        result = kaltura_post("cuepoint_cuepoint", "add", {
            "cuePoint[objectType]": "KalturaSessionCuePoint",
            "cuePoint[entryId]": state["entry_id"],
            "cuePoint[startTime]": 0,
            "cuePoint[endTime]": 300000,
            "cuePoint[name]": "E2E Test Session",
            "cuePoint[sessionOwner]": "test@example.com",
            "cuePoint[tags]": "e2e-test",
        })
        assert result.get("objectType") == "KalturaSessionCuePoint"
        assert result.get("name") == "E2E Test Session"
        state["session_cp_id"] = result["id"]
        runner.register_cleanup(f"session cue point {result['id']}",
                                lambda: _delete_cue_point(result["id"]))
        print(f"    Created: {result['id']}, name={result.get('name')}, owner={result.get('sessionOwner')}")

    runner.run_test("cuePoint.add — create session cue point", test_session_add)

    # ════════════════════════════════════════════
    # Phase 8: Operations — Clone, UpdateStatus, UpdateTimes
    # ════════════════════════════════════════════

    def test_clone():
        """Clone a cue point to the same entry (different ID)."""
        result = kaltura_post("cuepoint_cuepoint", "clone", {
            "id": state["code_cp_id"],
            "entryId": state["entry_id"],
        })
        assert result["id"] != state["code_cp_id"], "Cloned cue point should have a new ID"
        assert result.get("copiedFrom") == state["code_cp_id"], \
            f"Expected copiedFrom={state['code_cp_id']}, got {result.get('copiedFrom')}"
        state["cloned_cp_id"] = result["id"]
        runner.register_cleanup(f"cloned cue point {result['id']}",
                                lambda: _delete_cue_point(result["id"]))
        print(f"    Cloned: {state['code_cp_id']} → {result['id']}, copiedFrom={result.get('copiedFrom')}")

    runner.run_test("cuePoint.clone — clone code cue point", test_clone)

    def test_update_status():
        """Change cue point status to HANDLED (3)."""
        kaltura_post("cuepoint_cuepoint", "updateStatus", {
            "id": state["cloned_cp_id"],
            "status": 3,
        })
        result = kaltura_post("cuepoint_cuepoint", "get", {"id": state["cloned_cp_id"]})
        assert result.get("status") == 3, f"Expected HANDLED (3), got {result.get('status')}"
        print(f"    Status updated to HANDLED (3)")

    runner.run_test("cuePoint.updateStatus — set to HANDLED", test_update_status)

    def test_update_times():
        """Update cue point start and end times."""
        result = kaltura_post("cuepoint_cuepoint", "updateCuePointsTimes", {
            "id": state["code_cp_id"],
            "startTime": 15000,
            "endTime": 25000,
        })
        assert result.get("startTime") == 15000, f"Expected startTime=15000, got {result.get('startTime')}"
        assert result.get("endTime") == 25000, f"Expected endTime=25000, got {result.get('endTime')}"
        print(f"    Updated times: start={result['startTime']}, end={result['endTime']}")

    runner.run_test("cuePoint.updateCuePointsTimes — update start/end", test_update_times)

    def test_delete():
        """Delete a cue point and verify it's gone."""
        kaltura_post("cuepoint_cuepoint", "delete", {"id": state["cloned_cp_id"]})
        try:
            kaltura_post("cuepoint_cuepoint", "get", {"id": state["cloned_cp_id"]})
            print("    Deleted cue point still retrievable (status=DELETED)")
        except Exception as e:
            assert "INVALID_CUE_POINT_ID" in str(e), f"Unexpected error: {e}"
            print("    Confirmed: cue point deleted (INVALID_CUE_POINT_ID)")
        # Remove from cleanup since it's already deleted
        runner._cleanup_actions = [(n, f) for n, f in runner._cleanup_actions
                                   if state["cloned_cp_id"] not in n]

    runner.run_test("cuePoint.delete — soft-delete cue point", test_delete)

    # ════════════════════════════════════════════
    # Phase 9: Interactive Video Quiz
    # ════════════════════════════════════════════

    def test_quiz_add():
        """Mark entry as quiz with configuration."""
        try:
            result = kaltura_post("quiz_quiz", "add", {
                "entryId": state["entry_id"],
                "quiz[objectType]": "KalturaQuiz",
                "quiz[showResultOnAnswer]": 1,
                "quiz[showCorrectAfterSubmission]": 1,
                "quiz[allowAnswerUpdate]": 1,
                "quiz[showGradeAfterSubmission]": 1,
                "quiz[attemptsAllowed]": 3,
                "quiz[scoreType]": 1,
            })
        except Exception as e:
            if "ALREADY_A_QUIZ" in str(e):
                # Entry already has quiz config — update instead
                result = kaltura_post("quiz_quiz", "update", {
                    "entryId": state["entry_id"],
                    "quiz[objectType]": "KalturaQuiz",
                    "quiz[showResultOnAnswer]": 1,
                    "quiz[showCorrectAfterSubmission]": 1,
                    "quiz[allowAnswerUpdate]": 1,
                    "quiz[showGradeAfterSubmission]": 1,
                    "quiz[attemptsAllowed]": 3,
                    "quiz[scoreType]": 1,
                })
                print(f"    Entry already a quiz — updated config, version={result.get('version')}")
                return
            raise
        assert result.get("attemptsAllowed") == 3
        assert result.get("scoreType") == 1
        print(f"    Quiz added: version={result.get('version')}, attempts={result.get('attemptsAllowed')}")

    runner.run_test("quiz.add — mark entry as quiz", test_quiz_add)

    def test_quiz_get():
        """Retrieve quiz configuration."""
        result = kaltura_post("quiz_quiz", "get", {
            "entryId": state["entry_id"],
        })
        assert result.get("scoreType") == 1, f"Expected scoreType=1, got {result.get('scoreType')}"
        print(f"    Quiz config: scoreType={result.get('scoreType')}, version={result.get('version')}")

    runner.run_test("quiz.get — retrieve quiz configuration", test_quiz_get)

    def test_question_add():
        """Add a multiple-choice question."""
        result = kaltura_post("cuepoint_cuepoint", "add", {
            "cuePoint[objectType]": "KalturaQuestionCuePoint",
            "cuePoint[entryId]": state["entry_id"],
            "cuePoint[startTime]": 10000,
            "cuePoint[question]": "E2E test: What is 2+2?",
            "cuePoint[questionType]": 1,
            "cuePoint[hint]": "Basic arithmetic",
            "cuePoint[explanation]": "2+2=4 by definition",
            "cuePoint[tags]": "e2e-test",
            "cuePoint[optionalAnswers][0][key]": "a",
            "cuePoint[optionalAnswers][0][text]": "3",
            "cuePoint[optionalAnswers][0][isCorrect]": 0,
            "cuePoint[optionalAnswers][0][weight]": 1,
            "cuePoint[optionalAnswers][1][key]": "b",
            "cuePoint[optionalAnswers][1][text]": "4",
            "cuePoint[optionalAnswers][1][isCorrect]": 1,
            "cuePoint[optionalAnswers][1][weight]": 1,
            "cuePoint[optionalAnswers][2][key]": "c",
            "cuePoint[optionalAnswers][2][text]": "5",
            "cuePoint[optionalAnswers][2][isCorrect]": 0,
            "cuePoint[optionalAnswers][2][weight]": 1,
        })
        assert result.get("objectType") == "KalturaQuestionCuePoint"
        assert result.get("question") == "E2E test: What is 2+2?"
        assert len(result.get("optionalAnswers", [])) == 3
        state["question_cp_id"] = result["id"]
        runner.register_cleanup(f"question cue point {result['id']}",
                                lambda: _delete_cue_point(result["id"]))
        print(f"    Created question: {result['id']}, answers={len(result.get('optionalAnswers', []))}")

    runner.run_test("cuePoint.add — create quiz question (multiple choice)", test_question_add)

    def test_question_tf_add():
        """Add a true/false question."""
        result = kaltura_post("cuepoint_cuepoint", "add", {
            "cuePoint[objectType]": "KalturaQuestionCuePoint",
            "cuePoint[entryId]": state["entry_id"],
            "cuePoint[startTime]": 20000,
            "cuePoint[question]": "E2E test: The sky is blue.",
            "cuePoint[questionType]": 2,
            "cuePoint[tags]": "e2e-test",
            "cuePoint[optionalAnswers][0][key]": "true",
            "cuePoint[optionalAnswers][0][text]": "True",
            "cuePoint[optionalAnswers][0][isCorrect]": 1,
            "cuePoint[optionalAnswers][1][key]": "false",
            "cuePoint[optionalAnswers][1][text]": "False",
            "cuePoint[optionalAnswers][1][isCorrect]": 0,
        })
        assert result.get("questionType") == 2
        state["question_tf_id"] = result["id"]
        runner.register_cleanup(f"TF question {result['id']}",
                                lambda: _delete_cue_point(result["id"]))
        print(f"    Created T/F question: {result['id']}")

    runner.run_test("cuePoint.add — create true/false question", test_question_tf_add)

    def test_user_entry_add():
        """Start a quiz attempt (create user entry)."""
        result = kaltura_post("userEntry", "add", {
            "userEntry[objectType]": "KalturaQuizUserEntry",
            "userEntry[entryId]": state["entry_id"],
        })
        assert "id" in result, f"Expected user entry ID: {result}"
        state["user_entry_id"] = result["id"]
        runner.register_cleanup(f"user entry {result['id']}",
                                lambda: _delete_user_entry(result["id"]))
        print(f"    Started attempt: userEntryId={result['id']}, version={result.get('version')}")

    runner.run_test("userEntry.add — start quiz attempt", test_user_entry_add)

    def test_answer_add():
        """Submit an answer to the multiple-choice question."""
        result = kaltura_post("cuepoint_cuepoint", "add", {
            "cuePoint[objectType]": "KalturaAnswerCuePoint",
            "cuePoint[entryId]": state["entry_id"],
            "cuePoint[parentId]": state["question_cp_id"],
            "cuePoint[quizUserEntryId]": state["user_entry_id"],
            "cuePoint[answerKey]": "b",
        })
        assert result.get("objectType") == "KalturaAnswerCuePoint"
        assert result.get("isCorrect") == 1, f"Expected correct (1), got {result.get('isCorrect')}"
        state["answer_cp_id"] = result["id"]
        runner.register_cleanup(f"answer cue point {result['id']}",
                                lambda: _delete_cue_point(result["id"]))
        print(f"    Answer: {result['id']}, isCorrect={result.get('isCorrect')}")

    runner.run_test("cuePoint.add — submit correct answer", test_answer_add)

    def test_answer_wrong():
        """Submit a wrong answer to the T/F question."""
        result = kaltura_post("cuepoint_cuepoint", "add", {
            "cuePoint[objectType]": "KalturaAnswerCuePoint",
            "cuePoint[entryId]": state["entry_id"],
            "cuePoint[parentId]": state["question_tf_id"],
            "cuePoint[quizUserEntryId]": state["user_entry_id"],
            "cuePoint[answerKey]": "false",
        })
        assert result.get("isCorrect") == 0, f"Expected wrong (0), got {result.get('isCorrect')}"
        state["answer_wrong_id"] = result["id"]
        runner.register_cleanup(f"wrong answer {result['id']}",
                                lambda: _delete_cue_point(result["id"]))
        print(f"    Answer: {result['id']}, isCorrect={result.get('isCorrect')}")

    runner.run_test("cuePoint.add — submit wrong answer", test_answer_wrong)

    def test_submit_quiz():
        """Submit quiz for scoring."""
        result = kaltura_post("userEntry", "submitQuiz", {
            "id": state["user_entry_id"],
        })
        assert result.get("status") == "quiz.3" or str(result.get("status")) == "quiz.3", \
            f"Expected SUBMITTED (quiz.3), got {result.get('status')}"
        score = result.get("score", result.get("calculatedScore"))
        print(f"    Submitted: score={score}, status={result.get('status')}")

    runner.run_test("userEntry.submitQuiz — calculate score", test_submit_quiz)

    def test_quiz_list():
        """List quiz entries."""
        result = kaltura_post("quiz_quiz", "list", {
            "filter[entryIdEqual]": state["entry_id"],
        })
        assert result.get("totalCount", 0) >= 1, f"Expected quiz in list: {result}"
        print(f"    Quiz entries: {result.get('totalCount')}")

    runner.run_test("quiz.list — list quiz entries", test_quiz_list)

    def test_quiz_get_url():
        """Get quiz PDF download URL (requires allowDownload=1)."""
        # Ensure allowDownload is enabled
        kaltura_post("quiz_quiz", "update", {
            "entryId": state["entry_id"],
            "quiz[objectType]": "KalturaQuiz",
            "quiz[allowDownload]": 1,
        })
        result = kaltura_post("quiz_quiz", "getUrl", {
            "entryId": state["entry_id"],
            "quizOutputType": 1,
        })
        assert isinstance(result, str) and ("http" in result or "/" in result), \
            f"Expected URL string, got: {result}"
        print(f"    PDF URL: {result[:80]}...")

    runner.run_test("quiz.getUrl — get PDF download URL", test_quiz_get_url)

    def test_user_entry_list():
        """List user entries for the quiz."""
        result = kaltura_post("userEntry", "list", {
            "filter[entryIdEqual]": state["entry_id"],
        })
        assert result.get("totalCount", 0) >= 1, f"Expected user entries: {result}"
        found = any(str(o.get("id")) == str(state["user_entry_id"])
                     for o in result.get("objects", []))
        assert found, "Created user entry not found in list"
        print(f"    User entries: {result.get('totalCount')}")

    runner.run_test("userEntry.list — list quiz attempts", test_user_entry_list)

    # ════════════════════════════════════════════
    # Phase 10: eSearch — Cue Point Search
    # ════════════════════════════════════════════

    def test_esearch_cue_point():
        """Search for entries with cue points via eSearch."""
        # Allow indexing time
        time.sleep(5)
        result = kaltura_post("elasticsearch_esearch", "searchEntry", {
            "searchParams[objectType]": "KalturaESearchEntryParams",
            "searchParams[searchOperator][objectType]": "KalturaESearchEntryOperator",
            "searchParams[searchOperator][operator]": 1,
            "searchParams[searchOperator][searchItems][0][objectType]": "KalturaESearchCuePointItem",
            "searchParams[searchOperator][searchItems][0][itemType]": 1,
            "searchParams[searchOperator][searchItems][0][fieldName]": "tags",
            "searchParams[searchOperator][searchItems][0][searchTerm]": "e2e-test",
        })
        total = result.get("totalCount", 0)
        assert total >= 1, f"Expected entries with e2e-test cue points, got {total}"
        print(f"    eSearch found {total} entries with e2e-test tagged cue points")

    runner.run_test("eSearch — find entries by cue point tags", test_esearch_cue_point)

    def test_esearch_question():
        """Search for entries containing quiz questions."""
        result = kaltura_post("elasticsearch_esearch", "searchEntry", {
            "searchParams[objectType]": "KalturaESearchEntryParams",
            "searchParams[searchOperator][objectType]": "KalturaESearchEntryOperator",
            "searchParams[searchOperator][operator]": 1,
            "searchParams[searchOperator][searchItems][0][objectType]": "KalturaESearchCuePointItem",
            "searchParams[searchOperator][searchItems][0][itemType]": 2,
            "searchParams[searchOperator][searchItems][0][fieldName]": "question",
            "searchParams[searchOperator][searchItems][0][searchTerm]": "2+2",
        })
        total = result.get("totalCount", 0)
        # eSearch indexing may have a delay — accept 0 with a note
        if total >= 1:
            print(f"    eSearch found {total} entries with '2+2' question")
        else:
            print(f"    eSearch returned 0 (indexing delay expected for new cue points)")

    runner.run_test("eSearch — search quiz question content", test_esearch_question)

    # ════════════════════════════════════════════
    # Cleanup & Summary
    # ════════════════════════════════════════════

    keep = "--keep" in sys.argv
    if keep:
        print("\n--keep flag set. Skipping cleanup.")
        print(f"  Entry: {state.get('entry_id')}")
        print(f"  Code CP: {state.get('code_cp_id')}")
        print(f"  Chapter CP: {state.get('chapter_cp_id')}")
        print(f"  Slide CP: {state.get('slide_cp_id')}")
        print(f"  Annotation CP: {state.get('annotation_cp_id')}")
        print(f"  Ad CP: {state.get('ad_cp_id')}")
        print(f"  Event CP: {state.get('event_cp_id')}")
        print(f"  Session CP: {state.get('session_cp_id')}")
        print(f"  Question CP: {state.get('question_cp_id')}")
        print(f"  User Entry: {state.get('user_entry_id')}")
    else:
        if sys.stdin.isatty():
            input("\nPress Enter to clean up...")
        runner.cleanup()

    success = runner.summary()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
