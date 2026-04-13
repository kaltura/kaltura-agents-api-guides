# Kaltura API Guides — Project Standards

This project produces Kaltura API documentation for **AI agents building applications** on Kaltura. Every guide must be accurate, tested against the live API, and written so an agent can follow it to build integrations safely, securely, and efficiently.

## Repository Structure

```
Kaltura API Guides/
├── AGENTS.md                              # This file
├── PLAN.md                                # Master roadmap and API landscape
├── GUIDE_MAP.md                           # Dependency graph, reading order, decision tree
├── KALTURA_API_GETTING_STARTED.md         # API structure, first call, multirequest, errors
├── KALTURA_SESSION_GUIDE.md               # KS generation and management
├── KALTURA_APPTOKENS_API.md               # Secure auth with AppTokens
├── KALTURA_ESEARCH_API.md                 # Unified search
├── KALTURA_UPLOAD_AND_DELIVERY_API.md     # Upload, ingest, playback URLs
├── KALTURA_PLAYER_EMBED_GUIDE.md          # Player v7 embed (iframe + JS)
├── KALTURA_REACH_API.md                   # AI captions, translation, clips, automation rules
├── KALTURA_AGENTS_MANAGER_API.md          # Automated content processing
├── KALTURA_AI_GENIE_API.md                # Conversational AI search
├── KALTURA_EVENTS_PLATFORM_API.md         # Virtual events
├── KALTURA_MULTI_STREAM_API.md            # Dual/multi-screen entries
├── KALTURA_APP_REGISTRY_API.md            # Application instance registry
├── KALTURA_USER_PROFILE_API.md            # Per-app user profiles & attendance
├── KALTURA_MESSAGING_API.md               # Template-based email messaging
├── KALTURA_WEBHOOKS_API.md                # HTTP webhooks & email via Messaging Service
├── KALTURA_USER_MANAGEMENT_API.md         # User CRUD, roles (RBAC), groups
├── KALTURA_AUTH_BROKER_API.md             # SSO/SAML auth profiles, app subscriptions
├── KALTURA_CATEGORIES_AND_ACCESS_CONTROL_API.md  # Categories, membership, access control
├── KALTURA_CUSTOM_METADATA_API.md         # XSD schemas, metadata profiles, XSLT transforms
├── KALTURA_CAPTIONS_AND_TRANSCRIPTS_API.md # Caption assets, transcripts, multi-language, REACH
├── KALTURA_ANALYTICS_REPORTS_API.md       # Reports, CSV exports, live analytics, stream health
├── KALTURA_ANALYTICS_EVENTS_COLLECTION_API.md  # Playback & engagement event collection
├── KALTURA_GAMIFICATION_API.md            # Leaderboards, badges, certificates, lead scoring
├── KALTURA_DISTRIBUTION_API.md            # Content distribution connectors (push to YouTube/FB/FTP)
├── KALTURA_SYNDICATION_API.md             # Syndication feeds (RSS/MRSS/iTunes/Roku pull)
├── KALTURA_EXPERIENCE_COMPONENTS_API.md   # Express Recorder, Captions Editor, Analytics Widget
├── KALTURA_MULTI_ACCOUNT_MANAGEMENT_API.md # Multi-account management, cross-account analytics
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
5. **Customer-accessible only.** Document only API actions and features that are accessible to customer accounts. Verify every action against the live API with a standard customer KS. If an action returns `SERVICE_FORBIDDEN`, it is an internal/system action and must not be documented. The `disableentitlement` KS privilege bypasses content entitlement checks but does NOT override partner-level service restrictions.
6. **One guide per service boundary.** Each guide covers one cohesive API service or tightly-coupled service cluster. Two services belong in the same guide only if they share API actions, one depends on the other at the API level, or a developer using one always needs the other. Services that merely "relate to entries" (e.g., metadata and captions) are separate guides. When in doubt, split — standalone guides can cross-reference each other, but a bundled guide cannot be unbundled without losing coverage depth.
7. **Self-contained.** Every guide must contain all the information an agent needs to build integrations. Agents must never need to visit external websites, GitHub repositories, knowledge base articles, or other online resources to understand or use an API. If information from an external source is relevant, inline it in the guide. External links used during research are references for the guide author — they do not belong in the published guide.

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

- **Prerequisites / Authentication** — Kaltura account, KS requirements, auth method, required privileges
- **Numbered sections** — `# 1. Section Title` (H1 with number), `## 1.1 Subsection` for nesting
- **Error Handling** — Common error codes and responses for that API. Agents must know what errors to expect and how to handle them.
- **Best Practices** — Security, performance, and integration patterns specific to that API. Guide agents toward production-quality code.
- **Related Guides** (final section) — Format: `- **[Display Name](FILENAME.md)** — One-line description`

## curl Example Standards

### Kaltura API v3 (form-encoded)

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/{service}/action/{action}" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "param[key]=value"
```

- Shell variables: `$KALTURA_SERVICE_URL`, `$KALTURA_KS`, `$KALTURA_PARTNER_ID`, `$KALTURA_ENTRY_ID`
- Always include `format=1` for JSON responses
- One `-d` parameter per line with backslash continuation
- The API v3 backend accepts both `application/x-www-form-urlencoded` and `application/json` bodies. Guides use form-encoded as the default (easier for agents to adapt), but JSON is equally supported.

### Modern JSON APIs (Events Platform, Agents Manager, AI Genie)

```bash
curl -X POST "$KALTURA_BASE_URL/endpoint" \
  -H "Authorization: Bearer $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d '{"key": "value"}'
```

Auth header formats differ by API:
- **Events Platform & Agents Manager:** `Authorization: Bearer $KALTURA_KS`
- **AI Genie:** `Authorization: KS $KALTURA_KS`
- **API v3:** KS as form parameter (`-d "ks=$KALTURA_KS"`)

## Writing Style

- **No negative framing.** Write "Use UTC format for dates" not "Non-UTC dates are rejected."
- **No language-specific code.** curl only in guides. **Exception:** Guides for front-end components (Player embed, editor, Unisphere widgets) include JavaScript/HTML examples where the component's API is inherently browser-based. These guides still use curl for any server-side API calls.
- **Minimal commentary.** Let API parameters and examples speak. Prose only when behavior is non-obvious.
- **Tables for structured data.** Parameter lists, status codes, enum values.
- **Inline code for identifiers.** Backticks for parameter names, values, IDs, env vars.
- **No emojis** unless explicitly requested.
- **No external links.** Guides must not link to GitHub repositories, knowledge base articles, external documentation, or any other website. The only acceptable URLs in guides are: (a) Kaltura API/CDN endpoint URLs used in curl examples and configuration, (b) `example.com` placeholder URLs in code samples, and (c) cross-references to other guides in this project using `[Name](FILENAME.md)` format. If external information is needed, inline it. Source code repositories, reference implementations, and "learn more" links are research aids for the author — they do not belong in the published guide.
- **Trailing double spaces for line breaks.** Lines within a paragraph that should render as separate visual lines must end with `  ` (two trailing spaces). Especially important in header blocks (Base URL / Auth / Format) and multi-line list items. Without them, GitHub and other renderers join lines into one paragraph.
- **No "VPaaS" terminology.** Use "multi-account" or "parent-child account" when describing Kaltura's multi-account model. Explain concepts directly rather than using internal product names.
- **Platform scale.** Refer to the platform as having "100+ API services" and "a dozen client libraries" — not "80+" or other approximations.

## Auth Patterns

| API | Auth Method | KS Notes |
|-----|------------|----------|
| API v3 (media, baseEntry, etc.) | `-d "ks=$KALTURA_KS"` form param | Admin KS with `disableentitlement` for full access |
| Events Platform | `Bearer $KALTURA_KS` header | KS must have `userId` set |
| Agents Manager | `Bearer $KALTURA_KS` header | Standard admin KS |
| AI Genie | `KS $KALTURA_KS` header | Standard admin KS |
| App Registry | `Bearer $KALTURA_KS` header | Admin KS with `ADMIN_BASE` permission |
| User Profile | `Bearer $KALTURA_KS` header | Admin KS with `ADMIN_BASE` permission |
| Messaging | `Bearer $KALTURA_KS` header | Admin KS (type=2) |
| Webhooks (Event Notifications) | `-d "ks=$KALTURA_KS"` form param | Admin KS with `disableentitlement` |
| Distribution & Syndication | `-d "ks=$KALTURA_KS"` form param | Admin KS with `disableentitlement` |
| Auth Broker | `KS $KALTURA_KS` header | Admin KS |
| Player embed | KS in URL or JS config | USER KS (type=0) for playback |

## Common Kaltura API Patterns

- **Entry statuses:** -2 (NO_CONTENT), 0 (IMPORT), 1 (PRECONVERT), 2 (READY), 4 (CONVERTING), 7 (DELETED)
- **Upload lifecycle:** `uploadToken.add` → `uploadToken.upload` → `media.add` → `media.addContent`
- **Polling pattern:** Check `baseEntry.get` for `status=2` with interval/timeout
- **Cascade behavior:** Deleting a parent entry cascades to children — use `baseEntry.list` with `parentEntryIdEqual` to discover children first
- **Search for child entries:** Use `parentEntryIdEqual` filter to retrieve child entries (multi-stream, clip children). Default search returns root entries only.
- **Event IDs are integers** (Events Platform) — pass as `12345`, not `"evt_abc123"`

## Security & Compliance Guidance

Every guide must steer agents toward production-quality, secure integrations:

1. **Use AppTokens in production.** Never embed `adminSecret` in client-facing code. API secrets are permanent — they cannot be regenerated, rotated, or revoked. Create scoped AppTokens with minimal privileges and rotate them periodically. See `KALTURA_APPTOKENS_API.md`.
2. **Scope KS privileges.** Use `edit:entryId`, `sview:*`, `setrole:ROLE`, `iprestrict`, `urirestrict` to limit what a session can access. Prefer USER KS (type=0) over ADMIN KS (type=2) whenever possible.
3. **Set KS expiry.** Default to short-lived sessions (1-4 hours). Use AppToken session start for renewal rather than long-lived admin sessions.
4. **Never embed secrets or KS in mobile/client apps.** API secrets are permanent and cannot be rotated if compromised. KS tokens expire, breaking hardcoded binaries, and users can extract them. Generate KS server-side and pass to client per-session.
5. **Verify webhook signatures.** Always validate HMAC signatures on incoming webhooks using `SHA256(signing_secret + body)`. See `KALTURA_WEBHOOKS_API.md` section 5.
6. **Validate inputs at boundaries.** Sanitize user-provided entry IDs, search terms, and metadata before passing to API calls.
7. **Use Kaltura's built-in capabilities.** Prefer Kaltura REACH for transcription/translation, Agents Manager for automation, Messaging for emails, eSearch for content discovery, and Access Control for content protection — rather than building custom implementations.
8. **Handle errors gracefully.** Every API call can fail — check for error responses, implement retries with backoff for transient failures, and log error codes for debugging.
9. **Protect content with Access Control.** Use `accessControlProfile` to restrict content by IP, domain, geo, or scheduling rules rather than implementing custom access logic.
10. **Use CAN-SPAM compliant email.** When sending emails via the Messaging API, always include unsubscribe links and respect opt-out preferences. See `KALTURA_MESSAGING_API.md`.

## Leveraging Kaltura Capabilities

Agents building on Kaltura should use platform services rather than reimplementing:

| Need | Use Kaltura Service | Guide |
|------|-------------------|-------|
| Transcription, captioning | REACH API (machine or human captions) | `KALTURA_REACH_API.md` |
| Translation | REACH API (40+ languages) | `KALTURA_REACH_API.md` |
| Content summaries, chapters | REACH API (AI summarization) | `KALTURA_REACH_API.md` |
| Auto-process new uploads | Agents Manager (trigger + action rules) | `KALTURA_AGENTS_MANAGER_API.md` |
| Auto-process matching entries | REACH Automation Rules (Boolean/category conditions) | `KALTURA_REACH_API.md` |
| Content search | eSearch API (full-text, facets, operators) | `KALTURA_ESEARCH_API.md` |
| Conversational AI / Q&A | AI Genie (RAG over video library) | `KALTURA_AI_GENIE_API.md` |
| Video player embed | Player v7 (iframe or JS SDK) | `KALTURA_PLAYER_EMBED_GUIDE.md` |
| Email notifications | Messaging API (templates, tracking, unsubscribe) | `KALTURA_MESSAGING_API.md` |
| Event-driven webhooks | Webhooks API (HTTP callbacks with HMAC signing) | `KALTURA_WEBHOOKS_API.md` |
| Virtual events | Events Platform API (sessions, speakers, templates) | `KALTURA_EVENTS_PLATFORM_API.md` |
| Secure auth without secrets | AppTokens (HMAC-based session start) | `KALTURA_APPTOKENS_API.md` |
| Multi-camera / dual-screen | Multi-Stream API (parent-child entries) | `KALTURA_MULTI_STREAM_API.md` |
| User registration & attendance | User Profile API (per-app profiles) | `KALTURA_USER_PROFILE_API.md` |
| User provisioning & RBAC | User Management API (users, roles, groups) | `KALTURA_USER_MANAGEMENT_API.md` |
| SSO/SAML authentication | Auth Broker API (IdP config, app subscriptions) | `KALTURA_AUTH_BROKER_API.md` |
| Content organization | Categories & Access Control (hierarchy, entitlement) | `KALTURA_CATEGORIES_AND_ACCESS_CONTROL_API.md` |
| Custom metadata schemas | Custom Metadata API (XSD schemas, appinfo, XSLT) | `KALTURA_CUSTOM_METADATA_API.md` |
| Captions & transcripts | Captions & Transcripts API (SRT/VTT/DFXP, REACH) | `KALTURA_CAPTIONS_AND_TRANSCRIPTS_API.md` |
| Content distribution | Distribution connectors (YouTube, Facebook, FTP, cross-Kaltura) | `KALTURA_DISTRIBUTION_API.md` |
| Syndication feeds | RSS/MRSS/iTunes/Roku feeds for external platforms | `KALTURA_SYNDICATION_API.md` |
| Analytics reports | Reports API (VOD/Live/Webcast metrics, CSV exports) | `KALTURA_ANALYTICS_REPORTS_API.md` |
| Playback event tracking | Stats collection (quartiles, seeks, buffer events) | `KALTURA_ANALYTICS_EVENTS_COLLECTION_API.md` |
| Gamification & leaderboards | Game Services (badges, certificates, rules engine) | `KALTURA_GAMIFICATION_API.md` |
| Browser recording | Express Recorder (WebRTC recording widget) | `KALTURA_EXPERIENCE_COMPONENTS_API.md` |
| Caption editing | Captions Editor (interactive editing with waveform) | `KALTURA_EXPERIENCE_COMPONENTS_API.md` |
| Multi-account management | Parent-child accounts, cross-account analytics | `KALTURA_MULTI_ACCOUNT_MANAGEMENT_API.md` |

## Adding a New Guide

1. **Research.** Explore the API surface — endpoints, params, response schemas, auth. Test calls live.
2. **Verify accessibility.** Test every action you plan to document with a customer account KS. If any action returns `SERVICE_FORBIDDEN` or requires partner-level permissions beyond standard KS privileges, exclude it from the guide. `disableentitlement` bypasses content entitlement checks but does NOT unlock partner-level service restrictions.
3. **Write the guide.** Follow the header block, numbered sections, curl examples, Related Guides structure.
4. **Create the test file.** `tests/test_{name}.py` — cover every documented endpoint with real API calls.
5. **Run tests.** All tests must pass against the live API. Tests must succeed with actual successful API responses — not by catching expected errors.
6. **Cross-reference.** Add to Related Guides sections of existing guides where relevant. Only link to published guides — never reference planned or future guides.
7. **Update GUIDE_MAP.md.** Add the new guide to the reading order tiers, dependency graph, and decision tree. Run `python3 scripts/validate_guide_map.py` to verify all cross-references are valid.
8. **Update PLAN.md.** Add a row to the Completed Guides table.
9. **Iterate.** If tests reveal undocumented behavior, update the guide to match reality.

### Naming Convention

- Guide: `KALTURA_{SERVICE_NAME}_API.md` (or `_GUIDE.md` for non-API docs)
- Test: `tests/test_{service_name}_api.py`

## Detailed Reference

See `.claude/rules/` for detailed standards on specific topics:

- **test-standards.md** — Test file structure, conventions, environment config, test helpers
- **player-testing.md** — Browser-based player testing, Player v7 runtime API
- **common-pitfalls.md** — Known issues and fixes encountered during guide development
