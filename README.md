# Kaltura API Guides

Comprehensive, live-tested API guides for [Kaltura](https://www.kaltura.com/) — the leading video platform. Written for **AI agents and developers** building integrations.

Every guide uses `curl` examples with shell variables, follows a consistent structure, and has a companion test script that validates every documented endpoint against the live Kaltura API.

## Guides

| Guide | Description | Tests |
|-------|-------------|-------|
| [Session (KS) Guide](KALTURA_SESSION_GUIDE.md) | Kaltura Session generation and management | — |
| [AppTokens API](KALTURA_APPTOKENS_API.md) | Secure server-to-server auth without admin secrets | 17 tests |
| [eSearch API](KALTURA_ESEARCH_API.md) | Unified search across entries, captions, metadata | — |
| [Upload & Delivery API](KALTURA_UPLOAD_AND_DELIVERY_API.md) | Upload, chunked ingest, playback URLs, thumbnails | 25 tests |
| [Player Embed Guide](KALTURA_PLAYER_EMBED_GUIDE.md) | Player v7 embed (iframe + JavaScript) | — |
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

- **Agent-first** — Written so an AI agent can read top-to-bottom and build integrations
- **Language-agnostic** — All examples use `curl` with shell variables; adapt to any language
- **Live-tested** — Every guide has companion tests that run against the real Kaltura API
- **Positive framing** — Guides document what works and how to use it, with no ambiguity

## Project Structure

```
├── KALTURA_*_API.md          # API guides
├── KALTURA_*_GUIDE.md        # Non-API documentation
├── PLAN.md                   # Roadmap and full API landscape
├── CLAUDE.md                 # AI agent project instructions
└── tests/
    ├── .env.example          # Template for API credentials
    ├── test_helpers.py       # Shared test utilities
    └── test_*_api.py         # Per-guide test scripts
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

This project is licensed under the MIT License — see [LICENSE](LICENSE) for details.

## Links

- [Kaltura Developer Portal](https://developer.kaltura.com/)
- [Kaltura API Documentation](https://developer.kaltura.com/api-docs/)
- [Kaltura GitHub](https://github.com/kaltura)
- [Kaltura Events MCP Server](https://github.com/kaltura/mcp-events)
