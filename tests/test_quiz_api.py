#!/usr/bin/env python3
"""End-to-end validation of the Kaltura Interactive Video Quiz API.

Covers: quiz.add/get/update/list/getUrl, 5 question types (MC, T/F, reflection,
multi-answer, open), viewer quiz flow (userEntry, answers, scoring), reports,
and instructor feedback.
"""

import sys
import os
import time

sys.path.insert(0, os.path.dirname(__file__))
from test_helpers import kaltura_post, TestRunner, PARTNER_ID, KS, SERVICE_URL

state = {}


def _find_ready_entry():
    """Find an existing READY entry to attach quiz to."""
    result = kaltura_post("baseEntry", "list", {
        "filter[statusEqual]": 2,
        "filter[mediaTypeEqual]": 1,
        "pager[pageSize]": 1,
    })
    entries = result.get("objects", [])
    assert len(entries) > 0, "No READY entries found on account"
    return entries[0]["id"], entries[0].get("name", "unknown")


def _delete_cue_point(cp_id):
    try:
        kaltura_post("cuepoint_cuepoint", "delete", {"id": cp_id})
    except Exception:
        pass


def _delete_user_entry(ue_id):
    try:
        kaltura_post("userEntry", "delete", {"id": ue_id})
    except Exception:
        pass


def main():
    runner = TestRunner("Interactive Video Quiz — E2E Validation")

    # ════════════════════════════════════════════
    # Phase 1: Setup
    # ════════════════════════════════════════════

    def test_find_entry():
        entry_id, name = _find_ready_entry()
        state["entry_id"] = entry_id
        print(f"    Using entry: {entry_id} — {name}")

    runner.run_test("baseEntry.list — find READY entry for quiz tests", test_find_entry)

    # ════════════════════════════════════════════
    # Phase 2: Quiz Configuration
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

    # ════════════════════════════════════════════
    # Phase 3: Question Types
    # ════════════════════════════════════════════

    def test_question_add():
        """Add a multiple-choice question (type=1)."""
        result = kaltura_post("cuepoint_cuepoint", "add", {
            "cuePoint[objectType]": "KalturaQuestionCuePoint",
            "cuePoint[entryId]": state["entry_id"],
            "cuePoint[startTime]": 10000,
            "cuePoint[question]": "E2E test: What is 2+2?",
            "cuePoint[questionType]": 1,
            "cuePoint[hint]": "Basic arithmetic",
            "cuePoint[explanation]": "2+2=4 by definition",
            "cuePoint[tags]": "e2e-quiz-test",
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
        print(f"    Created MC question: {result['id']}, answers={len(result.get('optionalAnswers', []))}")

    runner.run_test("cuePoint.add — multiple choice question (type=1)", test_question_add)

    def test_question_tf_add():
        """Add a true/false question (type=2)."""
        result = kaltura_post("cuepoint_cuepoint", "add", {
            "cuePoint[objectType]": "KalturaQuestionCuePoint",
            "cuePoint[entryId]": state["entry_id"],
            "cuePoint[startTime]": 20000,
            "cuePoint[question]": "E2E test: The sky is blue.",
            "cuePoint[questionType]": 2,
            "cuePoint[tags]": "e2e-quiz-test",
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

    runner.run_test("cuePoint.add — true/false question (type=2)", test_question_tf_add)

    def test_question_reflection():
        """Add a reflection point (type=3, no correct answer, not scored)."""
        result = kaltura_post("cuepoint_cuepoint", "add", {
            "cuePoint[objectType]": "KalturaQuestionCuePoint",
            "cuePoint[entryId]": state["entry_id"],
            "cuePoint[startTime]": 25000,
            "cuePoint[question]": "E2E: Pause and consider — what did you learn?",
            "cuePoint[questionType]": 3,
            "cuePoint[excludeFromScore]": 1,
            "cuePoint[tags]": "e2e-quiz-test",
        })
        assert result.get("questionType") == 3, f"Expected type 3, got {result.get('questionType')}"
        state["question_reflection_id"] = result["id"]
        runner.register_cleanup(f"reflection question {result['id']}",
                                lambda: _delete_cue_point(result["id"]))
        print(f"    Created reflection: {result['id']}, excludeFromScore={result.get('excludeFromScore')}")

    runner.run_test("cuePoint.add — reflection point question (type=3)", test_question_reflection)

    def test_question_multi_answer():
        """Add a multiple-answer question (type=4, multiple correct)."""
        result = kaltura_post("cuepoint_cuepoint", "add", {
            "cuePoint[objectType]": "KalturaQuestionCuePoint",
            "cuePoint[entryId]": state["entry_id"],
            "cuePoint[startTime]": 35000,
            "cuePoint[question]": "E2E: Select ALL primary colors",
            "cuePoint[questionType]": 4,
            "cuePoint[tags]": "e2e-quiz-test",
            "cuePoint[optionalAnswers][0][key]": "r",
            "cuePoint[optionalAnswers][0][text]": "Red",
            "cuePoint[optionalAnswers][0][isCorrect]": 1,
            "cuePoint[optionalAnswers][1][key]": "g",
            "cuePoint[optionalAnswers][1][text]": "Green",
            "cuePoint[optionalAnswers][1][isCorrect]": 0,
            "cuePoint[optionalAnswers][2][key]": "b",
            "cuePoint[optionalAnswers][2][text]": "Blue",
            "cuePoint[optionalAnswers][2][isCorrect]": 1,
        })
        assert result.get("questionType") == 4
        correct_count = sum(1 for a in result.get("optionalAnswers", []) if a.get("isCorrect") == 1)
        assert correct_count == 2, f"Expected 2 correct answers, got {correct_count}"
        state["question_multi_id"] = result["id"]
        runner.register_cleanup(f"multi-answer question {result['id']}",
                                lambda: _delete_cue_point(result["id"]))
        print(f"    Created multi-answer: {result['id']}, correct_count={correct_count}")

    runner.run_test("cuePoint.add — multiple-answer question (type=4)", test_question_multi_answer)

    def test_question_open():
        """Add an open-ended question (type=8, free-text answer)."""
        result = kaltura_post("cuepoint_cuepoint", "add", {
            "cuePoint[objectType]": "KalturaQuestionCuePoint",
            "cuePoint[entryId]": state["entry_id"],
            "cuePoint[startTime]": 40000,
            "cuePoint[question]": "E2E: Describe the main concept in your own words",
            "cuePoint[questionType]": 8,
            "cuePoint[tags]": "e2e-quiz-test",
        })
        assert result.get("questionType") == 8
        state["question_open_id"] = result["id"]
        runner.register_cleanup(f"open question {result['id']}",
                                lambda: _delete_cue_point(result["id"]))
        print(f"    Created open question: {result['id']}")

    runner.run_test("cuePoint.add — open-ended question (type=8)", test_question_open)

    # ════════════════════════════════════════════
    # Phase 4: Viewer Quiz Flow
    # ════════════════════════════════════════════

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
        """Submit a correct answer to the MC question."""
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

    def test_open_answer():
        """Submit a free-text answer to the open question."""
        result = kaltura_post("cuepoint_cuepoint", "add", {
            "cuePoint[objectType]": "KalturaAnswerCuePoint",
            "cuePoint[entryId]": state["entry_id"],
            "cuePoint[parentId]": state["question_open_id"],
            "cuePoint[quizUserEntryId]": state["user_entry_id"],
            "cuePoint[openAnswer]": "The main concept is dependency injection via factory pattern.",
        })
        assert result.get("objectType") == "KalturaAnswerCuePoint"
        assert result.get("openAnswer") is not None, "openAnswer should be set"
        state["open_answer_id"] = result["id"]
        runner.register_cleanup(f"open answer {result['id']}",
                                lambda: _delete_cue_point(result["id"]))
        print(f"    Open answer: {result['id']}, openAnswer={result.get('openAnswer', '')[:50]}")

    runner.run_test("cuePoint.add — open-ended answer with openAnswer field", test_open_answer)

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

    # ════════════════════════════════════════════
    # Phase 5: Quiz Service Actions
    # ════════════════════════════════════════════

    def test_quiz_list():
        """List quiz entries."""
        result = kaltura_post("quiz_quiz", "list", {
            "filter[entryIdEqual]": state["entry_id"],
        })
        assert result.get("totalCount", 0) >= 1, f"Expected quiz in list: {result}"
        print(f"    Quiz entries: {result.get('totalCount')}")

    runner.run_test("quiz.list — list quiz entries", test_quiz_list)

    def test_quiz_get_url():
        """Get quiz PDF download URL."""
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
    # Phase 6: Feedback & Reports
    # ════════════════════════════════════════════

    def test_answer_feedback():
        """Set instructor feedback on an answer cue point."""
        answer = kaltura_post("cuepoint_cuepoint", "get", {"id": state["answer_cp_id"]})
        result = kaltura_post("cuepoint_cuepoint", "update", {
            "id": state["answer_cp_id"],
            "cuePoint[objectType]": "KalturaAnswerCuePoint",
            "cuePoint[entryId]": state["entry_id"],
            "cuePoint[quizUserEntryId]": answer.get("quizUserEntryId", state["user_entry_id"]),
            "cuePoint[feedback]": "Well done — correct!",
        })
        assert result.get("feedback") == "Well done — correct!", \
            f"Expected feedback text, got {result.get('feedback')}"
        print(f"    Feedback set on answer {state['answer_cp_id']}: {result.get('feedback')}")

    runner.run_test("cuePoint.update — set instructor feedback on answer", test_answer_feedback)

    def test_quiz_report():
        """Pull a quiz report via report.getTable."""
        result = kaltura_post("report", "getTable", {
            "reportType": "quiz.QUIZ",
            "reportInputFilter[objectType]": "KalturaEndUserReportInputFilter",
            "reportInputFilter[entryIdIn]": state["entry_id"],
            "reportInputFilter[timeZoneOffset]": 0,
            "pager[pageSize]": 25,
            "objectIds": state["entry_id"],
        })
        assert result is not None, "Report returned None"
        if isinstance(result, dict):
            print(f"    Quiz report: totalCount={result.get('totalCount')}, "
                  f"header={result.get('header', '')[:60]}")
        else:
            print(f"    Quiz report: {str(result)[:80]}")

    runner.run_test("report.getTable — quiz.QUIZ report", test_quiz_report)

    def test_quiz_user_report():
        """Pull per-user quiz percentage report."""
        result = kaltura_post("report", "getTable", {
            "reportType": "quiz.QUIZ_USER_PERCENTAGE",
            "reportInputFilter[objectType]": "KalturaEndUserReportInputFilter",
            "reportInputFilter[entryIdIn]": state["entry_id"],
            "reportInputFilter[timeZoneOffset]": 0,
            "pager[pageSize]": 25,
            "objectIds": state["entry_id"],
        })
        assert result is not None, "Report returned None"
        if isinstance(result, dict):
            print(f"    User % report: totalCount={result.get('totalCount')}, "
                  f"header={result.get('header', '')[:60]}")
        else:
            print(f"    User % report: {str(result)[:80]}")

    runner.run_test("report.getTable — quiz.QUIZ_USER_PERCENTAGE report", test_quiz_user_report)

    # ════════════════════════════════════════════
    # Cleanup & Summary
    # ════════════════════════════════════════════

    keep = "--keep" in sys.argv
    if keep:
        print("\n--keep flag set. Skipping cleanup.")
        print(f"  Entry: {state.get('entry_id')}")
        print(f"  Question MC: {state.get('question_cp_id')}")
        print(f"  Question TF: {state.get('question_tf_id')}")
        print(f"  User Entry: {state.get('user_entry_id')}")
    else:
        if sys.stdin.isatty():
            input("\nPress Enter to clean up...")
        runner.cleanup()

    success = runner.summary()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
