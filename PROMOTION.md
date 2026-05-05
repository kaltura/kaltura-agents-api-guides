# Promotion & Distribution Plan

Actionable checklist for getting maximum reach for the Kaltura API Guides.

## Tier 1: Quick Wins (do first, all low effort)

### AI Agent Discovery

- [ ] **Context7** -- Submit at [context7.com/add-package](https://context7.com/add-package). The `context7.json` is already in the repo. Once indexed, any developer typing "use context7" gets Kaltura docs via MCP.

- [ ] **llms.txt directories** -- Submit to:
  - [directory.llmstxt.cloud](https://directory.llmstxt.cloud/) -- 849+ entries, "Submit your llms.txt" button
  - Check [llmstxt.org](https://llmstxt.org/) for any additional directories listed

- [ ] **Agent Skills registries** -- The repo already has a `SKILL.md` and `.agents/skills/` structure. Submit to:
  - [anthropics/skills](https://github.com/anthropics/skills) -- PR to list `kaltura-api` skill. Discoverable by Claude Code, VS Code Copilot, Codex users
  - [skills.sh](https://skills.sh/) -- Vercel's Agent Skills Directory. Browseable leaderboard, installable via `npx skills add`. Compatible with 18+ agents
  - [VoltAgent/awesome-agent-skills](https://github.com/VoltAgent/awesome-agent-skills) -- 1000+ skills, community-curated. PR to add Kaltura
  - Host `/.well-known/skills/index.json` on the GitHub Pages site -- Cloudflare's Agent Skills Discovery RFC. The `npx skills add <url>` CLI auto-discovers from any URL serving this endpoint

### API Directories

- [ ] **[PublicAPIs.dev](https://publicapis.dev/)** -- PR to add Kaltura under "Video" via their [contributing guide](https://github.com/marcelscruz/public-apis/blob/main/CONTRIBUTING.md). Open-source, well-maintained.

- [ ] **[public-api-lists](https://github.com/public-api-lists/public-api-lists)** -- PR to add under "Video" category. 730+ APIs across 48 categories.

- [ ] **[APIs.io](https://apis.io/)** -- Register via an `apis.json` file. 1,362 providers indexed. Create an `apis.json` in the repo root pointing to Kaltura's API documentation.

- [ ] **[APIs.guru](https://apis.guru/add-api)** -- Requires a machine-readable OpenAPI spec URL (not documentation guides). Only relevant if Kaltura publishes an official OpenAPI spec.

- [ ] **Postman API Network** -- An unofficial "Kaltura" workspace exists (created by API Evangelist, marked as unofficial). Create an *official* Kaltura workspace with collections from the guides' curl examples, or contribute to the existing one.

### GitHub Awesome Lists

- [ ] **[krzemienski/awesome-video](https://github.com/krzemienski/awesome-video)** -- PR to add under documentation/API section. 3k+ stars, the primary video dev resource list.

- [ ] **[awesome-selfhosted/awesome-selfhosted](https://github.com/awesome-selfhosted/awesome-selfhosted)** -- Kaltura CE is already listed. Add a link to the API guides alongside it. 200k+ stars. Low priority -- they prefer software listings over documentation.

### GitHub Optimization

- [x] **GitHub Pages** -- MkDocs Material site deployed at `kaltura.md` with search, dark/light mode, auto-deploy.

- [x] **Releases** -- Automated via release-please with conventional commits. v6.5.0 current. 48 guides, 918 live-validated tests.

- [x] **CI/CD** -- Deploy workflow (MkDocs + llms.txt auto-generation), link checker, Experience Components E2E, API validation, commitlint, all active on push.

- [x] **Kaltura GitHub Organization** -- Repo lives at `kaltura/kaltura-agents-api-guides` with org pinning.

- [ ] **Social preview image** -- Upload via Repo Settings > Social Preview. Shows on every Twitter/LinkedIn/Slack share.

## Tier 2: Community Posts (medium effort, high reach)

### Developer Platforms

- [ ] **Hacker News** -- Submit as "Show HN: Live-tested Kaltura API guides built for AI agents" at [news.ycombinator.com/submit](https://news.ycombinator.com/submit). Best posted Tuesday-Thursday, 9-11am ET.

- [ ] **Reddit** -- Post to these subreddits (adapt the angle per community):
  - [r/LLMDevs](https://www.reddit.com/r/LLMDevs/) -- Strict quality rules; frame as educational content, not self-promotion
  - [r/ClaudeAI](https://www.reddit.com/r/ClaudeAI/) -- Focus on Agent Skill + Context7 angle
  - [r/webdev](https://www.reddit.com/r/webdev/) -- "Open-sourced 48 live-tested Kaltura API guides for rich media and AI experiences"

- [ ] **Dev.to** -- Article about making API docs AI-agent-friendly, using this project as a case study. Tags: `#kaltura`, `#api`, `#ai`, `#agents`.

- [ ] **Dev Hunt** -- Submit at [devhunt.org](https://devhunt.org/). Open-source Product Hunt alternative for dev tools. Free, GitHub-authenticated.

### Newsletters

- [ ] **Changelog** -- Submit at [changelog.com/news](https://changelog.com/news). 17k email subscribers, 350k monthly podcast listens. Accepts submissions.

- [ ] **Console.dev** -- Submit at [console.dev](https://console.dev/). 22k+ subscribers. They review 2-3 interesting devtools weekly.

- [ ] **TLDR** -- No public submission form. Requires editorial outreach to their team. One of the largest dev newsletters but inclusion is at their discretion.

### GEO (Generative Engine Optimization)

- [ ] **Schema.org structured data** -- Add JSON-LD `SoftwareSourceCode` and `TechArticle` markup to the MkDocs site via a custom template override. Helps AI systems (ChatGPT, Perplexity, Google AI Overviews) cite the guides in their responses.

- [ ] **Cite sources and stats in guides** -- GEO research shows AI engines prefer content with quotations, statistics, and authoritative citations. Review guides for opportunities to add specific numbers.

### AI Ecosystem

- [ ] **Custom ChatGPT GPT** -- Create a "Kaltura API Assistant" custom GPT with the guides uploaded as knowledge files. OpenAI plugins are deprecated, but custom GPTs with knowledge files remain functional. Discovery is limited without the GPT Store, but direct links work.

- [ ] **[MkDocs Catalog](https://github.com/mkdocs/catalog)** -- PR to add the site to this official curated list of 300+ MkDocs projects.

### Standards-Based Discovery

- [ ] **`/.well-known/agents.json`** -- Open spec ([wild-card-ai/agents-json](https://github.com/wild-card-ai/agents-json), 1.3k stars) for describing API-to-agent contracts. Host on the GitHub Pages domain.

- [ ] **RFC 9727 `/.well-known/api-catalog`** -- IETF standard for API discovery. Host a Linkset JSON at `/.well-known/api-catalog` pointing to documentation, specs, and llms.txt. Fewer than 15 sites implement it -- early adoption is a differentiator.

- [ ] **`robots.txt` Content Signals** -- Cloudflare's standard for declaring AI usage permissions. Add `Content-Signal: ai-input, search` directives. Only 4% of sites have adopted this.

- [ ] **Markdown content negotiation** -- Serve clean markdown when agents send `Accept: text/markdown` header. Cloudflare measured up to 80% token reduction. Already used by Claude Code, OpenCode, and Cursor.

- [ ] **Scan with [isitagentready.com](https://isitagentready.com/)** -- Cloudflare's tool (April 2026) that scores agent readiness across discoverability, content, bot access, and protocol discovery. Free and actionable.

## Tier 3: Relationship-Based (high impact, requires coordination)

### Kaltura Official Channels

- [ ] **Kaltura Developer Portal** -- Contact Kaltura dev relations to get the guides linked from [developer.kaltura.com](https://developer.kaltura.com/).

- [ ] **Kaltura Knowledge Center** -- Request inclusion at [knowledge.kaltura.com](https://knowledge.kaltura.com/help).

### Stack Overflow

- [ ] **Answer Kaltura questions** -- Monitor the [`kaltura` tag](https://stackoverflow.com/questions/tagged/kaltura) and link to relevant guides in answers. Ongoing SEO value.

### Video Tech Communities

- [ ] **Demuxed** -- Share in the Demuxed Slack community. Video engineering focused.

- [ ] **Video Dev** -- Share in video-dev.org community channels.

### MCP Ecosystem

- [ ] **Official MCP Registry** ([registry.modelcontextprotocol.io](https://registry.modelcontextprotocol.io/)) -- If the Kaltura MCP server (`kaltura/mcp-events`) is published as an npm package, register it here.

- [ ] **GitHub MCP Registry** -- GitHub's own MCP server discovery. Register the Kaltura Events MCP server.

## Tracking

Update this checklist as items are completed. For each item, note the date and any resulting metrics (stars, views, traffic).
