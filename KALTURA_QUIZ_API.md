# Kaltura Interactive Video Quiz API

The quiz system turns video entries into interactive assessments.  
It uses cue points for questions and answers, with a configuration layer  
on the entry and a user-entry service for tracking attempts and scores.

**Base URL:** `$KALTURA_SERVICE_URL` (e.g., `https://www.kaltura.com/api_v3`)  
**Auth:** KS via `ks` parameter (admin KS with `disableentitlement` for full access)  
**Format:** `format=1` for JSON responses  
**Services:** `quiz_quiz`, `cuepoint_cuepoint`, `userEntry`, `report`  
**Prerequisite:** [Cue Points Hub](KALTURA_CUE_POINTS_API.md) for base cue point concepts and shared CRUD

<!-- Sections: 1.When to Use | 2.Prerequisites | 3.Quiz Lifecycle | 4.Mark an Entry as a Quiz | 5.Quiz Configuration (KalturaQuiz) | 6.Quiz Service Actions | 7.Question Types | 8.Question Fields | 9.Viewer Quiz Flow | 10.Answer Fields | 11.Quiz User Entry | 12.Scoring Models | 13.Quiz Reports | 14.Player IVQ Plugin | 15.Quiz Generation via REACH / Content Lab | 16.Gamification Integration | 17.Searching Quiz Content | 18.Error Handling | 19.Best Practices | 20.Related Guides -->


# 1. When to Use

- **Interactive learning** — Add assessments directly inside training videos so learners answer questions without leaving the player.  
- **Knowledge evaluation** — Measure learner comprehension with scored quizzes that track attempts, correctness, and completion rates.  
- **LMS quiz integration** — Programmatically create and manage video-based quizzes from an external Learning Management System, syncing scores and reports back to the LMS.  
- **Certification and compliance** — Gate course completion behind passing quiz scores, supporting multiple retakes and configurable scoring models.  
- **Content engagement** — Increase viewer attention and retention by interspersing questions, reflection points, and branching navigation throughout video content.


# 2. Prerequisites

- **KS (Kaltura Session):** Admin KS (type=2) with `disableentitlement` for creating and managing quizzes. Viewer interactions (starting attempts, submitting answers) use a USER KS (type=0) scoped to the entry.  
- **Cue Points plugin:** The `cuePoint` server plugin must be enabled on the account (enabled by default on most accounts).  
- **Quiz plugin:** The `quiz` server plugin must be enabled on the account.  
- **Player IVQ plugin:** To render quizzes during playback, enable the `ivq` and `kalturaCuepoints` plugins in the player configuration.  
- **Session management:** See [Session Guide](KALTURA_SESSION_GUIDE.md) for KS generation and privilege scoping.


# 3. Quiz Lifecycle

```
media.add (create video/audio entry)
    → media.addContent (upload or import content)
        → quiz.add (mark entry as quiz — sets capabilities='quiz.quiz')
            → cuePoint.add (add KalturaQuestionCuePoint for each question)
                → userEntry.add (viewer starts attempt → KalturaQuizUserEntry)
                    → cuePoint.add (viewer answers → KalturaAnswerCuePoint per question)
                        → userEntry.submitQuiz (calculate score)
                            → report.getTable (pull reports)
```

A quiz is built on top of a video or audio entry (mediaType=1 or mediaType=5). Create the source entry first, then call `quiz.add` to mark it as a quiz. This sets `capabilities = 'quiz.quiz'` on the entry, which is how the Player IVQ plugin and Content Hubs recognize it as a quiz entry. Questions are cue points positioned on the timeline. Viewers start an attempt, answer questions as playback progresses, and submit for scoring. The system auto-calculates correctness and computes scores across attempts.


# 4. Mark an Entry as a Quiz

**Service:** `quiz_quiz`  
**Prerequisite:** A video or audio entry (mediaType=1 or 5) must already exist. Create the entry with `media.add` + `media.addContent` first. See [Upload & Ingestion](KALTURA_UPLOAD_AND_INGESTION_API.md).

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/quiz_quiz/action/add" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "entryId=$KALTURA_ENTRY_ID" \
  -d "quiz[objectType]=KalturaQuiz" \
  -d "quiz[showResultOnAnswer]=1" \
  -d "quiz[showCorrectAfterSubmission]=1" \
  -d "quiz[allowAnswerUpdate]=1" \
  -d "quiz[showGradeAfterSubmission]=1" \
  -d "quiz[attemptsAllowed]=3" \
  -d "quiz[scoreType]=1"
```

This action sets `capabilities = 'quiz.quiz'` on the entry automatically. The Player IVQ plugin and Content Hubs use this field to identify quiz entries and render quiz UI.

If the entry already has a quiz configuration, `quiz.add` returns `PROVIDED_ENTRY_IS_ALREADY_A_QUIZ` — use `quiz.update` instead.


# 5. Quiz Configuration (KalturaQuiz)

| Field | Type | Description |
|-------|------|-------------|
| `version` | int | Auto-incremented on update (readonly) |
| `showResultOnAnswer` | int | Show correct/incorrect immediately (-1/0/1) |
| `showCorrectKeyOnAnswer` | int | Show correct answer key while answering |
| `allowAnswerUpdate` | int | Allow changing answers before submission |
| `showCorrectAfterSubmission` | int | Reveal correct answers after submit |
| `allowDownload` | int | Allow PDF download of quiz |
| `showGradeAfterSubmission` | int | Show score after submit |
| `attemptsAllowed` | int | Number of retakes allowed |
| `scoreType` | int | How to calculate final score across attempts |


# 6. Quiz Service Actions

| Action | Description |
|--------|-------------|
| `add` | Mark entry as quiz with configuration (sets `capabilities='quiz.quiz'`) |
| `get` | Get quiz config by entryId |
| `update` | Update quiz settings (increments version) |
| `list` | List quiz entries (filter by `entryIdEqual` or `entryIdIn`) |
| `serve` | Download quiz as PDF |
| `getUrl` | Get PDF download URL (`quizOutputType`: 1=PDF) |

**Discovering quiz entries:** Use `quiz.list` with `filter[entryIdEqual]` or `filter[entryIdIn]` to retrieve quiz configurations. The `capabilities` field on entries (`'quiz.quiz'`) is set automatically by `quiz.add` and is how the system identifies quiz entries.

**Deleting quiz attempts:** Use `userEntry.delete` with the user entry ID to remove a quiz attempt.


# 7. Question Types

| Value | Name | Description |
|-------|------|-------------|
| 1 | MULTIPLE_CHOICE_ANSWER | Single correct answer from options |
| 2 | TRUE_FALSE | True/false question |
| 3 | REFLECTION_POINT | Pause for reflection (no correct answer, not scored) |
| 4 | MULTIPLE_ANSWER_QUESTION | Multiple correct answers |
| 5 | FILL_IN_BLANK | Fill in the blank |
| 6 | HOT_SPOT | Hotspot on video frame |
| 7 | GO_TO | Navigation/branching point |
| 8 | OPEN_QUESTION | Free-text open-ended question |

## 7.1 Multiple Choice (type=1)

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/cuepoint_cuepoint/action/add" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "cuePoint[objectType]=KalturaQuestionCuePoint" \
  -d "cuePoint[entryId]=$KALTURA_ENTRY_ID" \
  -d "cuePoint[startTime]=30000" \
  -d "cuePoint[question]=What design pattern separates object creation from usage?" \
  -d "cuePoint[questionType]=1" \
  -d "cuePoint[hint]=Think about object creation" \
  -d "cuePoint[explanation]=The Factory pattern delegates instantiation to subclasses" \
  -d "cuePoint[optionalAnswers][0][key]=1" \
  -d "cuePoint[optionalAnswers][0][text]=Factory" \
  -d "cuePoint[optionalAnswers][0][isCorrect]=1" \
  -d "cuePoint[optionalAnswers][0][weight]=1" \
  -d "cuePoint[optionalAnswers][1][key]=2" \
  -d "cuePoint[optionalAnswers][1][text]=Singleton" \
  -d "cuePoint[optionalAnswers][1][isCorrect]=0" \
  -d "cuePoint[optionalAnswers][1][weight]=1" \
  -d "cuePoint[optionalAnswers][2][key]=3" \
  -d "cuePoint[optionalAnswers][2][text]=Observer" \
  -d "cuePoint[optionalAnswers][2][isCorrect]=0" \
  -d "cuePoint[optionalAnswers][2][weight]=1"
```

## 7.2 True/False (type=2)

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/cuepoint_cuepoint/action/add" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "cuePoint[objectType]=KalturaQuestionCuePoint" \
  -d "cuePoint[entryId]=$KALTURA_ENTRY_ID" \
  -d "cuePoint[startTime]=20000" \
  -d "cuePoint[question]=The sky is blue." \
  -d "cuePoint[questionType]=2" \
  -d "cuePoint[optionalAnswers][0][key]=true" \
  -d "cuePoint[optionalAnswers][0][text]=True" \
  -d "cuePoint[optionalAnswers][0][isCorrect]=1" \
  -d "cuePoint[optionalAnswers][1][key]=false" \
  -d "cuePoint[optionalAnswers][1][text]=False" \
  -d "cuePoint[optionalAnswers][1][isCorrect]=0"
```

## 7.3 Reflection Point (type=3)

Pauses for reflection — no correct answer, excluded from scoring:

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/cuepoint_cuepoint/action/add" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "cuePoint[objectType]=KalturaQuestionCuePoint" \
  -d "cuePoint[entryId]=$KALTURA_ENTRY_ID" \
  -d "cuePoint[startTime]=25000" \
  -d "cuePoint[question]=Pause and consider — what did you learn so far?" \
  -d "cuePoint[questionType]=3" \
  -d "cuePoint[excludeFromScore]=1"
```

## 7.4 Multiple Answer (type=4)

Multiple correct answers — viewer must select all correct options:

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/cuepoint_cuepoint/action/add" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "cuePoint[objectType]=KalturaQuestionCuePoint" \
  -d "cuePoint[entryId]=$KALTURA_ENTRY_ID" \
  -d "cuePoint[startTime]=35000" \
  -d "cuePoint[question]=Select ALL primary colors" \
  -d "cuePoint[questionType]=4" \
  -d "cuePoint[optionalAnswers][0][key]=r" \
  -d "cuePoint[optionalAnswers][0][text]=Red" \
  -d "cuePoint[optionalAnswers][0][isCorrect]=1" \
  -d "cuePoint[optionalAnswers][1][key]=g" \
  -d "cuePoint[optionalAnswers][1][text]=Green" \
  -d "cuePoint[optionalAnswers][1][isCorrect]=0" \
  -d "cuePoint[optionalAnswers][2][key]=b" \
  -d "cuePoint[optionalAnswers][2][text]=Blue" \
  -d "cuePoint[optionalAnswers][2][isCorrect]=1"
```

## 7.5 Open Question (type=8)

Free-text open-ended question — viewer types a response:

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/cuepoint_cuepoint/action/add" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "cuePoint[objectType]=KalturaQuestionCuePoint" \
  -d "cuePoint[entryId]=$KALTURA_ENTRY_ID" \
  -d "cuePoint[startTime]=40000" \
  -d "cuePoint[question]=Describe the main concept in your own words" \
  -d "cuePoint[questionType]=8"
```

## 7.6 Fill in the Blank (type=5)

The viewer fills in a blank within the question text. The `optionalAnswers` array defines acceptable answers.

## 7.7 Hot Spot (type=6)

Hotspot on a video frame — the viewer clicks on a region. Position data is stored in `partnerData`.

## 7.8 Go To (type=7)

Navigation/branching point — used for adaptive quizzes where the next question depends on the answer.


# 8. Question Fields

| Field | Type | Description |
|-------|------|-------------|
| `question` | string | Question text |
| `questionType` | int | Question type (see table above) |
| `optionalAnswers` | array | Array of answer choices |
| `hint` | string | Hint text shown to viewer |
| `explanation` | string | Explanation (hidden from non-editors) |
| `presentationOrder` | int | Display order |
| `excludeFromScore` | int | Exclude from score calculation (-1/0/1) |

Each `optionalAnswer` has: `key` (string), `text` (string), `weight` (float, default 1.0), `isCorrect` (int: -1/0/1).

**Security:** When a non-editor viewer retrieves question cue points, `isCorrect` on each answer option is returned as null and `explanation` is omitted. This prevents viewers from reading correct answers via the API.


# 9. Viewer Quiz Flow

**Step 1 — Start attempt:**

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/userentry/action/add" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "userEntry[objectType]=KalturaQuizUserEntry" \
  -d "userEntry[entryId]=$KALTURA_ENTRY_ID"
```

Returns a `KalturaQuizUserEntry` with `id`, `status=1` (ACTIVE), and `version` (attempt number).

**Step 2 — Submit answers:**

For each question, create a `KalturaAnswerCuePoint`:

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/cuepoint_cuepoint/action/add" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "cuePoint[objectType]=KalturaAnswerCuePoint" \
  -d "cuePoint[entryId]=$KALTURA_ENTRY_ID" \
  -d "cuePoint[parentId]=$QUESTION_CUE_POINT_ID" \
  -d "cuePoint[quizUserEntryId]=$QUIZ_USER_ENTRY_ID" \
  -d "cuePoint[answerKey]=1"
```

The server auto-calculates `isCorrect` by comparing `answerKey` against the question's correct answer keys.

For open questions, use `openAnswer` instead of `answerKey`:

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/cuepoint_cuepoint/action/add" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "cuePoint[objectType]=KalturaAnswerCuePoint" \
  -d "cuePoint[entryId]=$KALTURA_ENTRY_ID" \
  -d "cuePoint[parentId]=$QUESTION_CUE_POINT_ID" \
  -d "cuePoint[quizUserEntryId]=$QUIZ_USER_ENTRY_ID" \
  -d "cuePoint[openAnswer]=The main concept is dependency injection via factory pattern."
```

**Step 3 — Submit quiz for scoring:**

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/userentry/action/submitQuiz" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "id=$QUIZ_USER_ENTRY_ID"
```

Returns the `KalturaQuizUserEntry` with `score`, `calculatedScore`, and `status=quiz.3` (SUBMITTED).


# 10. Answer Fields

| Field | Type | Description |
|-------|------|-------------|
| `parentId` | string | Question cue point ID (insert-only, **required**) |
| `quizUserEntryId` | string | User entry ID for this attempt (insert-only, **required**) |
| `answerKey` | string | Selected answer key |
| `openAnswer` | string | Free-text answer (max 1024 chars, for open questions) |
| `isCorrect` | int | Server-computed correctness (readonly) |
| `correctAnswerKeys` | array | Correct answer keys from the question (readonly) |
| `explanation` | string | Explanation copied from question (readonly) |
| `feedback` | string | Instructor feedback (max 1024 chars, admin-only write) |

**Instructor feedback:** Update an answer cue point with the `feedback` field. The update requires both `entryId` and `quizUserEntryId` in the request body.


# 11. Quiz User Entry

| Field | Type | Description |
|-------|------|-------------|
| `score` | float | Raw quiz score (readonly) |
| `calculatedScore` | float | Score based on scoreType across attempts (readonly) |
| `feedback` | string | Overall instructor feedback (max 1024 chars) |
| `version` | int | Attempt number, 0-based (readonly) |
| `status` | string | 1=ACTIVE, 2=DELETED, quiz.3=SUBMITTED |


# 12. Scoring Models

| Value | Name | Description |
|-------|------|-------------|
| 1 | HIGHEST | Best score across all attempts |
| 2 | LOWEST | Worst score across all attempts |
| 3 | LATEST | Most recent attempt |
| 4 | FIRST | First attempt only |
| 5 | AVERAGE | Average across all attempts |


# 13. Quiz Reports

Four report types accessible via `report.getTable`:

| reportType | Description |
|------------|-------------|
| `quiz.QUIZ` | Per-question correct/wrong percentage |
| `quiz.QUIZ_USER_PERCENTAGE` | Per-user overall percentage |
| `quiz.QUIZ_AGGREGATE_BY_QUESTION` | Aggregated by specific question IDs |
| `quiz.QUIZ_USER_AGGREGATE_BY_QUESTION` | Per-user per-question breakdown |

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/report/action/getTable" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "reportType=quiz.QUIZ" \
  -d "reportInputFilter[objectType]=KalturaEndUserReportInputFilter" \
  -d "reportInputFilter[entryIdIn]=$KALTURA_ENTRY_ID" \
  -d "reportInputFilter[timeZoneOffset]=0" \
  -d "objectIds=$KALTURA_ENTRY_ID" \
  -d "pager[pageSize]=25"
```

The `objectIds` parameter must be set to the entry ID. The response contains `header` (comma-separated column names) and `data` (rows).


# 14. Player IVQ Plugin

The `ivq` player plugin renders quiz questions as overlays during playback:

```javascript
plugins: {
  kalturaCuepoints: {},
  ivq: {}
}
```

All quiz behavior is driven by the quiz data on the entry (via `quiz.get`), not plugin config.

**Quiz player flow:**
1. Welcome screen (if `showWelcomePage` enabled) with available attempts
2. As playback reaches a question's `startTime`, video pauses and question overlay appears
3. If `preventSeek` is enabled, forward seeking is blocked (middleware intercepts `setCurrentTime`)
4. After all questions answered and video ends, submit screen appears
5. After submission, review screen shows score and correct answers (per quiz config)

**Events:** `QuizStarted`, `QuizSkipped`, `QuestionAnswered`, `QuizSubmitted`, `QuizRetake`


# 15. Quiz Generation via REACH / Content Lab

AI-powered quiz generation is available through two paths:

- **REACH API** — Order a `QUIZ` task (serviceFeature=12) via `entryVendorTask.add`. The AI engine analyzes video content and generates question cue points automatically. See [REACH API](KALTURA_REACH_API.md).
- **Content Lab** — The Content Lab widget provides a UI for AI quiz generation from video content. See [Content Lab API](KALTURA_CONTENT_LAB_API.md).

Both paths produce standard `KalturaQuestionCuePoint` cue points — the same type created manually via the API.


# 16. Gamification Integration

Quiz completion events (`quizSubmitted`) can trigger gamification scoring rules — leaderboard points, badges for quiz completion, and certificates for passing scores. See [Gamification API](KALTURA_GAMIFICATION_API.md).


# 17. Searching Quiz Content

Quiz questions and answers are indexed in eSearch via `KalturaESearchCuePointItem`. Searchable fields include `question`, `answers`, `hint`, and `explanation`. See [Cue Points Hub — eSearch Integration](KALTURA_CUE_POINTS_API.md) for query examples.


# 18. Error Handling

| Error | Cause | Fix |
|-------|-------|-----|
| `PROVIDED_ENTRY_IS_ALREADY_A_QUIZ` | Calling `quiz.add` on entry with existing quiz config | Use `quiz.update` to modify existing config |
| `PARENT_CUE_POINT_NOT_FOUND` | Invalid `parentId` on answer cue point | Parent question must exist on the same entry |
| `CANNOT_APPROVE_TASK`-like for quiz | Submitting already-submitted quiz | Check `userEntry.status` before submission |
| `PROPERTY_VALIDATION_CANNOT_BE_NULL` | Answer without `parentId` or `quizUserEntryId` | Both fields are required on answer creation |
| `USER_ENTRY_NOT_FOUND` | Invalid `quizUserEntryId` on answer | Start an attempt with `userEntry.add` first |


# 19. Best Practices

- **Quiz answer security is server-enforced.** Non-editors cannot see `isCorrect` or `explanation` on question cue points — no client-side hiding needed.
- **Use `excludeFromScore=1`** for reflection points (type=3) and any question not meant for grading.
- **Check `userEntry.status` before submission.** Already-submitted quizzes cannot be resubmitted.
- **Include both `entryId` and `quizUserEntryId`** when updating answer feedback — the API requires both for validation.
- **Use `scoreType=1` (HIGHEST)** for training scenarios where learners retake until passing.
- **Retrieve quiz config with `quiz.get`** to check `attemptsAllowed` before starting new attempts.
- **Register cleanup before assertions** in tests. Quiz cue points and user entries persist — always clean up test data.


# 20. Related Guides

- **[Cue Points Hub](KALTURA_CUE_POINTS_API.md)** — Base cue point concepts, shared CRUD, eSearch integration
- **[Player Embed Guide](KALTURA_PLAYER_EMBED_GUIDE.md)** — Player v7 setup, IVQ plugin configuration
- **[REACH API](KALTURA_REACH_API.md)** — AI-powered quiz generation (serviceFeature=12)
- **[Content Lab API](KALTURA_CONTENT_LAB_API.md)** — AI quiz generation widget
- **[Gamification API](KALTURA_GAMIFICATION_API.md)** — Quiz scores as gamification inputs
- **[Analytics Reports API](KALTURA_ANALYTICS_REPORTS_API.md)** — Quiz engagement analytics
