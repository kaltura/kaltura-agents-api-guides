# Contributing to Kaltura API Guides

Thank you for your interest in improving these guides! Contributions of all kinds are welcome.

## Ways to Contribute

- **Fix errors** in existing guides (wrong parameters, outdated endpoints, typos)
- **Add missing parameters** or response fields to documented endpoints
- **Write new guides** for uncovered Kaltura APIs (see [PLAN.md](PLAN.md) for the roadmap)
- **Add or improve tests** to increase coverage
- **Improve clarity** of explanations or examples

## Guide Standards

All guides follow the conventions in [AGENTS.md](AGENTS.md). Key points:

1. **curl examples only** — No language-specific code. Use shell variables (`$SERVICE_URL`, `$KS`, `$PARTNER_ID`)
2. **Positive framing** — Document what works, not what to avoid
3. **Live-tested** — Every guide needs a companion test in `tests/`
4. **Consistent structure** — Header block, prerequisites, numbered sections, related guides

## Adding a New Guide

1. Research the API surface and test calls against the live API
2. Create `KALTURA_{SERVICE_NAME}_API.md` following the template in [AGENTS.md](AGENTS.md)
3. Create `tests/test_{service_name}_api.py` covering every documented endpoint
4. Run tests: `python3 tests/test_{service_name}_api.py`
5. Add cross-references to Related Guides sections of existing guides
6. Update project files:
   - [PLAN.md](PLAN.md) — add row to Completed Guides table
   - [GUIDE_MAP.md](GUIDE_MAP.md) — add to flywheel tier, dependency graph, and decision tree
   - [AGENTS.md](AGENTS.md) — add to file tree and capability table
   - [README.md](README.md) — add to Guides table with test count
7. Run `python3 scripts/validate_guide_map.py` to verify all cross-references

## Running Tests

```bash
cd tests
cp .env.example .env
# Fill in your Kaltura credentials

# Run one test
python3 test_upload_delivery_api.py

# Run all tests
for f in test_*.py; do echo "=== $f ===" && python3 "$f" && echo "PASS" || echo "FAIL"; done
```

Tests require a valid Kaltura account and admin KS. Some tests create and delete temporary entries.

## Pull Request Process

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run relevant tests to verify
5. Submit a pull request with a clear description of what changed and why

## Code of Conduct

Please be respectful and constructive. See [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).
