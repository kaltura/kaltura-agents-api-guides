#!/usr/bin/env python3
"""Auto-generate llms.txt from KALTURA_*.md guide files.

Scans the repo root for guide files, extracts the H1 title and first
paragraph, and writes a spec-compliant llms.txt (llmstxt.org).
"""

import glob
import os
import re

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Guide categories — order and grouping for the llms.txt output
# Follows the Kaltura flywheel: Foundation → Creation → Management → Experiences
CATEGORIES = {
    "Foundation": [
        "KALTURA_API_GETTING_STARTED.md",
        "KALTURA_SESSION_GUIDE.md",
        "KALTURA_APPTOKENS_API.md",
    ],
    "Content Creation": [
        "KALTURA_UPLOAD_AND_DELIVERY_API.md",
        "KALTURA_MULTI_STREAM_API.md",
        "KALTURA_EXPERIENCE_COMPONENTS_API.md",
        "KALTURA_EXPRESS_RECORDER_API.md",
        "KALTURA_CAPTIONS_EDITOR_API.md",
        "KALTURA_CONVERSATIONAL_AVATAR_API.md",
        "KALTURA_CNC_API.md",
        "KALTURA_GENIE_WIDGET_API.md",
        "KALTURA_MEDIA_MANAGER_API.md",
        "KALTURA_CONTENT_LAB_API.md",
        "KALTURA_AGENTS_WIDGET_API.md",
        "KALTURA_VOD_AVATAR_API.md",
        "KALTURA_ANALYTICS_EMBED_API.md",
        "KALTURA_CUE_POINTS_API.md",
        "KALTURA_QUIZ_API.md",
        "KALTURA_CHAPTERS_AND_SLIDES_API.md",
        "KALTURA_ANNOTATIONS_API.md",
        "KALTURA_AD_CUE_POINTS_API.md",
        "KALTURA_CODE_CUE_POINTS_API.md",
    ],
    "Content Management": [
        "KALTURA_ESEARCH_API.md",
        "KALTURA_CATEGORIES_AND_ACCESS_CONTROL_API.md",
        "KALTURA_CUSTOM_METADATA_API.md",
        "KALTURA_CAPTIONS_AND_TRANSCRIPTS_API.md",
        "KALTURA_USER_MANAGEMENT_API.md",
        "KALTURA_MODERATION_API.md",
    ],
    "AI Services": [
        "KALTURA_REACH_API.md",
        "KALTURA_AGENTS_MANAGER_API.md",
        "KALTURA_AI_GENIE_API.md",
    ],
    "Analytics & Events": [
        "KALTURA_ANALYTICS_REPORTS_API.md",
        "KALTURA_ANALYTICS_EVENTS_COLLECTION_API.md",
        "KALTURA_WEBHOOKS_API.md",
    ],
    "Experiences": [
        "KALTURA_PLAYER_EMBED_GUIDE.md",
        "KALTURA_EVENTS_PLATFORM_API.md",
        "KALTURA_GAMIFICATION_API.md",
        "KALTURA_MESSAGING_API.md",
        "KALTURA_UNISPHERE_FRAMEWORK_API.md",
    ],
    "Distribution & Syndication": [
        "KALTURA_DISTRIBUTION_API.md",
        "KALTURA_SYNDICATION_API.md",
    ],
    "Administration": [
        "KALTURA_MULTI_ACCOUNT_MANAGEMENT_API.md",
        "KALTURA_AUTH_BROKER_API.md",
        "KALTURA_APP_REGISTRY_API.md",
        "KALTURA_USER_PROFILE_API.md",
    ],
}

OPTIONAL_FILES = {
    "PLAN.md": "Full Kaltura API landscape (100+ services) and prioritized guide roadmap",
    "AGENTS.md": "Project conventions for AI agents contributing to this repo",
}


def extract_description(filepath):
    """Extract H1 title and first meaningful paragraph from a markdown file."""
    with open(filepath, "r") as f:
        lines = f.readlines()

    title = None
    desc_lines = []
    past_title = False

    for line in lines:
        stripped = line.strip()

        # Find H1
        if not title and stripped.startswith("# "):
            title = stripped.lstrip("# ").strip()
            past_title = True
            continue

        if not past_title:
            continue

        # Skip blank lines and metadata lines right after title
        if not stripped:
            if desc_lines:
                break  # End of first paragraph
            continue

        # Skip header block lines (bold fields like **Base URL:**)
        if stripped.startswith("**") and ":" in stripped:
            continue

        # First real paragraph
        desc_lines.append(stripped)

    description = " ".join(desc_lines)
    # Truncate to ~150 chars at word boundary
    if len(description) > 150:
        description = description[:147].rsplit(" ", 1)[0] + "..."

    return title, description


def main():
    output = []

    # Header (required by spec)
    output.append("# Kaltura API Guides")
    output.append("")
    output.append(
        "> Kaltura — The Agentic Digital Experience Platform. Kaltura is "
        "powering rich, agentic digital experiences across organizational "
        "journeys for customers, employees, learners, and audiences."
    )
    output.append("")
    output.append(
        "The Kaltura platform combines intelligent content creation, "
        "enterprise-grade content management and intelligence, and multimodal "
        "conversational engagement capabilities — exposed through 100+ REST "
        "API services. These are live-tested API guides with curl examples "
        "using shell variables, written for AI agents and developers building "
        "integrations. Every guide has companion test scripts validated "
        "against the live Kaltura API."
    )
    output.append("")

    # Categorized guide sections
    for category, files in CATEGORIES.items():
        output.append(f"## {category}")
        output.append("")
        for filename in files:
            filepath = os.path.join(REPO_ROOT, filename)
            if not os.path.exists(filepath):
                continue
            title, description = extract_description(filepath)
            if title and description:
                output.append(f"- [{title}]({filename}): {description}")
            elif title:
                output.append(f"- [{title}]({filename})")
        output.append("")

    # Detect any new KALTURA_*.md files not in CATEGORIES
    known_files = set()
    for files in CATEGORIES.values():
        known_files.update(files)

    all_guides = sorted(glob.glob(os.path.join(REPO_ROOT, "KALTURA_*.md")))
    new_guides = [
        os.path.basename(f) for f in all_guides if os.path.basename(f) not in known_files
    ]
    if new_guides:
        output.append("## Other Guides")
        output.append("")
        for filename in new_guides:
            filepath = os.path.join(REPO_ROOT, filename)
            title, description = extract_description(filepath)
            if title and description:
                output.append(f"- [{title}]({filename}): {description}")
            elif title:
                output.append(f"- [{title}]({filename})")
        output.append("")

    # Optional section
    output.append("## Optional")
    output.append("")
    for filename, description in OPTIONAL_FILES.items():
        filepath = os.path.join(REPO_ROOT, filename)
        if os.path.exists(filepath):
            title, _ = extract_description(filepath)
            display = title or filename
            output.append(f"- [{display}]({filename}): {description}")
    output.append("")

    # Write output
    llms_path = os.path.join(REPO_ROOT, "llms.txt")
    content = "\n".join(output)
    with open(llms_path, "w") as f:
        f.write(content)

    print(f"Generated llms.txt with {sum(len(v) for v in CATEGORIES.values())} categorized guides")
    if new_guides:
        print(f"  + {len(new_guides)} uncategorized guide(s): {', '.join(new_guides)}")


if __name__ == "__main__":
    main()
