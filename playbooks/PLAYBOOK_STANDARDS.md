# Playbook Standards

This document defines the structure, quality requirements, and conventions for all playbooks in `playbooks/`. Playbooks are opinionated, multi-service workflow guides that solve real developer problems by orchestrating multiple Kaltura APIs together.

## What Makes a Good Playbook

A playbook is NOT a thin wrapper around a single API guide. It must:

1. **Span 3+ API services** with non-obvious orchestration decisions
2. **Solve a real problem** with demonstrated search demand (StackOverflow, forums, customer asks)
3. **Require creative decisions** — architecture choices, trade-offs, conditional logic
4. **Be fully E2E tested** against the live Kaltura API
5. **Be self-contained** — an agent can execute it top-to-bottom without external references

## What Makes a Bad Playbook

Do not create playbooks that:

- Restate what a single API guide already covers (use a link instead)
- Describe a generic "do A then B then C" pipeline with no decision points
- Cover workflows that cannot be tested end-to-end
- Document internal/system-only operations (SERVICE_FORBIDDEN)
- Lack industry-specific use cases (too generic to be useful)

## File Naming

```
playbooks/
├── PLAYBOOK_STANDARDS.md          # This file
├── PLAYBOOK_PLAN.md               # Prioritized roadmap
├── {WORKFLOW_NAME}.md             # Individual playbooks
└── tests/
    └── test_{workflow_name}.py    # Companion E2E test
```

Naming convention:
- **Playbook file:** `SCREAMING_SNAKE_CASE.md` — action-oriented, matches the workflow
- **Test file:** `tests/test_snake_case.py` — mirrors playbook name
- Examples: `UPLOAD_TO_PUBLISH_AUTOMATION.md` → `tests/test_upload_to_publish_automation.py`

## Playbook File Structure

### Header Block (Required)

```markdown
# [Problem-First Title]

[2-3 sentence description: what pain this solves, for whom, what makes it non-trivial.]

**Complexity:** [Simple | Moderate | Advanced]  
**APIs Used:** [Service 1](../KALTURA_X_API.md), [Service 2](../KALTURA_Y_API.md), ...  
**Time to Implement:** [estimate for a developer familiar with Kaltura]  
**Prerequisites:** [what you need — account type, specific features enabled, etc.]

<!-- Sections: 1.Use Cases | 2.Architecture | 3.Phase-1-Name | ... | N-1.Monitoring | N.Testing -->
```

### Required Sections

Every playbook follows this structure:

```markdown
# 1. Use Cases

Industry-specific scenarios. At minimum cover two of: Education, Enterprise, Media/Telecom.
Each use case should be a concrete scenario, not a vague description.

# 2. Architecture Overview

Mermaid diagram showing:
- Data flow across APIs
- Decision points
- Async/polling steps
- Webhook callbacks (if any)

# 3–N-2. Implementation Phases

Numbered phases with:
- Phase title describing the goal
- Decision points called out in bold
- curl examples for every API call
- Expected responses (abbreviated)
- Error handling for that phase
- State to carry forward to next phase

# N-1. Monitoring & Troubleshooting

- What to watch in production
- Common failure modes and recovery
- Polling intervals and timeouts
- Webhook reliability considerations

# N. Testing & Validation

- How to verify the pipeline works E2E
- Pointer to companion test file
- Manual verification steps for browser-testable outcomes
```

### Section Numbering

Use `# 1. Title` (H1 with number) for top-level sections. Use `## 1.1 Subtitle` for subsections within a phase. This matches the API guide convention.

## curl Example Standards

Follow the same conventions as API guides (defined in AGENTS.md):

```bash
# API v3 (form-encoded)
curl -X POST "$KALTURA_SERVICE_URL/service/{service}/action/{action}" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "param[key]=value"

# Modern JSON APIs (Events, Agents, Genie)
curl -X POST "$KALTURA_BASE_URL/endpoint" \
  -H "Authorization: Bearer $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d '{"key": "value"}'
```

- Shell variables: `$KALTURA_SERVICE_URL`, `$KALTURA_KS`, `$KALTURA_PARTNER_ID`
- Always include `format=1` for API v3 JSON responses
- One `-d` parameter per line with backslash continuation
- Show the response inline (abbreviated) after each call

## Decision Points

Playbooks must contain explicit decision points — places where the developer chooses between approaches based on their requirements. Format:

```markdown
**Decision: Captioning strategy**

| Approach | When to Use | Trade-off |
|----------|------------|-----------|
| Machine ASR (REACH serviceType=1) | Speed over accuracy, internal content | Fast (minutes), ~85-95% accuracy |
| Human captioning (REACH serviceType=2) | Compliance/legal, external content | Slow (hours/days), 99%+ accuracy |
| Hybrid (machine then human review) | High volume with compliance needs | Balance of speed and accuracy |
```

## Architecture Diagrams

Use Mermaid `flowchart TD` or `sequenceDiagram` syntax:

```markdown
```mermaid
flowchart TD
    A[Upload Video] --> B{File or URL?}
    B -->|File| C[uploadToken.add → upload → addContent]
    B -->|URL| D[media.add → addContent with KalturaUrlResource]
    C --> E[Poll for READY status]
    D --> E
    E --> F[Trigger REACH captioning]
    F --> G[Webhook: captions complete]
    G --> H[Categorize & publish]
```​
```

## Testing Standards

Every playbook requires a companion test in `playbooks/tests/`. Tests follow the same conventions as API guide tests (see `.claude/rules/test-standards.md`) with these additions:

### Playbook Test Structure

```python
#!/usr/bin/env python3
"""E2E validation of [Workflow Name]. Covers: [phases listed]"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'tests'))
from test_helpers import kaltura_post, TestRunner, PARTNER_ID, KS, SERVICE_URL

state = {}

def main():
    runner = TestRunner("[Workflow Name] — E2E Pipeline Validation")

    # ════════════════════════════════════════════
    # Phase 1: [matches playbook phase]
    # ════════════════════════════════════════════
    def test_phase_1():
        """Validates [what this phase does]."""
        # ...

    runner.run_test("phase1.step — description", test_phase_1)

    # Continue for each phase...

    # Cleanup & Summary
    keep = "--keep" in sys.argv
    if not keep:
        if sys.stdin.isatty():
            input("Press Enter to clean up...")
        runner.cleanup()

    success = runner.summary()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
```

### Test Requirements

- Tests validate the **full pipeline**, not individual API calls (those are in guide tests)
- Register cleanup immediately after resource creation, before assertions
- Each phase maps to a section in the playbook
- Tests must pass with a standard customer admin KS
- Support `--keep` flag for manual inspection
- Import shared helpers from `../../tests/test_helpers.py`

## Writing Style

- **Problem-first framing.** Open with the pain point, not the solution
- **Positive instructions.** "Use REACH serviceType=1 for machine captioning" not "Don't use manual captioning when speed matters"
- **Opinionated.** Recommend specific approaches with rationale — agents need clear direction
- **Concise.** Let curl examples speak. Prose only when behavior is non-obvious or a decision needs context
- **No external links.** All information must be self-contained. Reference other repo files with relative paths
- **Industry callouts.** Use concrete scenarios: "A university with 50,000 lecture recordings" not "an organization with many videos"

## Cross-Referencing

### From Playbooks to Guides

Link to API guides for deep-dive reference:

```markdown
For full `uploadToken` lifecycle details, see [Upload & Ingestion](../KALTURA_UPLOAD_AND_INGESTION_API.md#3-upload-lifecycle).
```

### From Guides to Playbooks

Each API guide's "Related Guides" section should link relevant playbooks:

```markdown
- **[Upload-to-Publish Automation](playbooks/UPLOAD_TO_PUBLISH_AUTOMATION.md)** — Zero-touch pipeline: ingest, caption, enrich, categorize, publish
```

## Commit Messages

```
feat(playbooks): add Upload-to-Publish Automation with 12 E2E tests
fix(playbooks): correct REACH webhook payload in accessibility pipeline
test(playbooks): add meeting recording lifecycle validation
```

Scope is always `playbooks` or `playbooks/{name}` for targeted fixes.

## Publishing Checklist

Before merging a new playbook:

- [ ] Follows this standards document exactly
- [ ] Has companion test in `playbooks/tests/`
- [ ] All tests pass against live Kaltura API
- [ ] Architecture diagram renders correctly
- [ ] Decision points have clear trade-off tables
- [ ] At least 2 industry-specific use cases
- [ ] Cross-references added to relevant API guide "Related Guides" sections
- [ ] Added to `playbooks/PLAYBOOK_PLAN.md` as completed
- [ ] Added to `GUIDE_MAP.md` (Playbooks section)
- [ ] Added to `context7.json` focus list
- [ ] Added to `llms.txt`
- [ ] Commit uses conventional format with `feat(playbooks)` prefix
