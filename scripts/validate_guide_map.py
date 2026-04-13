#!/usr/bin/env python3
"""Validate GUIDE_MAP.md cross-references against actual guide files.

Checks:
1. All guides listed in GUIDE_MAP.md exist as files
2. All KALTURA_*.md files are listed in GUIDE_MAP.md
3. All cross-references in guide Related Guides sections point to existing files
4. No broken markdown links to .md files
"""

import os
import re
import sys

GUIDE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GUIDE_MAP = os.path.join(GUIDE_DIR, "GUIDE_MAP.md")

# Files that are not API guides (excluded from validation)
EXCLUDED_FILES = {
    "AGENTS.md", "PLAN.md", "README.md", "CONTRIBUTING.md",
    "CODE_OF_CONDUCT.md", "GUIDE_MAP.md", "PLAN_ENRICHMENT_DRAFT.md",
}


def find_guide_files():
    """Find all KALTURA_*.md files in the guide directory."""
    guides = set()
    for f in os.listdir(GUIDE_DIR):
        if f.startswith("KALTURA_") and f.endswith(".md"):
            guides.add(f)
    return guides


def extract_md_links(filepath):
    """Extract all markdown links to .md files from a file."""
    links = set()
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    # Match [text](file.md) patterns
    for match in re.finditer(r'\[([^\]]+)\]\(([^)]+\.md)\)', content):
        link_target = match.group(2)
        # Skip URLs and anchors
        if not link_target.startswith("http") and "#" not in link_target:
            links.add(link_target)
    return links


def extract_guide_map_references():
    """Extract all guide file references from GUIDE_MAP.md."""
    if not os.path.exists(GUIDE_MAP):
        return set()
    return extract_md_links(GUIDE_MAP)


def main():
    errors = []
    warnings = []

    # 1. Find all actual guide files
    actual_guides = find_guide_files()
    print(f"Found {len(actual_guides)} guide files (KALTURA_*.md)")

    # 2. Find all references in GUIDE_MAP.md
    if not os.path.exists(GUIDE_MAP):
        errors.append("GUIDE_MAP.md does not exist")
        print(f"\n{'='*50}")
        print(f"ERRORS: {len(errors)}")
        for e in errors:
            print(f"  ✗ {e}")
        sys.exit(1)

    map_refs = extract_guide_map_references()
    map_guide_refs = {r for r in map_refs if r.startswith("KALTURA_")}
    print(f"Found {len(map_guide_refs)} guide references in GUIDE_MAP.md")

    # 3. Check all GUIDE_MAP references point to existing files
    for ref in sorted(map_refs):
        filepath = os.path.join(GUIDE_DIR, ref)
        if not os.path.exists(filepath):
            errors.append(f"GUIDE_MAP.md references '{ref}' but file does not exist")

    # 4. Check all guide files are in GUIDE_MAP.md
    for guide in sorted(actual_guides):
        if guide not in map_guide_refs:
            warnings.append(f"'{guide}' exists but is not referenced in GUIDE_MAP.md")

    # 5. Check cross-references in each guide's Related Guides section
    broken_links = {}
    for guide in sorted(actual_guides):
        filepath = os.path.join(GUIDE_DIR, guide)
        links = extract_md_links(filepath)
        for link in sorted(links):
            target = os.path.join(GUIDE_DIR, link)
            if not os.path.exists(target) and link not in EXCLUDED_FILES:
                if guide not in broken_links:
                    broken_links[guide] = []
                broken_links[guide].append(link)

    for guide, links in sorted(broken_links.items()):
        for link in links:
            errors.append(f"{guide} has broken link to '{link}'")

    # Report
    print(f"\n{'='*50}")
    if warnings:
        print(f"WARNINGS: {len(warnings)}")
        for w in warnings:
            print(f"  ⚠ {w}")

    if errors:
        print(f"ERRORS: {len(errors)}")
        for e in errors:
            print(f"  ✗ {e}")
        sys.exit(1)
    else:
        print("✓ All cross-references valid")
        print(f"✓ All {len(actual_guides)} guides accounted for in GUIDE_MAP.md")
        sys.exit(0)


if __name__ == "__main__":
    main()
