# Playbook Plan

**Standards:** [PLAYBOOK_STANDARDS.md](PLAYBOOK_STANDARDS.md)

---

## Tier 1 — Build Next

| # | Playbook | APIs Spanned | Target User |
|---|----------|-------------|-------------|
| 1 | **Accessibility Compliance Pipeline** | Upload, REACH, Captions, Custom Metadata, Analytics, Access Control | Education IT, Compliance |
| 2 | **Analytics & ROI Dashboard** | Analytics Reports, Events Collection, Custom Metadata, eSearch | Training Manager, Marketing |
| 3 | **Upload-to-Publish Automation** | Upload, REACH, Agents Manager, Webhooks, eSearch, Categories | DevOps/Platform |
| 4 | **Secure Video Portal (SSO + RBAC)** | Auth Broker, User Mgmt, Access Control, Categories, Player Config, AppTokens | Enterprise IT |

## Tier 2 — Strategic

| # | Playbook | APIs Spanned | Target User |
|---|----------|-------------|-------------|
| 5 | **Content Moderation & Compliance** | Moderation, REACH (AI), Webhooks, Categories, Access Control | Trust & Safety |
| 6 | **Video Search & Discovery** | eSearch, AI Genie, Categories, Custom Metadata, Genie Widget | Knowledge Mgmt |
| 7 | **Mobile Playback Optimization** | Player Embed, Content Delivery, Thumbnails, Analytics Events | Mobile Dev |
| 8 | **Multilingual Video Localization** | REACH (translation + dubbing), Captions, VOD Avatar, Distribution | Global Comms |
| 9 | **Live Event Production** | Live Streaming, Events Platform, REACH, Analytics, Scheduling | Event Producer |

## Tier 3 — Niche

| # | Playbook | APIs Spanned | Target User |
|---|----------|-------------|-------------|
| 10 | **Meeting Recording Lifecycle** | Drop Folder, Upload, REACH, eSearch, Categories | Enterprise IT |
| 11 | **AI Content Repurposing** | Content Lab, eSearch, Clipping, Player, Distribution | Marketing, L&D |
| 12 | **Interactive Video Training** | Upload, Quiz, Chapters, Interactive Video, Analytics, Gamification | Instructional Design |
| 13 | **Platform Migration** | Upload, Bulk Ops, Custom Metadata, Categories, Drop Folder | Platform Eng |
| 14 | **Avatar-Narrated Training** | VOD Avatar, Upload, REACH, Player, Analytics Events | L&D, HR |

---

## Publishing Checklist

When a playbook ships, update:
- [ ] `GUIDE_MAP.md` (Playbooks section)
- [ ] `context7.json` (focus list)
- [ ] `llms.txt` (add entry)
- [ ] Related API guides ("Related Guides" sections)
- [ ] `PLAN.md` (remove from gaps)
