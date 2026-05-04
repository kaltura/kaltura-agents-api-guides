# Kaltura VOD Avatar Studio API

The VOD Avatar Studio lets you create pre-recorded avatar video presentations programmatically. You can select an AI avatar, write scenes with narration text, optionally use AI to compose scripts from existing video content, and generate a professional video of the avatar delivering the content. The generated video is saved as a standard Kaltura media entry.

**Base URL:** `https://video-avatar.$REGION.ovp.kaltura.com/api/v1` (default region: `nvp1`)  
**Auth:** `Authorization: Bearer $KS` header  
**Format:** JSON request/response  

**Widget URL:** `https://unisphere.nvp1.ovp.kaltura.com/v1` (for browser embedding)

This guide covers two integration paths:
- **Server-side API** (sections 4–10) — Full programmatic control over avatar videos: create, compose, generate, manage  
- **Widget embed** (section 11) — Drop-in browser UI for end users via the Unisphere framework  

For **real-time conversational avatars** that hold live AI-powered conversations, see the [Conversational Avatar Embed](KALTURA_CONVERSATIONAL_AVATAR_API.md).

<!-- Sections: 1.When to Use | 2.Prerequisites | 3.Architecture | 4.Auth & Headers | 5.Avatar Templates & Configuration | 6.Video Project Management | 7.AI Composition | 8.Audio Preview | 9.Video Generation | 10.Complete Server-Side Workflow | 11.Widget Embedding | 12.Error Handling | 13.Best Practices | 14.Related Guides -->


# 1. When to Use

- **Training video production** — Generate professional training videos with AI presenters without recording equipment or on-camera talent  
- **Content localization** — Create avatar-narrated versions of content in multiple languages from translated scripts  
- **Executive communications** — Produce avatar-delivered announcements, updates, or presentations from written scripts  
- **Session highlights** — Turn recorded webinars or meetings into short avatar-narrated summary videos using AI composition  
- **Video explainers** — Generate explainer videos from documents, video captions, or a text brief using AI composition  
- **Automated video pipelines** — Build server-side workflows that create avatar videos without any browser UI  


# 2. Prerequisites

- A valid Kaltura Session (KS) — a user-level session (type=0) is sufficient; no admin privileges required. See [Session Guide](KALTURA_SESSION_GUIDE.md)  
- The VOD Avatar feature enabled on your account — contact your Kaltura account manager  
- For AI composition: source entries must have captions or transcripts available  


# 3. Architecture

The VOD Avatar system has two layers:

| Layer | URL Pattern | Purpose |
|-------|------------|---------|
| Server-side API | `https://video-avatar.$REGION.ovp.kaltura.com/api/v1/` | Video project CRUD, AI composition, video generation, avatar management |
| Unisphere widget | `https://unisphere.$REGION.ovp.kaltura.com/v1/` | Browser-based studio UI (uses the server-side API internally) |

**Server-side API flow:**

1. **List avatar templates** — `avatarTemplate/list` returns the 36 available AI presenters  
2. **Create an avatar** — `avatar/upsert` configures a template with a background  
3. **Create a video project** — `video/add` creates a project with scenes and narration  
4. **Optionally compose with AI** — `video/compose` generates scenes from source content  
5. **Preview audio** — `video/previewAudio` lets you hear the TTS narration before generating  
6. **Generate the video** — `video/generate` starts rendering; poll `video/get` until status is `ready`  
7. **Retrieve the Kaltura entry** — The `entryId` field on the completed video links to the generated media entry  

**Video status lifecycle:**

```
draft ──→ composing ──→ composed ──→ generating ──→ ready
  │          │                          │
  │          ↓                          ↓
  │       compose-error            generate-error
  │          │                          │
  └──────────┘──── resetStatus ─────────┘
```

| Status | Meaning |
|--------|---------|
| `draft` | New project, scenes can be edited |
| `composing` | AI is generating scenes from source content (read-only) |
| `composed` | AI composition complete, scenes populated and editable |
| `compose-error` | AI composition failed — use `resetStatus` to return to `draft` |
| `generating` | Video is being rendered (read-only) |
| `ready` | Video generation complete, `entryId` populated with the Kaltura media entry |
| `generate-error` | Generation failed — use `resetStatus` to return to `composed` or `draft` |

Scenes are read-only while the video is in `composing` or `generating` status — edits are accepted again once the operation completes or is reset.


# 4. Auth & Headers

All server-side API endpoints require a valid Kaltura Session (KS). A user-level KS (type=0) is sufficient — no admin privileges are required. The service authenticates the KS and extracts the `partnerId` and `userId` to scope all data: each user only sees and manages their own videos and avatars.

```bash
# Generate a KS (type=0 user session is sufficient)
KS=$(curl -s -X POST "$KALTURA_SERVICE_URL/service/session/action/start" \
  -d "format=1" \
  -d "secret=$KALTURA_ADMIN_SECRET" \
  -d "partnerId=$KALTURA_PARTNER_ID" \
  -d "type=0" \
  -d "userId=creator@example.com" \
  -d "expiry=86400" | tr -d '"')

# All API calls use Bearer auth with JSON body
AVATAR_API="https://video-avatar.nvp1.ovp.kaltura.com/api/v1"
```

Every request uses:
- **Method:** POST  
- **Header:** `Authorization: Bearer $KS`  
- **Header:** `Content-Type: application/json`  
- **Body:** JSON  

**KS requirements:**
- A plain KS works — standard privileges are sufficient (no `disableentitlement` or custom privileges required)  
- Both `type=0` (USER) and `type=2` (ADMIN) sessions work  
- Data isolation is per-user: each user sees only their own videos and avatars, regardless of session type  
- The partner account must have the VOD Avatar feature enabled. Use `partner/checkConfiguration` to verify:
  ```bash
  curl -s -X POST "$AVATAR_API/partner/checkConfiguration" \
    -H "Authorization: Bearer $KS" \
    -H "Content-Type: application/json" \
    -d '{}'
  ```
  The response lists prerequisite checks with `valid: true/false`. The `source-only-conversion-profile` check must be valid. Contact your Kaltura account manager if checks fail  
- If the KS contains a `urirestrict` privilege, the restricted URI pattern must match the API path  


# 5. Avatar Templates & Configuration

Before creating a video, you need an **avatar** — a specific AI presenter with a chosen background. Avatars are built in two steps:

1. **Pick a template** — Each template is a predefined AI character with a unique face, voice, and speaking style. You select from the available set of predefined characters.  
2. **Configure it as an avatar** — Combine the template with a background (solid color, library image, or custom image from your Kaltura account). This creates a reusable avatar configuration tied to your user.  

The avatar ID is then passed to `video.add` to assign the presenter for that video project.

## Step 1: List Available Templates

Call `avatarTemplate/list` to get the full set of available AI characters. Each template has an `id` (used when creating avatars) and a display `name`:

```bash
curl -s -X POST "$AVATAR_API/avatarTemplate/list" \
  -H "Authorization: Bearer $KS" \
  -H "Content-Type: application/json" \
  -d '{}'
```

**Response:**

```json
{
  "objects": [
    { "id": "jane", "name": "Jane" },
    { "id": "adam", "name": "Adam" },
    { "id": "amir", "name": "Amir" }
  ],
  "totalCount": 36
}
```

The `id` field (e.g., `"jane"`, `"adam"`) is what you pass as `templateId` when creating an avatar. The full set of 36 templates: adam, amir, ben, cristina, david, derek, dylan, elizabeth, gloria, harper, harry, henry, james, jane, jason, jennifer, julia, kevin, larry, lisa, maria, maya, mia, miguel, ming, rita, sam, sara, sharon, sophia, taylor, theodore, tim, victoria, william, yasmin.

## Step 2: Create an Avatar (`avatar/upsert`)

An avatar pairs a template with a background. The `upsert` action is idempotent — if an avatar with the same template + background combination already exists for your user, it returns the existing one instead of creating a duplicate. This means you can safely call `upsert` every time without checking for existing avatars first.

```bash
AVATAR_RESULT=$(curl -s -X POST "$AVATAR_API/avatar/upsert" \
  -H "Authorization: Bearer $KS" \
  -H "Content-Type: application/json" \
  -d '{
    "templateId": "jane",
    "background": { "type": "color", "color": "#CEEEDB" }
  }')
AVATAR_ID=$(echo "$AVATAR_RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")
echo "Avatar ID: $AVATAR_ID"
```

**Request fields:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `templateId` | string | yes | One of the template IDs from `avatarTemplate/list` (e.g., `"jane"`, `"adam"`) |
| `background` | object | yes | Background configuration — structure depends on the `type` field (see below) |

**`background` object:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `type` | string | yes | One of: `"color"`, `"library"`, `"entry"` |
| `color` | string | if type=`"color"` | Hex color code (e.g., `"#CEEEDB"`, `"#FFFFFF"`) |
| `id` | string | if type=`"library"` | Predefined background image ID (lowercase alphanumeric and hyphens only, e.g., `"office-1"`) |
| `entryId` | string | if type=`"entry"` | Kaltura entry ID of a custom background image from your account |

**Background type examples:**

```bash
# Solid color background
'{ "templateId": "adam", "background": { "type": "color", "color": "#1A1A2E" } }'

# Predefined library image
'{ "templateId": "adam", "background": { "type": "library", "id": "office-1" } }'

# Custom image from your Kaltura account
'{ "templateId": "adam", "background": { "type": "entry", "entryId": "0_bg7x9k2m" } }'
```

**Response fields:**

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | The avatar ID — pass this as `avatarId` when creating video projects |
| `templateId` | string | The template used |
| `background` | object | The background configuration |
| `createdAt` | string | ISO 8601 creation timestamp |
| `updatedAt` | string | ISO 8601 last update timestamp |

## Get an Avatar

Retrieve an existing avatar configuration by ID:

```bash
curl -s -X POST "$AVATAR_API/avatar/get" \
  -H "Authorization: Bearer $KS" \
  -H "Content-Type: application/json" \
  -d "{ \"id\": \"$AVATAR_ID\" }"
```

Returns the same response structure as `avatar/upsert`.

## Preview an Avatar

Get a PNG image showing how the avatar looks with its configured background. Use this to display a visual preview before creating videos:

```bash
curl -s -X POST "$AVATAR_API/avatar/preview" \
  -H "Authorization: Bearer $KS" \
  -H "Content-Type: application/json" \
  -d "{ \"id\": \"$AVATAR_ID\" }" \
  --output avatar_preview.png
```

Returns `image/png` binary data. The preview shows the avatar character composited on the configured background.


# 6. Video Project Management

A video project is the central object — it holds the avatar assignment, an ordered list of scenes (each with narration text and an optional layout), and tracks the generation status. You create a project, populate its scenes (manually or via AI composition), then generate the final video.

## Create a Video Project

The `video/add` endpoint creates a new project. You must provide a `name` and an `avatarId` (from section 5). Scenes can be included at creation time or added later via `video/update`.

```bash
VIDEO_RESULT=$(curl -s -X POST "$AVATAR_API/video/add" \
  -H "Authorization: Bearer $KS" \
  -H "Content-Type: application/json" \
  -d "{
    \"name\": \"Q1 Training Overview\",
    \"avatarId\": \"$AVATAR_ID\",
    \"scenes\": [
      {
        \"layoutType\": \"full-screen\",
        \"narration\": { \"text\": \"Welcome to the Q1 training overview.\" }
      },
      {
        \"layoutType\": \"broll\",
        \"narration\": { \"text\": \"Here we see the key metrics from last quarter.\" },
        \"broll\": {
          \"entryId\": \"$BROLL_ENTRY_ID\",
          \"startTime\": 30
        }
      }
    ]
  }")
VIDEO_ID=$(echo "$VIDEO_RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")
echo "Video ID: $VIDEO_ID"
```

### Top-Level Request Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | yes | Display name for the video project |
| `avatarId` | string | yes | The avatar ID returned by `avatar/upsert` — determines which AI presenter appears in the video |
| `scenes` | array of scene objects | no | Ordered list of scenes. Can be empty at creation and populated later via `video/update` or `video/compose` |

### Scene Object

Each element in the `scenes` array represents one segment of the video.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `layoutType` | string enum | no | How the scene is displayed. Default: `"full-screen"` |
| `narration` | object | no | The spoken content for this scene (see narration fields below) |
| `broll` | object | no | Background video configuration (see broll fields below). The broll data is stored regardless of `layoutType` — you can set it up front and switch `layoutType` to `"broll"` later |

**`layoutType` enum:**

| Value | Visual | Description |
|-------|--------|-------------|
| `"full-screen"` | Avatar fills the frame | The avatar character is rendered full-screen with its configured background. Use for introductions, conclusions, and talking-head segments |
| `"broll"` | Avatar overlaid on video | The avatar is composited as a smaller overlay on top of a background video clip. Use when referencing visual content like charts, demos, or slides |

### Narration Object

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `text` | string | yes (if narration provided) | The script text the avatar will speak. This is converted to audio via text-to-speech during generation |
| `avatarId` | string | no | Override the video-level avatar for this specific scene. Omit to use the project's default `avatarId`. Useful for multi-presenter videos where different scenes feature different characters |

### Broll Object

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `entryId` | string | yes (if broll provided) | Kaltura entry ID of the background video to display behind the avatar |
| `startTime` | number | yes (if broll provided) | Start time in seconds within the background video. The clip plays from this point for the duration of the scene's narration |

**B-roll constraints:**
- The same entry can be reused across multiple scenes with different `startTime` values — each reuse does not count as an additional source  
- B-roll entries require a **standard frame rate** (25 or 30 fps). Re-encode PowerPoint exports and other non-standard-rate sources to 25 fps before uploading (e.g., `ffmpeg -i input.mp4 -r 25 -c:v libx264 -profile:v main -c:a aac output.mp4`)  
- Kaltura's transcoding pipeline adds an audio track to video-only uploads, so entries uploaded through the standard upload workflow (uploadToken → media.add → media.addContent) are always compatible with the Avatar renderer  
- The `broll` object is stored on the scene regardless of `layoutType` — you can pre-configure B-roll data and switch `layoutType` to `"broll"` later via `video/update` without re-specifying the entry  

**Narration constraints:**
- Provide narration text as a non-empty string — the API validates this at `video/add` time. Omitting the `narration` object entirely is accepted, but scenes with narration are required for generation  
- Each scene's narration must produce at least **~1.5 seconds of audio** after text-to-speech conversion. Use at least one complete sentence per scene (~4+ words) to meet this threshold  

**TTS speaking rate:**
- The text-to-speech engine speaks at approximately **2.4 words/second** (measured average across varying sentence lengths). When writing narration for B-roll scenes, calculate the maximum safe word count as: `available_clip_duration × 2.1` (using a 15% safety buffer)  
- Use `video/previewAudio` to verify the actual TTS duration for critical scenes before generating

### Response Fields

The response returns the full video object. Key fields:

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | The video project ID — use as `$VIDEO_ID` in all subsequent calls |
| `partnerId` | number | Your Kaltura partner ID |
| `userId` | string | The KS user who created the project |
| `status` | string enum | Current status — starts as `"draft"` (see status lifecycle in section 3) |
| `name` | string | The project name |
| `avatarId` | string | The assigned avatar ID |
| `scenes` | array | The scenes array as submitted |
| `entryId` | string or null | Kaltura media entry ID of the generated video — populated only when status is `"ready"` |
| `composeParams` | object or null | The compose parameters if AI composition was used (see section 7) |
| `createdAt` | string | ISO 8601 creation timestamp |
| `updatedAt` | string | ISO 8601 last update timestamp |

### Scene Examples

**Full-screen scene** — avatar talks directly to camera:

```bash
{ "layoutType": "full-screen", "narration": { "text": "Let me introduce the agenda." } }
```

**B-roll scene** — avatar overlaid on a video clip starting at the 45-second mark:

```bash
{ "layoutType": "broll", "narration": { "text": "As you can see in this demo..." }, "broll": { "entryId": "1_xyz789", "startTime": 45 } }
```

**Scene with per-scene avatar override** — different presenter for this scene:

```bash
{ "layoutType": "full-screen", "narration": { "text": "Hi, I am Adam.", "avatarId": "ADAM_AVATAR_ID" } }
```

**Minimal scene** — layout defaults to `"full-screen"`:

```bash
{ "narration": { "text": "This scene uses the default full-screen layout." } }
```

## Get a Video Project

```bash
curl -s -X POST "$AVATAR_API/video/get" \
  -H "Authorization: Bearer $KS" \
  -H "Content-Type: application/json" \
  -d "{ \"id\": \"$VIDEO_ID\" }"
```

Returns the full `VideoDto` including `status`, `entryId` (if generated), and all scenes.

## Update a Video Project

```bash
curl -s -X POST "$AVATAR_API/video/update" \
  -H "Authorization: Bearer $KS" \
  -H "Content-Type: application/json" \
  -d "{
    \"id\": \"$VIDEO_ID\",
    \"name\": \"Q1 Training — Updated\",
    \"scenes\": [
      {
        \"layoutType\": \"full-screen\",
        \"narration\": { \"text\": \"Updated welcome message for Q1 training.\" }
      }
    ]
  }"
```

**Request fields:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | yes | Video project ID |
| `name` | string | no | Updated name |
| `avatarId` | string | no | Updated avatar ID |
| `scenes` | array | no | Replaces all scenes (removed trailing scenes are cleaned up) |

Scenes are editable only when status is `draft` or `composed` — the API returns `VIDEO_IS_PROCESSING` during active operations.

## List Video Projects

```bash
curl -s -X POST "$AVATAR_API/video/list" \
  -H "Authorization: Bearer $KS" \
  -H "Content-Type: application/json" \
  -d '{
    "filter": { "orderBy": "-createdAt" },
    "pager": { "offset": 0, "limit": 10 }
  }'
```

**Filter options:**

| Field | Type | Values |
|-------|------|--------|
| `orderBy` | string | `"-createdAt"`, `"createdAt"`, `"-updatedAt"`, `"updatedAt"` (default: `"-createdAt"`) |

**Pager options:**

| Field | Type | Description |
|-------|------|-------------|
| `offset` | number | Number of results to skip (0-based) |
| `limit` | number | Maximum number of results to return |

**Response:**

```json
{
  "objects": [ ... ],
  "totalCount": 42
}
```

## Delete a Video Project

```bash
curl -s -X POST "$AVATAR_API/video/delete" \
  -H "Authorization: Bearer $KS" \
  -H "Content-Type: application/json" \
  -d "{ \"id\": \"$VIDEO_ID\" }"
```


# 7. AI Composition

The compose action uses AI to generate scenes from source video content. It analyzes captions and transcripts from the provided entries and creates a structured narration script.

## Compose Scenes from Content

```bash
curl -s -X POST "$AVATAR_API/video/compose" \
  -H "Authorization: Bearer $KS" \
  -H "Content-Type: application/json" \
  -d "{
    \"id\": \"$VIDEO_ID\",
    \"formatType\": \"session-highlights\",
    \"duration\": 120,
    \"entryIds\": [\"$SOURCE_ENTRY_1\", \"$SOURCE_ENTRY_2\"],
    \"userBrief\": \"Focus on the product roadmap announcements\",
    \"generateName\": true
  }"
```

**Request fields:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | yes | Video project ID |
| `formatType` | string | yes | `"session-highlights"` or `"video-explainer"` (see below) |
| `duration` | number | yes | Target video duration in seconds. Min: 1, max: 1200 (20 minutes) |
| `entryIds` | array | yes | Kaltura entry IDs with captions to analyze |
| `userBrief` | string | no | Describes the video goals, style, or focus areas for the AI |
| `generateName` | boolean | no | Auto-generate a video name from the content |

**Format types:**

| Format | Source Content | Output |
|--------|---------------|--------|
| `session-highlights` | Video captions only | Short highlights video narrated by the avatar summarizing the key points |
| `video-explainer` | Video captions + documents | Explainer video combining multiple sources into a coherent narrative |

The compose action:
1. Transitions the video status to `composing`  
2. Extracts captions and documents from the source entries  
3. Uses AI (AWS Bedrock Claude) to generate a structured scene-by-scene narration  
4. Populates the video's `scenes` array with the generated content  
5. Transitions to `composed` on success, or `compose-error` on failure  

Source entries require captions or transcripts — add them via [REACH](KALTURA_REACH_API.md) before composing. The API returns `CAPTIONS_NOT_FOUND` if text content is missing.

**Response:** Returns the video with status `composing`. Poll `video.get` until status changes to `composed`.


# 8. Audio Preview

Preview the text-to-speech narration for a specific scene before generating the full video:

```bash
# Returns audio/mpeg binary
curl -s -X POST "$AVATAR_API/video/previewAudio" \
  -H "Authorization: Bearer $KS" \
  -H "Content-Type: application/json" \
  -d "{ \"id\": \"$VIDEO_ID\", \"sceneId\": 0 }" \
  --output scene_preview.mp3
```

**Request fields:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | yes | Video project ID |
| `sceneId` | number | yes | Scene index (0-based) |

The scene requires narration text to be populated — returns `SCENE_EMPTY_NARRATION` if the text is missing.

Use `previewAudioStream` for streaming playback instead of downloading the full file:

```bash
curl -s -X POST "$AVATAR_API/video/previewAudioStream" \
  -H "Authorization: Bearer $KS" \
  -H "Content-Type: application/json" \
  -d "{ \"id\": \"$VIDEO_ID\", \"sceneId\": 0 }" \
  --output scene_stream.mp3
```


# 9. Video Generation

## Generate the Video

Once scenes are ready (status is `draft` or `composed`), generate the final video:

```bash
curl -s -X POST "$AVATAR_API/video/generate" \
  -H "Authorization: Bearer $KS" \
  -H "Content-Type: application/json" \
  -d "{ \"id\": \"$VIDEO_ID\" }"
```

The generate action:
1. Transitions the video status to `generating`  
2. **Scene generation (parallel):** For each scene, generates TTS audio, then renders the avatar video. Full-screen and b-roll scenes are rendered by separate backend services  
3. **Aggregation:** Stitches all scene videos together. For b-roll scenes, the background video is clipped at the specified `startTime` for the narration duration, and the avatar is composited as an overlay with green-screen replacement. All scenes are normalized to 1920×1080  
4. Uploads the final video as a Kaltura media entry  
5. Sets `entryId` on the video and transitions to `ready`  

**Response:** Returns the video with status `generating`. Poll `video.get` until status becomes `ready`.

## Poll for Completion

```bash
# Poll every 10 seconds until status is "ready" or an error
while true; do
  RESULT=$(curl -s -X POST "$AVATAR_API/video/get" \
    -H "Authorization: Bearer $KS" \
    -H "Content-Type: application/json" \
    -d "{ \"id\": \"$VIDEO_ID\" }")

  STATUS=$(echo "$RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin)['status'])")
  echo "Status: $STATUS"

  if [ "$STATUS" = "ready" ]; then
    ENTRY_ID=$(echo "$RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('entryId',''))")
    echo "Generated entry: $ENTRY_ID"
    break
  elif [ "$STATUS" = "generate-error" ]; then
    echo "Generation failed"
    break
  fi

  sleep 10
done
```

Generation time depends on the number of scenes, narration length, and current queue depth. Simple videos (1–3 full-screen scenes) typically complete in 2–5 minutes. Complex videos with many b-roll scenes can take 10–30 minutes or more. The process has two phases: scene generation (TTS + avatar rendering for each scene, runs in parallel) and aggregation (stitching scenes together with b-roll compositing). The `entryId` field appears on the video object once aggregation begins — its presence indicates scene generation succeeded and stitching is underway.

**Generation error diagnostics:**  
When generation fails, the status becomes `generate-error`. The API response includes only the status change — diagnose using the checklist below. Common causes:
- **Narration too short** — Ensure each scene produces at least ~1.5 seconds of TTS audio (~4+ words). Use one complete sentence per scene  
- **B-roll frame rate** — Confirm b-roll entries use 25 or 30 fps (see b-roll requirements in section 6)  
- **Rendering service busy** — Retry after a few minutes if all content checks pass  

**Isolating the cause:** Start by testing a minimal 1-scene full-screen video. If that succeeds, the issue is b-roll-specific — verify b-roll entry frame rate is 25 or 30 fps and confirm the entry is in `status=2` (Ready). If the 1-scene test also produces `generate-error`, verify narration length (~4+ words per scene) or retry later for a transient service issue.

## Reset Status After Error

If composition or generation fails, reset the status to allow editing and retrying:

```bash
curl -s -X POST "$AVATAR_API/video/resetStatus" \
  -H "Authorization: Bearer $KS" \
  -H "Content-Type: application/json" \
  -d "{ \"id\": \"$VIDEO_ID\" }"
```

**Reset behavior:**
- `compose-error` → resets to `draft`  
- `generate-error` → resets to `composed` (if previously composed) or `draft`  
- Other statuses → returns `CANNOT_RESET_STATUS`  

After resetting, you can modify scenes via `video/update` and call `video/generate` again. The previous `entryId` (if any) is retained — a new generation overwrites it with a fresh entry.


# 10. Complete Server-Side Workflow

This example creates an avatar video from scratch using only the server-side API:

```bash
AVATAR_API="https://video-avatar.nvp1.ovp.kaltura.com/api/v1"

# 1. Create an avatar with a color background
AVATAR=$(curl -s -X POST "$AVATAR_API/avatar/upsert" \
  -H "Authorization: Bearer $KS" \
  -H "Content-Type: application/json" \
  -d '{
    "templateId": "jane",
    "background": { "type": "color", "color": "#CEEEDB" }
  }')
AVATAR_ID=$(echo "$AVATAR" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")

# 2. Create a video project with scenes
VIDEO=$(curl -s -X POST "$AVATAR_API/video/add" \
  -H "Authorization: Bearer $KS" \
  -H "Content-Type: application/json" \
  -d "{
    \"name\": \"Product Update\",
    \"avatarId\": \"$AVATAR_ID\",
    \"scenes\": [
      {
        \"layoutType\": \"full-screen\",
        \"narration\": { \"text\": \"Hello! Today I will walk you through our latest product updates.\" }
      },
      {
        \"layoutType\": \"full-screen\",
        \"narration\": { \"text\": \"We have three major features to cover. Let us get started.\" }
      }
    ]
  }")
VIDEO_ID=$(echo "$VIDEO" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")

# 3. Preview audio for the first scene
curl -s -X POST "$AVATAR_API/video/previewAudio" \
  -H "Authorization: Bearer $KS" \
  -H "Content-Type: application/json" \
  -d "{\"id\": \"$VIDEO_ID\", \"sceneId\": 0}" \
  --output scene0_preview.mp3

# 4. Generate the video
curl -s -X POST "$AVATAR_API/video/generate" \
  -H "Authorization: Bearer $KS" \
  -H "Content-Type: application/json" \
  -d "{\"id\": \"$VIDEO_ID\"}"

# 5. Poll until ready
while true; do
  RESULT=$(curl -s -X POST "$AVATAR_API/video/get" \
    -H "Authorization: Bearer $KS" \
    -H "Content-Type: application/json" \
    -d "{\"id\": \"$VIDEO_ID\"}")
  STATUS=$(echo "$RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin)['status'])")
  echo "Status: $STATUS"
  [ "$STATUS" = "ready" ] || [ "$STATUS" = "generate-error" ] && break
  sleep 10
done

# 6. Get the generated Kaltura entry ID
ENTRY_ID=$(echo "$RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('entryId',''))")
echo "Generated Kaltura entry: $ENTRY_ID"
```

## Manual Storyboard with Multi-Source B-Roll

When you need precise control over the narrative and which video clips appear in each scene, author the scenes yourself instead of using AI composition (section 7). This approach lets you pick exact source entries, set b-roll start times, and interleave full-screen and b-roll layouts in any order.

The key difference: with AI composition (`video/compose`), you provide source entries and the AI decides how to structure the narrative and which clips to reference. With a manual storyboard, you write each scene's narration and explicitly assign b-roll entries and timestamps — the output matches your storyboard exactly.

```bash
AVATAR_API="https://video-avatar.nvp1.ovp.kaltura.com/api/v1"

# 1. Create (or reuse) an avatar
AVATAR=$(curl -s -X POST "$AVATAR_API/avatar/upsert" \
  -H "Authorization: Bearer $KS" \
  -H "Content-Type: application/json" \
  -d '{
    "templateId": "jane",
    "background": { "type": "color", "color": "#1A1A2E" }
  }')
AVATAR_ID=$(echo "$AVATAR" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")

# 2. Create a video with manually authored scenes mixing two source entries
#    - Scenes 0 and 5: full-screen (avatar on background, no b-roll)
#    - Scenes 1 and 4: b-roll from $SOURCE_ENTRY_A (e.g., a keynote recording)
#    - Scenes 2 and 3: b-roll from $SOURCE_ENTRY_B (e.g., a tutorial)
VIDEO=$(curl -s -X POST "$AVATAR_API/video/add" \
  -H "Authorization: Bearer $KS" \
  -H "Content-Type: application/json" \
  -d "{
    \"name\": \"Cloud AI Meets Neural Networks\",
    \"avatarId\": \"$AVATAR_ID\",
    \"scenes\": [
      {
        \"layoutType\": \"full-screen\",
        \"narration\": { \"text\": \"Welcome to this deep dive into two pillars of modern artificial intelligence. Today we connect the dots between cloud infrastructure powering AI at scale and the neural network architectures that make it all possible.\" }
      },
      {
        \"layoutType\": \"broll\",
        \"narration\": { \"text\": \"At AWS re:Invent 2023, Amazon unveiled its vision for generative AI infrastructure. Purpose-built chips like Trainium and Inferentia are redefining how we train and deploy large language models in the cloud.\" },
        \"broll\": { \"entryId\": \"$SOURCE_ENTRY_A\", \"startTime\": 30 }
      },
      {
        \"layoutType\": \"broll\",
        \"narration\": { \"text\": \"But what exactly are these AI models learning? At their core, neural networks process data through layers of interconnected nodes, each layer extracting increasingly abstract features from raw input.\" },
        \"broll\": { \"entryId\": \"$SOURCE_ENTRY_B\", \"startTime\": 10 }
      },
      {
        \"layoutType\": \"broll\",
        \"narration\": { \"text\": \"Consider digit recognition. A neural network takes pixel values as input, detects edges and curves in hidden layers, and outputs a prediction. This elegant architecture is the foundation of modern computer vision.\" },
        \"broll\": { \"entryId\": \"$SOURCE_ENTRY_B\", \"startTime\": 60 }
      },
      {
        \"layoutType\": \"broll\",
        \"narration\": { \"text\": \"Now scale that up to the cloud. Enterprises can run these neural networks across thousands of custom accelerators, making real-time AI inference accessible to any application, anywhere in the world.\" },
        \"broll\": { \"entryId\": \"$SOURCE_ENTRY_A\", \"startTime\": 180 }
      },
      {
        \"layoutType\": \"full-screen\",
        \"narration\": { \"text\": \"The convergence of scalable cloud infrastructure and intelligent neural architectures is accelerating AI innovation faster than ever. Thank you for watching.\" }
      }
    ]
  }")
VIDEO_ID=$(echo "$VIDEO" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")

# 3. Preview a b-roll scene's narration audio before committing to generation
curl -s -X POST "$AVATAR_API/video/previewAudio" \
  -H "Authorization: Bearer $KS" \
  -H "Content-Type: application/json" \
  -d "{\"id\": \"$VIDEO_ID\", \"sceneId\": 1}" \
  --output scene1_preview.mp3

# 4. Generate — skips compose entirely, goes straight from draft to generating
curl -s -X POST "$AVATAR_API/video/generate" \
  -H "Authorization: Bearer $KS" \
  -H "Content-Type: application/json" \
  -d "{\"id\": \"$VIDEO_ID\"}"

# 5. Poll until ready
while true; do
  RESULT=$(curl -s -X POST "$AVATAR_API/video/get" \
    -H "Authorization: Bearer $KS" \
    -H "Content-Type: application/json" \
    -d "{\"id\": \"$VIDEO_ID\"}")
  STATUS=$(echo "$RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin)['status'])")
  echo "Status: $STATUS"
  [ "$STATUS" = "ready" ] || [ "$STATUS" = "generate-error" ] && break
  sleep 10
done

ENTRY_ID=$(echo "$RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('entryId',''))")
echo "Generated Kaltura entry: $ENTRY_ID"
```

**When to use each approach:**

| Approach | When to use |
|----------|-------------|
| **Manual storyboard** (above) | You know exactly what the avatar should say in each scene, which source video clips to show, and at which timestamps. Use for curated presentations, training modules, or any video where the storyboard is predetermined |
| **AI composition** (section 7) | You have source entries and want the AI to analyze their captions and generate a coherent narrative automatically. Use for quick highlights, summaries, or when you do not have a specific script in mind |
| **Hybrid** | Use AI composition to generate a first draft, then call `video/update` to refine the scenes — rewrite narration text, swap b-roll entries, adjust start times, or reorder scenes before generating |


# 11. Widget Embedding

The VOD Avatar Studio is also available as a drop-in browser widget via the Unisphere framework. The widget uses the server-side API internally and provides a full UI for avatar selection, script editing, AI composition, and video generation.

## Basic Embed

```html
<div id="avatar-studio" style="width: 100%; height: 100vh;"></div>
<script type="module">
  import { loader } from "https://unisphere.nvp1.ovp.kaltura.com/v1/loader/index.esm.js";

  const workspace = await loader({
    serverUrl: "https://unisphere.nvp1.ovp.kaltura.com/v1",
    appId: "my-app",
    appVersion: "1.0.0",
    session: { ks: "$KALTURA_KS", partnerId: $KALTURA_PARTNER_ID },
    runtimes: [{
      widgetName: "unisphere.widget.vod-avatars",
      runtimeName: "studio",
      settings: {
        ks: "$KALTURA_KS",
        partnerId: $KALTURA_PARTNER_ID,
        kalturaServerURI: "https://www.kaltura.com"
      },
      visuals: [{
        type: "page",
        target: "avatar-studio",
        settings: {}
      }]
    }]
  });

  const studio = await workspace.getRuntimeAsync(
    "unisphere.widget.vod-avatars",
    "studio"
  );
</script>
```

## Runtime Settings

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `ks` | string | yes | Kaltura Session token — user-level (type=0) is sufficient |
| `partnerId` | number | yes | Partner ID — must be a number, not a string |
| `kalturaServerURI` | string | yes | Kaltura API server URL (e.g., `https://www.kaltura.com`) |
| `entryLink` | function | no | `(entryId: string) => string` — returns a URL for navigating to an entry in the host application |
| `handleShare` | function | no | `(entryId: string) => void` — called when the user clicks share on a generated video |
| `allowedProjectTypes` | array | no | Restricts available project types (see below). Default: all types available |
| `initialView` | string | no | `"videoLibrary"` (default) or `"projectBuilder"` — which view to show on load |
| `additionalEsearchFilters` | object | no | Extra eSearch filters for the media picker when selecting source content |
| `loadThumbnailWithKS` | boolean | no | Append KS to thumbnail URLs for access-controlled thumbnails |

## Project Types

The widget supports three project creation flows, controlled by `allowedProjectTypes`:

| Value | Label | Description |
|-------|-------|-------------|
| `"fromScratch"` | Start from scratch | Create an avatar video by writing scenes manually |
| `"session-highlights"` | Create session highlights | AI composes a highlights video from recorded session captions |
| `"video-explainer"` | Generate a video on any topic | AI composes an explainer from video captions and documents |

```javascript
// Only allow manual creation (no AI composition)
settings: {
  ks: "$KALTURA_KS",
  partnerId: $KALTURA_PARTNER_ID,
  kalturaServerURI: "https://www.kaltura.com",
  allowedProjectTypes: ["fromScratch"]
}
```

## Host-Page Callbacks

```javascript
settings: {
  ks: "$KALTURA_KS",
  partnerId: $KALTURA_PARTNER_ID,
  kalturaServerURI: "https://www.kaltura.com",
  entryLink: (entryId) => `https://myapp.com/media/${entryId}`,
  handleShare: (entryId) => {
    navigator.clipboard.writeText(`https://myapp.com/share/${entryId}`);
  }
}
```

## Workspace Lifecycle

```javascript
// Refresh the KS when it approaches expiry
workspace.session.setData(prev => ({ ...prev, ks: "new-ks-value" }));

// Destroy the workspace when the user navigates away
workspace.kill();
```

## Widget Behavior

- **Auto-save:** Scene edits are auto-saved after a 5-second debounce  
- **Polling:** The widget polls `video.get` every 10 seconds during generation  
- **Max scenes:** The widget enforces 20 scenes in its UI  
- **Default avatar:** `jane` template with `#CEEEDB` background  


# 12. Error Handling

## Server-Side API Errors

| Error Code | Meaning | Resolution |
|------------|---------|------------|
| `VIDEO_IS_PROCESSING` | Scenes cannot be modified while composing or generating (name and metadata updates are still allowed) | Wait for the current operation to complete |
| `VIDEO_CANNOT_COMPOSE` | Video status does not allow composition | Use `resetStatus` if in error state, or wait for current operation |
| `VIDEO_CANNOT_GENERATE` | Video status does not allow generation | Ensure video is in `draft` or `composed` status |
| `VIDEO_IS_BEING_GENERATED` | A generation is already in progress | Wait for it to complete |
| `CANNOT_RESET_STATUS` | Only error statuses can be reset | Only `compose-error` and `generate-error` can be reset |
| `SCENE_NOT_FOUND` | Scene index out of range | Check scene count in the video |
| `SCENE_EMPTY_NARRATION` | Scene has no narration text | Add narration text before previewing audio |
| `CAPTIONS_NOT_FOUND` | Source entries have no captions | Add captions/transcripts to source entries before composing |
| `TOO_MANY_SOURCES` | Too many unique b-roll source entries across all scenes | Reduce the number of distinct `entryId` values. Reuse entries at different `startTime` offsets instead of adding new sources |
| `AVATAR_NOT_FOUND` | Invalid avatar ID | Create an avatar with `avatar.upsert` first |
| `AVATAR_TEMPLATE_NOT_FOUND` | Invalid template ID | Use an ID from `avatarTemplate.list` |
| `BACKGROUND_NOT_FOUND` | Invalid library background ID | Use a valid background ID from the asset library |
| `VIDEO_AVATAR_NOT_CONFIGURED` | Video has no avatar set | Set `avatarId` when creating or updating the video |
| `INVALID_STATUS_TRANSITION` | Status change not allowed | Follow the status lifecycle diagram in section 3 |

## Widget Errors

- **Blank studio** — Verify the KS is valid and `partnerId` is a number (required type). Check browser console for API errors  
- **No avatars available** — Confirm the account has VOD Avatar feature provisioning  
- **Generation produces `generate-error`** — Isolate the cause: test a minimal 1-scene full-screen video first. If that succeeds, check b-roll entries for standard frame rates (25/30 fps) and confirm they are within the 5-source limit. If it also errors, retry later for a transient service issue  
- **KS expiry** — Update reactively: `workspace.session.setData(prev => ({ ...prev, ks: "new-ks" }))`  


# 13. Best Practices

- **Generate the KS server-side.** The KS is visible in client-side code — generate it on your backend and pass it to the widget  
- **Set `partnerId` as a number.** The VOD Avatar widget requires `partnerId` as a number type (e.g., `12345` rather than `"12345"`)  
- **Ensure captions before composing.** Source entries need captions or transcripts for AI composition. Use [REACH](KALTURA_REACH_API.md) to add captions first  
- **Poll at 10-second intervals.** The widget uses 10-second polling; match this in server-side integrations  
- **Handle error states.** Use `resetStatus` to recover from `compose-error` or `generate-error`, then modify scenes and retry  
- **Preview audio before generating.** Use `previewAudio` to verify narration quality — generation is more expensive  
- **Reuse b-roll entries at different start times.** The same entry at different `startTime` offsets gives visual variety without adding sources. Prefer fewer entries with longer durations for maximum reuse  
- **Prepare b-roll entries.** Ensure all b-roll source videos use standard frame rates (25 or 30 fps). Re-encode PowerPoint exports and screen recordings before uploading. Kaltura's transcoding pipeline handles codec conversion and adds audio tracks automatically  
- **Write at least one full sentence per scene.** The API validates narration text at `video/add` time — provide at least one complete sentence (~4+ words) per scene to produce sufficient TTS audio (1.5+ seconds)  
- **Budget narration for b-roll scenes.** TTS speaks at ~2.4 words/second. For b-roll scenes, keep word count below `(clip_duration - startTime) × 2.1` to leave a safety margin. Use `previewAudio` and `ffprobe` to verify actual TTS duration for scenes close to the budget  
- **Use long KS expiry for generation.** Generation can take 10–20 minutes for complex videos. Use 86400s (24h) expiry to ensure the session remains valid throughout  
- **Process generated videos.** The resulting Kaltura entry can be enriched via [REACH](KALTURA_REACH_API.md) (captions, translation), [Content Lab](KALTURA_CONTENT_LAB_API.md) (chapters, summaries), or [Agents](KALTURA_AGENTS_MANAGER_API.md) (automated workflows)  
- **Use HTTPS.** The Unisphere loader and all widget bundles require HTTPS  

## Multi-Region CDN

| Region | Server-Side API | Widget URL |
|--------|----------------|------------|
| NVP1 (US East, default) | `https://video-avatar.nvp1.ovp.kaltura.com/api/v1` | `https://unisphere.nvp1.ovp.kaltura.com/v1` |
| IRP2 (EU West) | `https://video-avatar.irp2.ovp.kaltura.com/api/v1` | `https://unisphere.irp2.ovp.kaltura.com/v1` |
| FRP2 (EU Central) | `https://video-avatar.frp2.ovp.kaltura.com/api/v1` | `https://unisphere.frp2.ovp.kaltura.com/v1` |
| CAP2 (Canada) | `https://video-avatar.cap2.ovp.kaltura.com/api/v1` | `https://unisphere.cap2.ovp.kaltura.com/v1` |
| SGP2 (Singapore) | `https://video-avatar.sgp2.ovp.kaltura.com/api/v1` | `https://unisphere.sgp2.ovp.kaltura.com/v1` |
| SYP2 (Australia) | `https://video-avatar.syp2.ovp.kaltura.com/api/v1` | `https://unisphere.syp2.ovp.kaltura.com/v1` |


# 14. Related Guides

- **[Conversational Avatar Embed](KALTURA_CONVERSATIONAL_AVATAR_API.md)** — Real-time AI avatar conversations via iframe SDK or WebRTC — the live counterpart to this pre-recorded studio  
- **[Unisphere Framework](KALTURA_UNISPHERE_FRAMEWORK_API.md)** — The micro-frontend framework that powers the widget embed: loader, workspace lifecycle, services  
- **[Experience Components Overview](KALTURA_EXPERIENCE_COMPONENTS_API.md)** — Index of all embeddable components with shared guidelines  
- **[REACH API](KALTURA_REACH_API.md)** — Add captions and transcripts to source entries before AI composition, or enrich generated avatar videos  
- **[Content Lab API](KALTURA_CONTENT_LAB_API.md)** — Generate summaries, chapters, or clips from avatar videos  
- **[Session Guide](KALTURA_SESSION_GUIDE.md)** — KS generation and privilege management  
- **[AppTokens API](KALTURA_APPTOKENS_API.md)** — Production token management for secure KS generation  
