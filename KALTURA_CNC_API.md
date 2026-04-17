# Kaltura Chat & Collaborate (CnC) API

The Chat & Collaborate (CnC) component provides real-time communication and audience interaction alongside video content. It powers the collaboration layer in Kaltura virtual events and MediaSpace content pages.

**Base URL:** Managed by the Events Platform — CnC is activated within event sessions, not via a standalone URL  
**Auth:** Managed by the Events Platform — CnC uses the event session's authentication context  
**Format:** Embedded automatically within Kaltura event pages  


# 1. When to Use

- **Virtual events and webinars** — Add real-time audience chat and Q&A alongside live or recorded sessions  
- **Content hubs** — Enable discussion threads and collaboration on media content pages  
- **Learning platforms** — Facilitate student-instructor interaction alongside course videos  


# 2. Prerequisites

- **Kaltura Session (KS)** — An ADMIN KS (type=2) is needed for configuring CnC settings and managing event sessions. Attendee access is managed automatically by the Events Platform authentication context. See the [Session Guide](KALTURA_SESSION_GUIDE.md) for KS generation details.  
- **CnC feature enabled** — The account must have the Chat & Collaborate feature enabled as part of a Kaltura Events or Enterprise subscription.  
- **Events Platform** — CnC is activated within event sessions created through the [Events Platform API](KALTURA_EVENTS_PLATFORM_API.md). Configure event sessions with CnC modules (chat, Q&A, polls) enabled.  


# 3. Features

CnC provides a suite of collaboration modules that appear as panels alongside the video player:

| Module | Description |
|--------|-------------|
| **Group Chat** | Real-time text chat for all participants. Messages appear in chronological order with sender names and timestamps. Supports emoji reactions on messages. |
| **Q&A** | Structured question-and-answer panel. Attendees submit questions; moderators can review, approve, answer publicly, or answer privately. Supports upvoting to surface popular questions. |
| **Polls** | Live polling during sessions. Presenters create multiple-choice polls, attendees vote, and results display in real-time. |
| **Announcements** | One-way messages from moderators/presenters to all participants. Appear prominently in the chat area. |
| **Reactions** | Emoji reactions (applause, thumbs up, etc.) that float across the screen during live sessions. |


# 4. Integration

CnC is embedded as part of the Kaltura Events Platform or MediaSpace experience. It is not a standalone widget with a public embed API — it is automatically included when you create virtual event sessions through the Events Platform.

**How CnC is activated:**

1. Create a virtual event with sessions via the [Events Platform API](KALTURA_EVENTS_PLATFORM_API.md)  
2. Configure session settings to enable chat, Q&A, and/or polls  
3. When attendees join the event page, the CnC panels load automatically alongside the video player  
4. Moderators manage chat and Q&A through the event moderation interface  

**Configuration through Events Platform:**

- **Enable/disable modules** — Control which CnC features (chat, Q&A, polls) are available per session  
- **Moderation settings** — Set whether Q&A requires moderator approval before questions are visible  
- **Anonymity** — Configure whether attendees can post anonymously  
- **Pre/post-event behavior** — Control whether chat is available before the session starts or after it ends  


# 5. Data Access

Chat and Q&A data from events can be accessed through the Events Platform reporting endpoints. Use the analytics report types for virtual events to retrieve engagement metrics including chat message counts, Q&A participation, and poll responses. See the [Analytics Reports API](KALTURA_ANALYTICS_REPORTS_API.md) for event-specific report types (3009, 3010).


# 6. Error Handling

- **Chat not appearing in event page** — Verify the session has chat enabled in its configuration. CnC modules only load for sessions where they are explicitly enabled via the Events Platform settings.  
- **Q&A questions not visible** — If Q&A moderation is enabled, submitted questions require moderator approval before appearing to other attendees. Check the moderation queue in the event management interface.  
- **Polls not displaying results** — Poll results only appear after the presenter explicitly publishes them. Verify the poll has been activated and its results released.  


# 7. Best Practices

- **Enable only the modules you need.** Disable unused CnC features (chat, Q&A, polls) per session to reduce UI clutter and simplify the attendee experience.  
- **Use moderated Q&A for large events.** Enable moderator approval for Q&A in sessions with more than 50 attendees to manage question volume and maintain quality.  
- **Review engagement data post-event.** Use the analytics report types (3009, 3010) via the [Analytics Reports API](KALTURA_ANALYTICS_REPORTS_API.md) to assess chat and Q&A participation metrics.  


# 8. Related Guides

- **[Experience Components Overview](KALTURA_EXPERIENCE_COMPONENTS_API.md)** — Index of all embeddable components with shared guidelines  
- **[Events Platform](KALTURA_EVENTS_PLATFORM_API.md)** — Virtual events where CnC is embedded together with the Player  
- **[Analytics Reports](KALTURA_ANALYTICS_REPORTS_API.md)** — Event-specific report types for chat and Q&A engagement metrics  
- **[Player Embed Guide](KALTURA_PLAYER_EMBED_GUIDE.md)** — Video playback that CnC panels appear alongside
