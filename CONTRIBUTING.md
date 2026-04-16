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

## Commit Messages

This repository uses [Conventional Commits](https://www.conventionalcommits.org/) and automated versioning. Every commit message must follow this format:

```
<type>(<scope>): <description>
```

**Type** determines the version bump:

| Type | When to use | Version bump |
|------|-------------|-------------|
| `feat` | New guide, new major section, new capability | **Minor** (6.2.0 → 6.3.0) |
| `fix` | Correct wrong API docs, fix broken examples, fix tests | **Patch** (6.2.0 → 6.2.1) |
| `test` | Test-only changes (new tests, fix flaky tests) | None (included in next release notes) |
| `docs` | README, CONTRIBUTING, non-guide prose | None |
| `chore` | Meta files, dependencies, formatting | None |
| `ci` | GitHub Actions, workflow changes | None |
| `refactor` | Restructure without content change | None |

**Scope** (optional) identifies the guide or area:

```
feat(moderation): add Moderation API guide with 16 E2E tests
fix(reach): correct serviceFeature enum values 21-23
test(reach): fix cascade failure in combined filter test
chore: update GUIDE_MAP.md cross-references
ci: add commitlint and release-please workflows
```

**Breaking changes** trigger a major version bump. Add `!` after the type:

```
feat!: restructure all guides to new section format
```

Commit messages are validated automatically by CI on every push and pull request. The `Conventional commits` check will report any formatting issues.

### How Releases Work

Releases are fully automated via [release-please](https://github.com/googleapis/release-please):

1. Push commits to `main` with conventional commit messages
2. Release-please opens (or updates) a release PR that accumulates changes
3. When you merge the release PR, it automatically:
   - Bumps `version.txt`
   - Creates a git tag (e.g., `v6.3.0`)
   - Publishes a GitHub Release with notes generated from commit messages

You control when releases happen by choosing when to merge the release PR.

## Pull Request Process

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run relevant tests to verify
5. Submit a pull request with a clear description of what changed and why
6. Ensure the `Conventional commits` CI check passes

## Code of Conduct

Please be respectful and constructive. See [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).
