# Kaltura Content Delivery API

This guide covers delivering content to viewers: constructing playManifest URLs for adaptive streaming (HLS/DASH), raw serve URLs for direct file access, download URLs, flavor asset selection, delivery profiles, and CDN configuration.

**Base URL:** `$KALTURA_SERVICE_URL` (default: `https://www.kaltura.com/api_v3`)  
**CDN Base:** `https://cdnapisec.kaltura.com` (or your account's CDN host)  
**Auth:** Public entries work without KS. Access-controlled entries require a KS appended to the URL.  
**Format:** Form-encoded request body; JSON response (format=1)  

<!-- Sections: 1.When to Use | 2.Prerequisites | 3.playManifest — Adaptive Streaming | 4.Raw Serve URL — Direct File Access | 5.Download Endpoint | 6.Flavor Asset Delivery | 7.Delivery Profiles | 8.CDN URL Tokenization | 9.Access Control on Delivery | 10.Complete Delivery Workflow | 11.Error Handling | 12.Best Practices | 13.Related Guides -->


# 1. When to Use

| Scenario | What to Use |
|----------|-------------|
| **Video player integration** — Adaptive streaming in a web or mobile player | `playManifest` with `format=applehttp` (HLS) or `format=mpegdash` (DASH) |
| **Progressive download** — Direct MP4 link for simple `<video>` tags | `playManifest` with `format=url` |
| **File download** — Download button that prompts "Save as..." | `playManifest` with `format=download` or `raw` URL |
| **Serve original source file** — Access the uploaded file as-is (SVG, PDF, data files) | Raw serve URL (`/raw/entry_id/...`) |
| **Serve a specific transcoded rendition** — Download a particular bitrate/resolution | `flavorAsset.getUrl` |
| **Restrict content delivery** — Geo-blocking, domain restrictions, IP whitelist, scheduling | Access control profiles (applied automatically to playManifest/thumbnail URLs) |
| **Multi-CDN delivery** — Route traffic through different CDN providers | Delivery profiles with CDN-specific tokenization |
| **Clipping and preview** — Play only a segment of a video | `playManifest` with `seekFrom` / `clipTo` parameters |


# 2. Prerequisites

- **Partner ID:** Available from KMC > Settings > Integration Settings.  
- **Content:** Entries must be in READY status (status=2) for delivery. See [Upload & Ingestion Guide](KALTURA_UPLOAD_AND_INGESTION_API.md).  
- **KS (optional):** Only needed for access-controlled entries. See [Session Guide](KALTURA_SESSION_GUIDE.md).  


# 3. playManifest — Adaptive Streaming

The `playManifest` endpoint is the primary way to get playback URLs for video and audio entries. It returns streaming manifests (HLS, DASH) or redirects to direct file URLs.

**URL pattern:**
```
https://cdnapisec.kaltura.com/p/{PARTNER_ID}/sp/{PARTNER_ID}00/playManifest/entryId/{ENTRY_ID}/format/{FORMAT}/protocol/https
```

Parameters are path-based key/value pairs (not query string), though query parameters are also accepted.

## 3.1 Core Parameters

| Parameter | Short | Type | Description |
|-----------|-------|------|-------------|
| `entryId` | `e` | string | Entry ID to play |
| `format` | `f` | string | Delivery format (see table below) |
| `protocol` | `pt` | string | Media protocol for URLs inside manifest: `http`, `https` |
| `ks` | — | string | Kaltura Session (also accepted via `X-Kaltura-Ks` header) |

## 3.2 Format Values

| Value | Description | Use Case |
|-------|-------------|----------|
| `applehttp` | HLS (Apple HTTP Live Streaming) | Most common — works on all modern browsers and mobile |
| `mpegdash` | MPEG-DASH | Alternative adaptive format (Widevine DRM) |
| `url` | Single progressive URL (redirect) | Simple `<video>` embed, no adaptive bitrate |
| `download` | Download URL (redirect with Content-Disposition) | Download buttons, offline access |
| `hds` | Adobe HTTP Dynamic Streaming | Legacy Flash-based players |
| `sl` | Microsoft Smooth Streaming (Silverlight) | Legacy Silverlight players |
| `hdnetworkmanifest` | Akamai HDS manifest | Akamai-specific delivery |
| `rtmp` | RTMP streaming | Legacy real-time streaming |
| `auto` | Auto-detect best format | Let the server choose |

## 3.3 Flavor Selection Parameters

| Parameter | Short | Type | Description |
|-----------|-------|------|-------------|
| `flavorId` | `fi` | string | Single flavor asset ID |
| `flavorIds` | `fs` | string | Comma-separated flavor asset IDs |
| `flavorParamId` | `fp` | int | Single flavor params ID |
| `flavorParamIds` | `fps` | string | Comma-separated flavor params IDs |
| `tags` | `t` | string | Comma-separated flavor tags to filter by |

When no flavor selection parameters are provided, the server selects flavors based on format-specific tag defaults:
- **HLS/DASH:** `applembr` → `ipadnew,iphonenew` → `ipad,iphone`
- **Progressive HTTP:** `mbr` → `web`

## 3.4 Bitrate Control

| Parameter | Short | Type | Description |
|-----------|-------|------|-------------|
| `preferredBitrate` | `pb` | int | Preferred bitrate in kbps |
| `maxBitrate` | `mb` | int | Maximum bitrate cap in kbps |
| `minBitrate` | `mib` | int | Minimum bitrate floor in kbps |

**Business scenario — bandwidth-constrained delivery:** A mobile app on a cellular connection caps `maxBitrate=1500` to prevent buffering, while a smart TV app on fiber sets `minBitrate=3000` for quality.

## 3.5 Clipping and Seeking

| Parameter | Short | Type | Description |
|-----------|-------|------|-------------|
| `seekFrom` | `sf` | int | Start playback from this point (milliseconds) |
| `clipTo` | `ct` | int | End playback at this point (milliseconds) |

**Business scenario — content preview:** An e-commerce site shows 30-second previews of product videos. The playManifest URL includes `clipTo=30000` to limit playback without creating separate clips.

## 3.6 Player and Session Parameters

| Parameter | Short | Type | Description |
|-----------|-------|------|-------------|
| `uiConfId` | `ui` | int | Player UI configuration ID |
| `sessionId` | — | string | Playback session ID for analytics |
| `playSessionId` | — | string | Play session tracking |
| `playbackContext` | `pc` | string | Playback context string |
| `referrer` | `r` | string | Base64-encoded referrer URL for access control |
| `responseFormat` | — | string | Response format: `redirect` (default), `f4m`, `m3u8`, `jsonp` |

## 3.7 Delivery and CDN Parameters

| Parameter | Short | Type | Description |
|-----------|-------|------|-------------|
| `cdnHost` | `ch` | string | Override CDN hostname |
| `storageId` | `si` | int | Serve from a specific remote storage |
| `deliveryProfileId` | — | int | Use a specific delivery profile |
| `deliveryProfileIds` | — | string | Comma-separated delivery profile IDs |
| `deliveryCode` | `dc` | string | Delivery code identifier |

## 3.8 Audio and Caption Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `defaultAudioLang` | string | Default audio language code |
| `muxedAudioLang` | string | Muxed audio track language |
| `tracks` | string | Track selection string |
| `disableCaptions` | bool | Suppress caption tracks from manifest |

## 3.9 Sequence / Multi-Entry Playback

| Parameter | Type | Description |
|-----------|------|-------------|
| `sequence` | string | Comma-separated entry IDs for multi-entry sequence playback (HLS/DASH only) |

## 3.10 Security Parameters

| Parameter | Short | Type | Description |
|-----------|-------|------|-------------|
| `expiry` | `ex` | int | URL token expiry (Unix timestamp) |
| `kt` | — | string | Kaltura URL token (pre-signed URL verification) |
| `hashes` | — | string | Access control hash verification |

## 3.11 Examples

```bash
# HLS streaming (most common)
https://cdnapisec.kaltura.com/p/$KALTURA_PARTNER_ID/sp/${KALTURA_PARTNER_ID}00/playManifest/entryId/$KALTURA_ENTRY_ID/format/applehttp/protocol/https

# MPEG-DASH streaming
https://cdnapisec.kaltura.com/p/$KALTURA_PARTNER_ID/sp/${KALTURA_PARTNER_ID}00/playManifest/entryId/$KALTURA_ENTRY_ID/format/mpegdash/protocol/https

# Progressive download (single MP4)
https://cdnapisec.kaltura.com/p/$KALTURA_PARTNER_ID/sp/${KALTURA_PARTNER_ID}00/playManifest/entryId/$KALTURA_ENTRY_ID/format/url/protocol/https

# Download with specific flavor
https://cdnapisec.kaltura.com/p/$KALTURA_PARTNER_ID/sp/${KALTURA_PARTNER_ID}00/playManifest/entryId/$KALTURA_ENTRY_ID/format/download/protocol/https/flavorParamIds/0

# With access control (append KS)
https://cdnapisec.kaltura.com/p/$KALTURA_PARTNER_ID/sp/${KALTURA_PARTNER_ID}00/playManifest/entryId/$KALTURA_ENTRY_ID/format/applehttp/protocol/https/ks/$KALTURA_KS

# 30-second preview clip
https://cdnapisec.kaltura.com/p/$KALTURA_PARTNER_ID/sp/${KALTURA_PARTNER_ID}00/playManifest/entryId/$KALTURA_ENTRY_ID/format/applehttp/protocol/https/clipTo/30000

# Capped at 1500kbps maximum bitrate
https://cdnapisec.kaltura.com/p/$KALTURA_PARTNER_ID/sp/${KALTURA_PARTNER_ID}00/playManifest/entryId/$KALTURA_ENTRY_ID/format/applehttp/protocol/https/maxBitrate/1500

# With referrer for domain restriction
https://cdnapisec.kaltura.com/p/$KALTURA_PARTNER_ID/sp/${KALTURA_PARTNER_ID}00/playManifest/entryId/$KALTURA_ENTRY_ID/format/applehttp/protocol/https/referrer/aHR0cHM6Ly9teXNpdGUuY29t
```

**Download URL from entry object:** Every `KalturaMediaEntry` includes a `downloadUrl` property that is a pre-built playManifest download URL.


# 4. Raw Serve URL — Direct File Access

The `raw` URL serves the **original source file** for any entry type — documents, data entries, images, SVGs, videos, or audio. Unlike `playManifest` (which returns adaptive streaming manifests) or the thumbnail API (which returns transformed images), `raw` returns the file exactly as uploaded.

**URL pattern:**
```
https://cdnapisec.kaltura.com/p/{PARTNER_ID}/raw/entry_id/{ENTRY_ID}/{param}/{value}/...
```

## 4.1 Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `direct_serve` | bool | When `1`/`true`, serves inline (no Content-Disposition download prompt) |
| `forceproxy` | bool | When `1`/`true`, proxies the file through the server instead of redirecting |
| `file_name` | string | Sets the `Content-Disposition` filename for downloads |
| `format` | string | File extension to select a specific flavor (e.g., `mp4`, `mov`) |
| `type` | string | Set to `download` for format-specific download |
| `version` | string | Data version (for data entries) |
| `ks` | string | Kaltura Session for access-controlled entries |
| `referrer` | string | Base64-encoded referrer for domain restrictions |

## 4.2 Behavior by Entry Type

| Entry Type | Behavior |
|------------|----------|
| **Image** | Serves the original uploaded image file |
| **Video/Audio** | Serves original source flavor, falls back to best web-playable flavor |
| **Document** | Serves document file with `Access-Control-Allow-Origin: *` |
| **Data** | Serves the data file, redirects if on remote storage |

## 4.3 Examples

```bash
# Serve an SVG inline in the browser
https://cdnapisec.kaltura.com/p/$KALTURA_PARTNER_ID/raw/entry_id/$KALTURA_ENTRY_ID/direct_serve/1/forceproxy/true/logo.svg

# Serve a PDF (prompts download — no direct_serve)
https://cdnapisec.kaltura.com/p/$KALTURA_PARTNER_ID/raw/entry_id/$KALTURA_ENTRY_ID/forceproxy/true/report.pdf

# Serve original source video inline (native browser player)
https://cdnapisec.kaltura.com/p/$KALTURA_PARTNER_ID/raw/entry_id/$KALTURA_ENTRY_ID/direct_serve/1/forceproxy/true/video.mp4

# Access-controlled entry (append KS)
https://cdnapisec.kaltura.com/p/$KALTURA_PARTNER_ID/raw/entry_id/$KALTURA_ENTRY_ID/ks/$KALTURA_KS/direct_serve/1/forceproxy/true/file.zip
```

## 4.4 When to Use Raw vs Other Methods

| Method | Use Case |
|--------|----------|
| **`raw`** | Original uploaded file (SVGs, source video, documents, data files, original images) |
| **`playManifest`** | Adaptive video/audio playback (HLS, DASH). Returns transcoded renditions, not source file |
| **`download`** | Like raw but with additional flavor selection and access control context |
| **Thumbnail API** | Images when you need resizing, cropping, format conversion, or video frame extraction |


# 5. Download Endpoint

The `download` endpoint serves files with `Content-Disposition: attachment` headers. It supports flavor selection and access control preview limits.

**URL pattern:**
```
https://cdnapisec.kaltura.com/p/{PARTNER_ID}/sp/{PARTNER_ID}00/download/entry_id/{ENTRY_ID}/...
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `flavor` | string | Specific flavor asset ID to download |
| `file_name` | string | Override download filename |
| `ks` | string | Kaltura Session |
| `referrer` | string | Base64-encoded referrer |

When no flavor is specified, selects the best web-playable flavor, falling back to the original source.


# 6. Flavor Asset Delivery

The `flavorAsset` service provides API-based URL generation for specific renditions.

## 6.1 flavorAsset.getUrl — Get Download URL for a Flavor

```
POST /api_v3/service/flavorAsset/action/getUrl
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `id` | string | Flavor asset ID |
| `storageId` | int | Specific storage profile (optional) |
| `forceProxy` | bool | Route through proxy (optional) |
| `options[fileName]` | string | Override download filename (optional) |
| `options[referrer]` | string | Referrer for access control (optional) |

Returns a direct download URL string.

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/flavorAsset/action/getUrl" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "id=$FLAVOR_ASSET_ID"
```

**Business scenario — quality-specific download:** An LMS offers "Download HD" and "Download SD" buttons. Each button links to `flavorAsset.getUrl` with the appropriate flavor asset ID.

## 6.2 flavorAsset.list — Discover Available Renditions

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/flavorAsset/action/list" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "filter[entryIdEqual]=$KALTURA_ENTRY_ID"
```

Returns all flavors with `id`, `width`, `height`, `bitrate` (kbps), `size` (KB), `status`, `isOriginal`.

## 6.3 flavorAsset.getFlavorAssetsWithParams

Returns all flavor assets paired with their flavor params for an entry, including params without assets (not yet transcoded) and assets without params.

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/flavorAsset/action/getFlavorAssetsWithParams" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "entryId=$KALTURA_ENTRY_ID"
```


# 7. Delivery Profiles

Delivery profiles configure how URLs are constructed for specific CDN providers. Each profile defines the CDN host, URL pattern, and authentication/tokenization.

Delivery profiles are configured by Kaltura administrators for your account. You interact with them indirectly through playManifest URL parameters (`deliveryProfileId`, `deliveryProfileIds`) and access control rules.

## 7.1 Profile Types

| Category | Types |
|----------|-------|
| **Generic** | APPLE_HTTP, HDS, HTTP, RTMP, RTSP, SILVER_LIGHT |
| **Akamai** | AKAMAI_HLS_DIRECT, AKAMAI_HLS_MANIFEST, AKAMAI_HD, AKAMAI_HDS, AKAMAI_HTTP, AKAMAI_RTMP, AKAMAI_SS |
| **Generic CDN** | GENERIC_HLS, GENERIC_HDS, GENERIC_HTTP, GENERIC_HLS_MANIFEST, GENERIC_SS, GENERIC_RTMP |
| **Level3** | LEVEL3_HLS, LEVEL3_HTTP, LEVEL3_RTMP |
| **Limelight** | LIMELIGHT_HTTP, LIMELIGHT_RTMP |
| **VOD Packager** | VOD_PACKAGER_HLS, VOD_PACKAGER_HDS, VOD_PACKAGER_MSS, VOD_PACKAGER_DASH |
| **Live** | LIVE_HLS, LIVE_HDS, LIVE_DASH, LIVE_RTMP, LIVE_PACKAGER_HLS, LIVE_PACKAGER_HDS, LIVE_PACKAGER_DASH, LIVE_PACKAGER_MSS |

## 7.2 CDN Selection Priority

When playManifest resolves a delivery profile, it follows this priority:

1. **Explicit request:** `deliveryProfileId` or `deliveryProfileIds` URL parameter  
2. **Access control rules:** `LIMIT_DELIVERY_PROFILES` action (whitelist or blacklist)  
3. **Storage profile mapping:** Each storage profile maps to delivery profiles by format  
4. **Partner default:** System selects based on format and CDN host  

## 7.3 Multi-CDN Support

Multiple remote storage profiles can hold copies of the same content. The system selects the storage profile (CDN) with the most available flavors. Storage serve priority controls the preference:

| Value | Behavior |
|-------|----------|
| KALTURA_ONLY | Always serve from Kaltura storage |
| KALTURA_FIRST | Prefer Kaltura, fall back to external |
| EXTERNAL_FIRST | Prefer external storage, fall back to Kaltura |
| EXTERNAL_ONLY | Only serve from external storage |


# 8. CDN URL Tokenization

When a delivery profile has a URL tokenizer configured, signed tokens are automatically appended to all URLs in the manifest. This prevents unauthorized hotlinking.

**Supported CDN tokenizers:**

| CDN | Mechanism |
|-----|-----------|
| **Akamai** | `__gda__` parameter with HMAC-MD5 token |
| **AWS CloudFront** | RSA-SHA1 signed URLs with `Policy`, `Signature`, `Key-Pair-Id` parameters. Supports ACL-based policies, IP restriction, and expiry |
| **Level3 / CenturyLink** | Level3 URL authentication |
| **Limelight** | Limelight CDN token |
| **Kaltura CDN** | Internal `kt` token using SHA1(secret + URL) |
| **KS-based** | KS token embedded in URL |

Tokenization is forced automatically when entitlement is enabled or access control rules exist on the entry.

**Kaltura URL Token (`kt`):** playManifest supports pre-signed URLs for embedding in emails or offline use:
- `expiry` = Unix timestamp when the URL expires  
- `kt` = SHA1(url_token_secret + URL with `{kt}` placeholder)  
- When present, KS validation is bypassed — the URL itself is the authorization  


# 9. Access Control on Delivery

Access control profiles define rules that are enforced server-side on every playManifest, raw, download, and thumbnail request. Rules can restrict access by IP address, country, domain, user agent, authentication status, scheduling windows, and custom metadata conditions.

Different delivery endpoints are evaluated in different contexts: playManifest uses the PLAY context, raw/download uses DOWNLOAD, and thumbnail URLs use THUMBNAIL. An entry can be viewable but not downloadable, or thumbnails can be accessible even when playback is restricted.

For the complete access control model — including profile CRUD, rule conditions, actions, metadata-driven scheduling, and business scenarios — see the [Access Control API Guide](KALTURA_ACCESS_CONTROL_API.md).


# 10. Complete Delivery Workflow

```
1. Upload & transcode content (see Upload & Ingestion Guide)
2. Entry reaches READY status (status=2)

For adaptive streaming:
3a. Construct playManifest URL:
    /p/{PID}/sp/{PID}00/playManifest/entryId/{EID}/format/applehttp/protocol/https
4a. Player fetches HLS manifest, selects bitrate, plays

For direct file access:
3b. Construct raw URL:
    /p/{PID}/raw/entry_id/{EID}/direct_serve/1/forceproxy/true
4b. Browser serves file inline or prompts download

For specific flavor download:
3c. List flavors: flavorAsset.list with entryIdEqual
4c. Get URL: flavorAsset.getUrl with flavor asset ID
5c. Redirect user to the returned URL

For access-controlled content:
- Append /ks/{KS} to any delivery URL
- Access control rules are evaluated automatically
```


# 11. Error Handling

| Error | Meaning | Resolution |
|-------|---------|------------|
| HTTP 403 | Access denied by access control rules | Check KS, referrer, IP, geo restrictions |
| HTTP 404 | Entry not found or not READY | Verify entry exists and status=2 |
| Empty manifest | No matching flavors for the requested format | Check flavor tags, format compatibility |
| `ENTRY_DELETED_MODERATED` | Entry was deleted or rejected by moderator | Entry is no longer available |
| Redirect loop | playManifest can't resolve a delivery profile | Check delivery profile configuration |


# 12. Best Practices

- **Use HLS (`applehttp`) as default format.** It has the broadest device support and efficient adaptive bitrate switching.  
- **Always use HTTPS protocol.** Partners with `enforce_encryption` will block non-HTTPS requests.  
- **Append KS for protected content.** Access-controlled entries require a valid KS in the URL. Use short-lived user KS (type=0) for player embed, not admin KS.  
- **Use `playSessionId` for analytics.** Include a unique session ID to track playback analytics accurately.  
- **Use `referrer` for domain restrictions.** Base64-encode the page URL and pass it as the `referrer` parameter.  
- **Cache playManifest URLs.** Manifest URLs are CDN-cached. For time-sensitive access control, use `expiry` and `kt` parameters.  
- **Use `flavorAsset.getUrl` for download links.** It handles storage selection, CDN routing, and tokenization automatically.  
- **Use Access Control profiles for restrictions.** The platform handles geo, IP, domain, and scheduling checks during playback — configure them in Kaltura and they're enforced on every request.  
- **Short-form parameter names** (`e`, `f`, `pt`, etc.) are supported for all playManifest parameters for shorter URLs.  
- **Videos under 10 seconds:** Akamai HDS format automatically falls back to progressive HTTP for very short videos.  


# 13. Related Guides

- **[Upload & Ingestion API](KALTURA_UPLOAD_AND_INGESTION_API.md)** — Upload content and manage entries before delivery  
- **[Thumbnail & Image API](KALTURA_THUMBNAIL_API.md)** — Dynamic thumbnail generation, sprite sheets, thumbAsset management  
- **[Session Guide](KALTURA_SESSION_GUIDE.md)** — KS generation for access-controlled delivery  
- **[Player Embed Guide](KALTURA_PLAYER_EMBED_GUIDE.md)** — Embed player with playManifest URLs  
- **[Access Control API](KALTURA_ACCESS_CONTROL_API.md)** — Access control profiles, rules, conditions, and actions for delivery restrictions  
- **[Categories & Entitlements API](KALTURA_CATEGORIES_AND_ENTITLEMENTS_API.md)** — Category-based content visibility and entitlement enforcement  
- **[Distribution](KALTURA_DISTRIBUTION_API.md)** — Distribute content to external platforms  
- **[Syndication](KALTURA_SYNDICATION_API.md)** — Serve content via syndication feeds  
- **[Analytics Reports](KALTURA_ANALYTICS_REPORTS_API.md)** — Track delivery and playback metrics  
