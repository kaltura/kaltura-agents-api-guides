# Kaltura API Guides — Project Standards

This project produces Kaltura API documentation for **AI agents building applications** on Kaltura. Every guide must be accurate, tested against the live API, and written so an agent can follow it to build integrations safely, securely, and efficiently.

## Repository Structure

```
Kaltura API Guides/
├── AGENTS.md                              # This file
├── PLAN.md                                # Master roadmap and API landscape
├── KALTURA_SESSION_GUIDE.md               # KS generation and management
├── KALTURA_APPTOKENS_API.md               # Secure auth with AppTokens
├── KALTURA_ESEARCH_API.md                 # Unified search
├── KALTURA_UPLOAD_AND_DELIVERY_API.md     # Upload, ingest, playback URLs
├── KALTURA_PLAYER_EMBED_GUIDE.md          # Player v7 embed (iframe + JS)
├── KALTURA_REACH_API.md                   # AI captions, translation, clips
├── KALTURA_AGENTS_MANAGER_API.md          # Automated content processing
├── KALTURA_AI_GENIE_API.md                # Conversational AI search
├── KALTURA_EVENTS_PLATFORM_API.md         # Virtual events
├── KALTURA_MULTI_STREAM_API.md            # Dual/multi-screen entries
└── tests/                                 # Companion test scripts
```

## Verification Commands

```bash
cd "Kaltura API Guides/tests"
python3 test_multi_stream_api.py           # Run a specific test
python3 test_multi_stream_api.py --keep    # Preserve entries for browser testing
for f in test_*.py; do echo "=== $f ===" && python3 "$f" && echo "PASS" || echo "FAIL"; done
```

All tests must pass against the live Kaltura API before a guide is considered done. If a test fails, the guide is wrong — fix the guide, not the test.

## Philosophy

1. **Positive framing only.** Document what works and how to use it. Never note what won't work or what to avoid — agents get confused by negative instructions.
2. **Language-agnostic.** All API examples use `curl` with shell variables. Agents choose their own language.
3. **Live-tested.** Every guide has a companion test script that validates documented behavior against the real API.
4. **Agent-first.** Write for an AI agent that reads top-to-bottom and executes. Clear structure, explicit parameters, no ambiguity.

## Guide File Structure

### Header Block (Lines 1-7)

```markdown
# Kaltura [Service Name] [API/Guide]

[1-2 sentence description.]

**Base URL:** `https://...` (may differ by region/deployment)
**Auth:** [How to authenticate — KS param, Bearer header, etc.]
**Format:** [Request encoding and response format]
```

### Required Sections

- **Prerequisites** — Kaltura account, KS requirements, API-specific needs
- **Numbered sections** — `# 1. Section Title` (H1 with number), `## 1.1 Subsection` for nesting
- **Related Guides** (final section) — Format: `- **[Display Name](FILENAME.md)** — One-line description`

## curl Example Standards

### Kaltura API v3 (form-encoded)

```bash
curl -X POST "$SERVICE_URL/service/{service}/action/{action}" \
  -d "ks=$KS" \
  -d "format=1" \
  -d "param[key]=value"
```

- Shell variables: `$SERVICE_URL`, `$KS`, `$PARTNER_ID`, `$ENTRY_ID`
- Always include `format=1` for JSON responses
- One `-d` parameter per line with backslash continuation

### Modern JSON APIs (Events Platform, Agents Manager, AI Genie)

```bash
curl -X POST "$BASE_URL/endpoint" \
  -H "Authorization: Bearer $KS" \
  -H "Content-Type: application/json" \
  -d '{"key": "value"}'
```

Auth header formats differ by API:
- **Events Platform & Agents Manager:** `Authorization: Bearer $KS`
- **AI Genie:** `Authorization: KS $KS`
- **API v3:** KS as form parameter (`-d "ks=$KS"`)

## Writing Style

- **No negative framing.** Write "Use UTC format for dates" not "Non-UTC dates are rejected."
- **No language-specific code.** curl only in guides.
- **Minimal commentary.** Let API parameters and examples speak. Prose only when behavior is non-obvious.
- **Tables for structured data.** Parameter lists, status codes, enum values.
- **Inline code for identifiers.** Backticks for parameter names, values, IDs, env vars.
- **No emojis** unless explicitly requested.

## Auth Patterns

| API | Auth Method | KS Notes |
|-----|------------|----------|
| API v3 (media, baseEntry, etc.) | `-d "ks=$KS"` form param | Admin KS with `disableentitlement` for full access |
| Events Platform | `Bearer $KS` header | KS must have `userId` set |
| Agents Manager | `Bearer $KS` header | Standard admin KS |
| AI Genie | `KS $KS` header | Standard admin KS |
| Player embed | KS in URL or JS config | USER KS (type=0) for playback |

## Common Kaltura API Patterns

- **Entry statuses:** -2 (NO_CONTENT), 0 (IMPORT), 1 (PRECONVERT), 2 (READY), 4 (CONVERTING), 7 (DELETED)
- **Upload lifecycle:** `uploadToken.add` → `uploadToken.upload` → `media.add` → `media.addContent`
- **Polling pattern:** Check `baseEntry.get` for `status=2` with interval/timeout
- **Cascade behavior:** Deleting a parent entry may cascade to children
- **Search visibility:** Child entries (with `parentEntryId`) are excluded from default search — use `parentEntryIdEqual` filter
- **Event IDs are integers** (Events Platform), not strings

## Adding a New Guide

1. **Research.** Explore the API surface — endpoints, params, response schemas, auth. Test calls live.
2. **Write the guide.** Follow the header block, numbered sections, curl examples, Related Guides structure.
3. **Create the test file.** `tests/test_{name}.py` — cover every documented endpoint with real API calls.
4. **Run tests.** All tests must pass against the live API.
5. **Cross-reference.** Add to Related Guides sections of existing guides where relevant.
6. **Update PLAN.md.** Add a row to the Completed Guides table.
7. **Iterate.** If tests reveal undocumented behavior, update the guide to match reality.

### Naming Convention

- Guide: `KALTURA_{SERVICE_NAME}_API.md` (or `_GUIDE.md` for non-API docs)
- Test: `tests/test_{service_name}_api.py`

## Detailed Reference

See `.claude/rules/` for detailed standards on specific topics:

- **test-standards.md** — Test file structure, conventions, environment config, test helpers
- **player-testing.md** — Browser-based player testing, Player v7 runtime API
- **common-pitfalls.md** — Known issues and fixes encountered during guide development
