# Kaltura API Guides

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Guides](https://img.shields.io/badge/Guides-10-green.svg)](#guides)
[![Tests](https://img.shields.io/badge/Live--Tested-156_tests-brightgreen.svg)](#guides)
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
| [Session (KS) Guide](KALTURA_SESSION_GUIDE.md) | Kaltura Session generation and management | -- |
| [AppTokens API](KALTURA_APPTOKENS_API.md) | Secure server-to-server auth without admin secrets | 17 tests |
| [eSearch API](KALTURA_ESEARCH_API.md) | Unified search across entries, captions, metadata | -- |
| [Upload & Delivery API](KALTURA_UPLOAD_AND_DELIVERY_API.md) | Upload, chunked ingest, playback URLs, thumbnails | 25 tests |
| [Player Embed Guide](KALTURA_PLAYER_EMBED_GUIDE.md) | Player v7 embed (iframe + JavaScript) | -- |
| [REACH API](KALTURA_REACH_API.md) | AI captions, translation, dubbing, clips | 36 tests |
| [Agents Manager API](KALTURA_AGENTS_MANAGER_API.md) | Automated content processing agents | 15 tests |
| [AI Genie API](KALTURA_AI_GENIE_API.md) | Conversational AI search and RAG | 17 tests |
| [Events Platform API](KALTURA_EVENTS_PLATFORM_API.md) | Virtual events, sessions, speakers, templates | 23 tests |
| [Multi-Stream API](KALTURA_MULTI_STREAM_API.md) | Dual/multi-screen video entries | 23 tests |

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

- Webhooks / Event Notifications
- Live Streaming
- Analytics
- Content Management (Users, Categories, Metadata)
- Virtual Avatar

## License

This project is licensed under the MIT License -- see [LICENSE](LICENSE) for details.

## Links

- [Kaltura Developer Portal](https://developer.kaltura.com/)
- [Kaltura API Documentation](https://developer.kaltura.com/api-docs/)
- [Kaltura GitHub](https://github.com/kaltura)
- [Kaltura Events MCP Server](https://github.com/kaltura/mcp-events)
