@AGENTS.md

# Kaltura API Guides — Agent Instructions

## Critical Workflow Rules

1. **Read before editing.** Before editing any `KALTURA_*.md` file, always `Read` the file first. Your memory of file contents from earlier in this conversation is unreliable after context compaction.

2. **Check the section index.** Each guide has an HTML comment near the top listing all sections. Read it to understand what exists before adding or modifying sections.

3. **Run tests after edits.** Every guide has a companion `tests/test_*.py`. Run it after any guide change: `python3 tests/test_{name}_api.py`

4. **Update cross-references.** When adding or modifying a guide, also update: GUIDE_MAP.md, README.md (table + badges), PLAN.md, SKILL.md, llms.txt, context7.json.

5. **Release workflow.** After pushing to main, check for open release-please PRs (`gh pr list --label "autorelease: pending"`). If the user asked to release, merge the PR to complete the release, then delete the `release-please--branches--main` remote branch and prune local refs. If not releasing, alert the user that a release PR is pending.

## Guide Structure (all guides follow this)

- Header block: `# Title`, description, `**Base URL:**`, `**Auth:**`, `**Format:**`
- `<!-- Sections: ... -->` index comment
- `# 1. When to Use` through numbered sections
- `# N-2. Error Handling`
- `# N-1. Best Practices`
- `# N. Related Guides`

## Current State

48 guides, 926 live tests, 48 test files. Version managed by release-please (no CHANGELOG.md — release notes are on GitHub Releases). Commit messages must follow Conventional Commits and stay under 72 characters in the header.

## Quick References

- Full standards: [AGENTS.md](AGENTS.md)
- Guide navigation: [GUIDE_MAP.md](GUIDE_MAP.md)
- Roadmap: [PLAN.md](PLAN.md)
- Common mistakes: [.claude/rules/common-pitfalls.md](.claude/rules/common-pitfalls.md)
- Test patterns: [.claude/rules/test-standards.md](.claude/rules/test-standards.md)
- All guides use `curl` with `$KALTURA_SERVICE_URL`, `$KALTURA_KS`, `$KALTURA_PARTNER_ID`
- Always include `format=1` for JSON responses in API v3 calls
