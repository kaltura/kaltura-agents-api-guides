@AGENTS.md

# Kaltura API Guides — Agent Instructions

## Project Intent

This project produces developer documentation for **AI agents building applications** on Kaltura's Digital Experience Platform. The platform serves 100+ API services powering rich media experiences across customer-facing, employee-facing, learner-facing, and audience-facing journeys.

The audience is an AI agent that reads top-to-bottom and executes. Every guide must be accurate (live-tested), self-contained, and actionable.

## Critical Workflow Rules

1. **Read before editing.** Before editing any `KALTURA_*.md` file, always `Read` the file first. Your memory of file contents from earlier in this conversation is unreliable after context compaction.

2. **Check the section index.** Each guide has an HTML comment near the top listing all sections. Read it to understand what exists before adding or modifying sections.

3. **Run tests after edits.** Every guide has a companion `tests/test_*.py`. Run it after any guide change: `python3 tests/test_{name}_api.py`

4. **Update cross-references.** When adding or modifying a guide, also update: GUIDE_MAP.md, README.md (table + badges), PLAN.md, SKILL.md, llms.txt, context7.json.

5. **Release workflow.** After pushing to main, check for open release-please PRs (`gh pr list --label "autorelease: pending"`). If the user asked to release, merge the PR to complete the release, then delete the `release-please--branches--main` remote branch and prune local refs. If not releasing, alert user that a release PR is pending.

## Terminology (Official — from Kaltura Glossary)

Use approved product names in all user/customer-facing text:

| Approved Term | What It Is | Legacy/Internal Names to Avoid |
|---------------|-----------|-------------------------------|
| **Content Hubs** | Brandable video portals for sharing media | KMS, MediaSpace, Video Portal |
| **LMS Extensions** | LTI integration into LMS platforms | KAF (OK in technical/architectural contexts) |
| **Rich Media CMS** | Admin backend for managing media, users, metadata | KMC |
| **Kaltura Room** | Virtual classroom / meeting engine | Newrow, NR2, KME |
| **Live Studio** | Self-produced live broadcasts | Town Halls, Kwebcast, External Broadcast |
| **Content Lab** | AI repurposing (clips, quizzes, summaries) | — |
| **REACH** | Marketplace for add-on enrichment services (credits-based) | — |
| **VPaaS** | Video Platform as a Service — the underlying API infrastructure | (Valid technical term, OK to use in developer docs) |
| **KMS Admin** | Admin backend controlling Content Hubs & LMS Extensions | — |
| **Agentic Avatars** | Conversational AI video avatars | — |
| **Kaltura Genies** | Conversational AI search (text/voice) | AI Class Genie, AI Work Genie |

**Key distinctions:**
- "VPaaS" = the API infrastructure layer. It is NOT a synonym for multi-account management.
- "KAF" is acceptable in technical/architectural documentation (this repo). Avoid in customer-facing UI text.
- "KMS" only when discussing the specific front-end component in technical contexts. Use "Content Hubs" for the solution.

## Documentation Standards

### Structure (every guide)

- Header block: `# Title`, 1-2 sentence description, `**Base URL:**`, `**Auth:**`, `**Format:**` (trailing double-spaces for line breaks)
- `<!-- Sections: ... -->` index comment immediately after header
- `# 1. When to Use` through numbered sections (`# N.` with H1)
- **Final 3 sections must be in this exact order:**
  - `# N-2. Error Handling`
  - `# N-1. Best Practices` (may include `## Common Integration Patterns`, `## Multi-Region CDN` as subsections)
  - `# N. Related Guides` — format: `- **[Name](FILENAME.md)** — One-line description` (bold link, em dash `—`)

### Writing Rules

- **Positive framing only.** State what to do: "Use Y to accomplish this." Never write "Don't do X", "avoid X", "never X", "X will fail if...", or "X won't work." AI agents follow positive instructions more reliably than prohibitions. If behavior matters, frame it as the correct action: "Use `flavorAsset.getUrl` for flavor URLs — it handles CDN routing and tokenization" (not "Don't construct flavor URLs manually").
- **Language-agnostic.** All server-side API examples use `curl` with shell variables. JavaScript/HTML only for browser-based components (Player, widgets).
- **Self-contained.** No external links. Inline all information an agent needs. Source repos and "learn more" URLs are research aids — keep them out of published guides.
- **Actionable instructions only.** Every instruction must be something an AI agent can execute. Replace "contact support" with specific prerequisite statements: "Requires X configured on your account (one-time setup by your Kaltura account team)."
- **Minimal prose.** Tables for structured data. Let examples speak. Commentary only when behavior is non-obvious.
- **Trailing double-spaces** on lines that must render as separate lines (header block, multi-line list items).
- **No emojis** unless explicitly requested.
- **Active voice, simple language.** Address the reader as "you". Avoid jargon and business-speak.
- **Platform scale.** "100+ API services", "a dozen client libraries."

### curl Standards

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/{service}/action/{action}" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "param[key]=value"
```

- Always `format=1` for JSON responses
- One `-d` per line with backslash continuation
- Shell variables: `$KALTURA_SERVICE_URL`, `$KALTURA_KS`, `$KALTURA_PARTNER_ID`, `$KALTURA_ENTRY_ID`
- **No inline comments** inside curl blocks — `#` after `\` continuation breaks the command. Put explanations above the curl block.
- **No hardcoded IDs** in `-d` parameters — use `$KALTURA_ENTRY_ID`, `$CATEGORY_ID`, `$PROFILE_ID`, etc. An agent will copy literal values verbatim.
- **No short variable names** — always use the `$KALTURA_` prefix (`$KALTURA_KS` not `$KS`, `$KALTURA_SERVICE_URL` not `$SERVICE_URL`). This ensures agents export the correct environment variables.

### What NOT to Document

- Actions that return `SERVICE_FORBIDDEN` with a customer KS
- External links (GitHub repos, knowledge base URLs, "learn more")
- Deprecated features (v2 player, legacy module names in user-facing text)
- Negative framing ("don't do X", "X will fail if...")
- `media.addFrom*` convenience methods (`addFromUrl`, `addFromEntry`, `addFromFlavorAsset`) — guide agents to use `media.addContent` with the appropriate resource type (`KalturaUrlResource`, `KalturaEntryResource`, `KalturaAssetResource`)

## Playbook Workflow Rules

Playbooks live in `playbooks/` and follow [playbooks/PLAYBOOK_STANDARDS.md](playbooks/PLAYBOOK_STANDARDS.md). Key rules:

1. **Read PLAYBOOK_STANDARDS.md before writing any playbook.**
2. **Every playbook must have a companion E2E test** in `playbooks/tests/`.
3. **Playbooks span 3+ APIs** — if it only uses one service, it belongs in that guide.
4. **Problem-first naming** — file names match what developers search for.
5. **Opinionated with decision points** — recommend approaches and explain trade-offs.

## Current State

50 guides, 960+ live tests, 1 playbook. Conventional Commits enforced (header under 72 chars). Version managed by release-please.

## Quick References

- Full standards: [AGENTS.md](AGENTS.md)
- Guide navigation: [GUIDE_MAP.md](GUIDE_MAP.md)
- Roadmap: [PLAN.md](PLAN.md)
- Playbook standards: [playbooks/PLAYBOOK_STANDARDS.md](playbooks/PLAYBOOK_STANDARDS.md)
- Common mistakes: [.claude/rules/common-pitfalls.md](.claude/rules/common-pitfalls.md)
- Test patterns: [.claude/rules/test-standards.md](.claude/rules/test-standards.md)
