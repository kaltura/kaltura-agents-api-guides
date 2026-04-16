# Kaltura API Guides

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Release](https://img.shields.io/github/v/release/zoharbabin/kaltura-api-guides?label=Release)](https://github.com/zoharbabin/kaltura-api-guides/releases/latest)
[![Guides](https://img.shields.io/badge/Guides-39-green.svg)](#guides)
[![Tests](https://img.shields.io/badge/Live--Tested-777_tests-brightgreen.svg)](#guides)
[![llms.txt](https://img.shields.io/badge/llms.txt-available-purple.svg)](llms.txt)
[![Agent Skill](https://img.shields.io/badge/Agent_Skill-kaltura--api-orange.svg)](.agents/skills/kaltura-api/SKILL.md)
[![Docs Site](https://img.shields.io/badge/Docs-GitHub_Pages-blue.svg)](https://zoharbabin.github.io/kaltura-api-guides/)

[Kaltura](https://corp.kaltura.com/) — The Agentic Digital Experience Platform. Kaltura is powering rich, agentic digital experiences across organizational journeys for customers, employees, learners, and audiences. The Kaltura platform combines intelligent content creation, enterprise-grade content management and intelligence, and multimodal conversational engagement capabilities. Kaltura serves leading enterprises, financial institutions, educational institutions, media and telecom providers, and other organizations worldwide.

These are comprehensive, live-tested API guides written for **AI agents and developers** building integrations on Kaltura.

Every guide uses `curl` examples with shell variables, follows a consistent structure, and has a companion test script that validates every documented endpoint against the live Kaltura API.

## AI Agent Access

These guides are optimized for AI agent consumption through multiple discovery mechanisms:

| Method | How to Use |
|--------|-----------|
| **Agent Skill** | Agents implementing [agentskills.io](https://agentskills.io) auto-discover the [Kaltura API skill](.agents/skills/kaltura-api/SKILL.md) with a capability map and links to each guide |
| **Context7** | Add `use context7` to your prompt — the guides are indexed and searchable via [Context7 MCP](https://context7.com) |
| **llms.txt** | LLM-readable index at [`llms.txt`](llms.txt) following the [llmstxt.org](https://llmstxt.org) standard |
| **Direct** | Clone the repo or read any guide file directly — each is self-contained with curl examples |

## Guides

| Guide | Description | Tests |
|-------|-------------|-------|
| [API Getting Started](KALTURA_API_GETTING_STARTED.md) | API structure, first call, multirequest batching, error handling | 13 tests |
| [Session (KS) Guide](KALTURA_SESSION_GUIDE.md) | Kaltura Session generation and management | 13 tests |
| [AppTokens API](KALTURA_APPTOKENS_API.md) | Secure server-to-server auth without admin secrets | 17 tests |
| [eSearch API](KALTURA_ESEARCH_API.md) | Unified search across entries, captions, metadata | 19 tests |
| [Upload & Delivery API](KALTURA_UPLOAD_AND_DELIVERY_API.md) | Upload, chunked ingest, playback URLs, thumbnails | 34 tests |
| [Player Embed Guide](KALTURA_PLAYER_EMBED_GUIDE.md) | Player v7 embed (iframe + JavaScript) | 14 tests |
| [REACH API](KALTURA_REACH_API.md) | Governed enrichment services marketplace: captions, translation, moderation, 22+ services | 32 tests |
| [REACH — AI Clips](KALTURA_REACH_API.md) | AI clip generation via Content Lab / REACH | 15 tests |
| [Agents Manager API](KALTURA_AGENTS_MANAGER_API.md) | Automated content processing agents | 15 tests |
| [AI Genie API](KALTURA_AI_GENIE_API.md) | Conversational AI search and RAG | 17 tests |
| [Events Platform API](KALTURA_EVENTS_PLATFORM_API.md) | Virtual events, sessions, speakers, templates | 25 tests |
| [App Registry API](KALTURA_APP_REGISTRY_API.md) | Register and manage application instances | 20 tests |
| [User Profile API](KALTURA_USER_PROFILE_API.md) | Per-app user profiles, event attendance lifecycle | 30 tests |
| [Messaging API](KALTURA_MESSAGING_API.md) | Template-based email messaging, delivery tracking, unsubscribe management | 22 tests |
| [Webhooks API](KALTURA_WEBHOOKS_API.md) | HTTP webhooks and email notifications on content events | 34 tests |
| [Multi-Stream API](KALTURA_MULTI_STREAM_API.md) | Dual/multi-screen video entries | 23 tests |
| [User Management API](KALTURA_USER_MANAGEMENT_API.md) | User CRUD, roles (RBAC), groups, login management | 25 tests |
| [Auth Broker API](KALTURA_AUTH_BROKER_API.md) | SSO/SAML auth profiles, app subscriptions, SPA proxy | 13 tests |
| [Categories & Access Control API](KALTURA_CATEGORIES_AND_ACCESS_CONTROL_API.md) | Category hierarchy, membership, entitlement, access control profiles | 28 tests |
| [Custom Metadata API](KALTURA_CUSTOM_METADATA_API.md) | XSD schemas, metadata profiles, appinfo annotations, XSLT transforms | 24 tests |
| [Captions & Transcripts API](KALTURA_CAPTIONS_AND_TRANSCRIPTS_API.md) | Caption assets (SRT/VTT/DFXP), transcripts, multi-language, REACH | 36 tests |
| [Analytics Reports API](KALTURA_ANALYTICS_REPORTS_API.md) | Reports, CSV exports, live analytics, stream health | 35 tests |
| [Analytics Events Collection API](KALTURA_ANALYTICS_EVENTS_COLLECTION_API.md) | Playback/engagement event collection, stats.collect, trackEvent | 16 tests |
| [Gamification API](KALTURA_GAMIFICATION_API.md) | Leaderboards, badges, certificates, lead scoring, rules engine | 47 tests |
| [Content Distribution API](KALTURA_DISTRIBUTION_API.md) | Push content to YouTube, Facebook, FTP, cross-Kaltura via connectors | 84 tests |
| [Syndication Feeds API](KALTURA_SYNDICATION_API.md) | RSS/MRSS/iTunes/Roku feeds for external platforms to pull | 14 tests |
| [Experience Components API](KALTURA_EXPERIENCE_COMPONENTS_API.md) | Index of all embeddable components with shared guidelines | 26 tests |
| [Express Recorder API](KALTURA_EXPRESS_RECORDER_API.md) | Browser-based WebRTC video, audio, and screen recording | — |
| [Captions Editor API](KALTURA_CAPTIONS_EDITOR_API.md) | Interactive caption editing with video/waveform sync | — |
| [Conversational Avatar Embed](KALTURA_CONVERSATIONAL_AVATAR_API.md) | AI-powered conversational video avatar embed | — |
| [Chat & Collaborate (CnC)](KALTURA_CNC_API.md) | Real-time chat, Q&A, polls alongside video content | — |
| [Genie Widget API](KALTURA_GENIE_WIDGET_API.md) | Conversational AI search widget over video library | 7 tests |
| [Media Manager API](KALTURA_MEDIA_MANAGER_API.md) | Browsable media library: select, upload, manage entries | 11 tests |
| [Content Lab API](KALTURA_CONTENT_LAB_API.md) | AI content repurposing: summaries, chapters, clips, quizzes | 9 tests |
| [Agents Widget API](KALTURA_AGENTS_WIDGET_API.md) | Automated content-processing agent management UI | 7 tests |
| [VOD Avatar Studio API](KALTURA_VOD_AVATAR_API.md) | Pre-recorded avatar video generation from scripts | 6 tests |
| [Embeddable Analytics API](KALTURA_ANALYTICS_EMBED_API.md) | Analytics dashboards via iframe + postMessage | — |
| [Unisphere Framework API](KALTURA_UNISPHERE_FRAMEWORK_API.md) | Micro-frontend framework: loader, workspace, services | 21 tests |
| [Multi-Account Management API](KALTURA_MULTI_ACCOUNT_MANAGEMENT_API.md) | Sub-accounts, cross-account auth, multi-account analytics | 6 tests |
| [Moderation API](KALTURA_MODERATION_API.md) | Content flagging, approve/reject queue, AI moderation via REACH | 16 tests |

## Quick Start

### 1. Get a Kaltura Account

Sign up at [developer.kaltura.com](https://developer.kaltura.com/) or use an existing Kaltura account.

### 2. Configure Test Environment

```bash
cd tests
cp .env.example .env
# Edit .env with your Kaltura credentials
```

### 3. Run Tests

```bash
# Run a specific test
python3 tests/test_upload_delivery_api.py

# Run all tests
cd tests
for f in test_*.py; do echo "=== $f ===" && python3 "$f" && echo "PASS" || echo "FAIL"; done
```

## How These Guides Are Different

- **Agent-first** -- Written so an AI agent can read top-to-bottom and build integrations
- **Language-agnostic** -- All examples use `curl` with shell variables; adapt to any language
- **Live-tested** -- Every guide has companion tests that run against the real Kaltura API
- **Positive framing** -- Guides document what works and how to use it, with no ambiguity

## Project Structure

```
├── .agents/skills/kaltura-api/  # Agent Skill (agentskills.io)
├── KALTURA_*_API.md             # API guides
├── KALTURA_*_GUIDE.md           # Non-API documentation
├── AGENTS.md                    # AI agent project instructions
├── context7.json                # Context7 indexing config
├── llms.txt                     # LLM-readable index
├── PLAN.md                      # Roadmap and full API landscape
└── tests/
    ├── .env.example             # Template for API credentials
    ├── test_helpers.py          # Shared test utilities
    └── test_*_api.py            # Per-guide test scripts
```

## Contributing

Contributions are welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

Whether you want to:
- Fix an error in an existing guide
- Add a test for an undocumented edge case
- Write a new guide for an uncovered Kaltura API
- Improve clarity or add missing parameters

All contributions that improve accuracy and coverage are appreciated.

## Roadmap

See [PLAN.md](PLAN.md) for the full Kaltura API landscape and prioritized list of upcoming guides, including:

- Live Streaming
- Playlists
- Scheduling

## License

This project is licensed under the MIT License -- see [LICENSE](LICENSE) for details.

## Links

- [Kaltura Developer Portal](https://developer.kaltura.com/)
- [Kaltura API Documentation](https://developer.kaltura.com/api-docs/)
- [Kaltura GitHub](https://github.com/kaltura)
- [Kaltura Events MCP Server](https://github.com/kaltura/mcp-events)
