# Promotion & Distribution Plan

Actionable checklist for getting maximum reach for the Kaltura API Guides.

## Tier 1: Quick Wins (do first, all low effort)

### AI Agent Discovery

- [ ] **Context7** — Submit at [context7.com/add-package](https://context7.com/add-package). The `context7.json` is already in the repo. Once indexed, any developer typing "use context7" gets Kaltura docs via MCP.

- [ ] **llms.txt directories** — Submit to:
  - [directory.llmstxt.cloud](https://directory.llmstxt.cloud/) — Click "Submit your llms.txt", enter the repo URL
  - Check [llmstxt.org](https://llmstxt.org/) for any additional directories listed

- [ ] **Agent Skills registry** — PR to [anthropics/skills](https://github.com/anthropics/skills) to list the `kaltura-api` skill. This makes it discoverable by Claude Code, VS Code Copilot, and Codex users.

### API Directories

- [ ] **[APIs.guru](https://apis.guru/add-api)** — Submit Kaltura's OpenAPI spec URL. 2,500+ APIs indexed, used by AI agents for API discovery. Requires a machine-readable API definition (OpenAPI/Swagger). Category: Video.

- [ ] **[PublicAPIs.dev](https://publicapis.dev/)** — PR to add Kaltura via their [contributing guide](https://github.com/marcelscruz/public-apis/blob/main/CONTRIBUTING.md). Open-source, well-maintained successor to the Public APIs GitHub repo. Searchable and categorized.

- [ ] **[APIs.io](https://apis.io/)** — Register via an `apis.json` file. Lightweight API discovery standard. Create an `apis.json` in the repo root pointing to Kaltura's API documentation.

- [ ] **[Postman API Network](https://www.postman.com/explore)** — Create a public Postman workspace with collections for each guide's curl examples. Gets indexed automatically. World's largest public API hub.

- [ ] **[public-api-lists](https://github.com/public-api-lists/public-api-lists)** — PR to add under "Video" category. 730+ APIs across 48 categories, 207 contributors. Separate from PublicAPIs.dev.

### GitHub Awesome Lists

- [ ] **[krzemienski/awesome-video](https://github.com/krzemienski/awesome-video)** — PR to add under documentation/API section. 3k+ stars, the primary video dev resource list.

- [ ] **[awesome-selfhosted/awesome-selfhosted](https://github.com/awesome-selfhosted/awesome-selfhosted)** — PR to add a link under the Media Streaming > Video Streaming section (Kaltura CE is already listed). 200k+ stars.

- [ ] **[Kikobeats/awesome-api](https://github.com/Kikobeats/awesome-api)** — PR to add as an API documentation resource.

### GitHub Optimization

- [x] **GitHub Pages** — MkDocs Material site deployed at `zoharbabin.github.io/kaltura-api-guides/` with Kaltura branding, dark/light mode, search, and auto-deploy via GitHub Actions.

- [x] **v1.0.0 Release** — Created with release notes summarizing all 10 guides.

- [x] **CI/CD Automation** — Deploy workflow (MkDocs + llms.txt auto-generation) and link checker workflow both active on push to main.

- [ ] **Social preview image** — Image created at `assets/images/social-preview.png` (1280x640, Kaltura brand flywheel design). Upload via Repo Settings > Social Preview. Shows on every Twitter/LinkedIn/Slack share.

## Tier 2: Community Posts (medium effort, high reach)

### Developer Platforms

- [ ] **Hacker News** — Submit as "Show HN: Live-tested Kaltura API guides built for AI agents" at [news.ycombinator.com/submit](https://news.ycombinator.com/submit). Best posted Tuesday-Thursday, 9-11am ET.

- [ ] **Reddit** — Post to these subreddits (adapt the angle per community):
  - [r/LLMDevs](https://www.reddit.com/r/LLMDevs/) — "Made Kaltura's Digital Experience Platform API docs agent-friendly with Agent Skills + Context7 + llms.txt"
  - [r/ClaudeAI](https://www.reddit.com/r/ClaudeAI/) — Focus on the Agent Skill angle
  - [r/webdev](https://www.reddit.com/r/webdev/) — "Open-sourced 10 live-tested Kaltura API guides for rich media and AI experiences"

- [ ] **Dev.to** — Write an article about making API docs AI-agent-friendly, using this project as the case study. Tags: `#kaltura`, `#api`, `#ai`, `#agents`.

- [ ] **Dev Hunt** — Submit at [devhunt.org](https://devhunt.org/) (open-source Product Hunt alternative for dev tools). Free, GitHub-authenticated.

### Newsletters

- [ ] **TLDR Newsletter** — Submit at [tldr.tech](https://tldr.tech/). One of the largest dev newsletters.

- [ ] **Changelog** — Submit at [changelog.com/news](https://changelog.com/news). 17k email subscribers, 350k monthly podcast listens.

- [ ] **Console.dev** — Submit at [console.dev](https://console.dev/). 22k+ subscribers. They review interesting devtools.

### GEO (Generative Engine Optimization)

- [ ] **Schema.org structured data** — Add JSON-LD `SoftwareSourceCode` and `TechArticle` markup to the MkDocs site via a custom template override. Helps AI systems (ChatGPT, Perplexity, Google AI Overviews) cite the guides in their responses.

- [ ] **Cite sources and stats in guides** — GEO research shows AI engines prefer content with quotations, statistics, and authoritative citations. Review guides for opportunities to add specific numbers and cite official Kaltura docs.

### AI Ecosystem

- [ ] **OpenAI GPT Store** — Create a custom "Kaltura API Assistant" GPT. Upload the guides as knowledge files and add an OpenAPI action spec for key API calls. Publish to the [GPT Store](https://help.openai.com/en/articles/8554397-creating-and-editing-gpts). Puts Kaltura API docs directly inside ChatGPT's ecosystem.

- [ ] **[MkDocs Catalog](https://github.com/mkdocs/catalog)** — PR to add the site to this official curated list of 300+ MkDocs projects. Notable documentation sites are listed alongside plugins.

### Standards-Based Discovery

- [ ] **`/.well-known/ai-plugin.json`** — Host an OpenAI-style plugin manifest on the GitHub Pages domain. Points to the OpenAPI spec and describes the API for AI agent consumption. APIs.guru auto-populates fields from this file.

- [ ] **RFC 9727 `/.well-known/api-catalog`** — IETF standard for API discovery. Host a Linkset JSON at `/.well-known/api-catalog` on the docs domain pointing to API documentation, OpenAPI specs, and llms.txt. Emerging standard that crawlers and AI agents are starting to support.

## Tier 3: Relationship-Based (high impact, requires coordination)

### Kaltura Official Channels

- [ ] **Kaltura Developer Portal** — Contact Kaltura dev relations to get the guides linked from [developer.kaltura.com](https://developer.kaltura.com/).

- [ ] **Kaltura Knowledge Center** — Request inclusion at [knowledge.kaltura.com](https://knowledge.kaltura.com/help).

- [ ] **Move to Kaltura GitHub Organization** — Transfer this repo to the [kaltura](https://github.com/kaltura) GitHub org for official standing, better discoverability, and cross-linking with repos like [kaltura/mcp-events](https://github.com/kaltura/mcp-events). Coordinate with Kaltura's GitHub org admins.

### Stack Overflow

- [ ] **Answer Kaltura questions** — Monitor the [`kaltura` tag](https://stackoverflow.com/questions/tagged/kaltura) and link to relevant guides in answers. Ongoing SEO value.

### Video Tech Communities

- [ ] **Demuxed** — Share in the Demuxed Slack community. Video engineering focused.

- [ ] **Video Dev** — Share in video-dev.org community channels.

## Tracking

Update this checklist as items are completed. For each item, note the date and any resulting metrics (stars, views, traffic).
