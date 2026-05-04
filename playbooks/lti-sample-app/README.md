# Kaltura LMS Extensions — LTI Integration Demo

Reference implementation for the [LTI Platform Integration Playbook](../LTI_PLATFORM_INTEGRATION.md). Simulates an LMS and demonstrates how Kaltura's LMS Extensions (KAF) integrate with any LTI-compliant platform via the **ltigeneric** profile.

For LTI concepts, authentication flows, and KAF module documentation, see the [LTI Integration Guide](../../KALTURA_LTI_INTEGRATION_GUIDE.md).

## Quick Start

```bash
cd "Kaltura API Guides/playbooks/lti-sample-app"
pip install flask requests
python app.py
```

Open http://localhost:5050 in your browser.

For full functionality (Content Picker return, Caliper events from KAF servers):

```bash
cloudflared tunnel --config /dev/null --url http://localhost:5050
PUBLIC_URL=https://xxxx.trycloudflare.com python app.py
```

The `--config /dev/null` flag prevents existing `~/.cloudflared/config.yml` from interfering. Only features that redirect back to your app (Content Picker return, Express Capture save) require the tunnel — all other modules work on localhost.

## Configuration

Create a `.env` file in this directory, or set environment variables. Falls back to `../../tests/.env`.

```
KALTURA_PARTNER_ID=your_partner_id
KALTURA_ADMIN_SECRET=your_admin_secret
KALTURA_SERVICE_URL=https://www.kaltura.com/api_v3
PUBLIC_URL=https://your-tunnel-url.trycloudflare.com
PORT=5050
```

## What It Demonstrates

| App Page | Feature |
|----------|---------|
| **Try It** (`/`) | LTI 1.1 launches to 6 KAF modules |
| **How It Works** (`/how-it-works`) | Plain-language LTI explanation |
| **Grade Sync** (`/grade-passback`) | LTI Basic Outcomes grade passback |
| **Analytics** (`/caliper`) | Live Caliper event stream (mini LRS) |
| **Standalone Embed** (`/ks-sso`) | KAF without LTI (KS-SSO pattern) |
| **Course Setup** (`/provisioning`) | SIS provisioning via Kaltura API |

Modules launched: My Media, Media Gallery, Content Picker, Genie AI, Avatar Studio, Meeting Room. See the [playbook §3](../LTI_PLATFORM_INTEGRATION.md#3-lti-launch-signing-phase-1) for module endpoints and parameters.

## KAF Admin Prerequisites

The KAF instance needs the **ltigeneric** profile. Module-specific settings:

| Module | Admin Path | Config Needed |
|--------|-----------|---------------|
| My Media / Media Gallery | `/admin/config/tab/hosted` | Default |
| Content Picker | `/admin/config/tab/browseandembed` | Default |
| Genie AI | `/admin/config/tab/genieai` | `GlobalSiteGenie=1` |
| Avatar Studio | `/admin/config/tab/avatarvodstudio` | `allowedRoles=privateOnlyRole` |
| Meeting Room | `/admin/config/tab/embeddedrooms` | Module enabled |
| Caliper | `/admin/config/tab/caliper` | `directCaliperIntegration=No` |

Meeting Room requires a room entry ID (`custom_entry_id`) — create one via My Media → Add New → Meeting Room.

Shared Repository appears as a tab in Content Picker when enabled (not a standalone launch). See the [guide §5](../../KALTURA_LTI_INTEGRATION_GUIDE.md#5-kaf-modules) for details.

## E2E Testing

```bash
pip install playwright
python -m playwright install chromium
python app.py &
python test_app.py
```

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| "Access Denied" on a module | Check `ltiRolesMapping` in the module's KAF admin tab |
| "Application Error" on Meeting Room | Verify `custom_entry_id` is a valid room entry |
| Content Picker return fails | Use cloudflared tunnel with `PUBLIC_URL` |
| Caliper events not appearing | Profile URL must be reachable from KAF servers (use tunnel) |
| Media Gallery shows "No media" | Use consistent `user_id` across all launches |

For additional error scenarios, see the [playbook §9](../LTI_PLATFORM_INTEGRATION.md#9-monitoring--troubleshooting) and [guide §15](../../KALTURA_LTI_INTEGRATION_GUIDE.md#15-error-handling).

## Brand Compliance

- **Typography:** Lato
- **Colors:** Stream Blue (#006EFA), Brand Black (#282828), Eggshell (#F8F8F5)
- **Terminology:** "LMS Extensions" (not "KAF"), "Content Hubs" (not "KMS/MediaSpace")

## Requirements

- Python 3.8+
- Flask, requests
- Kaltura account with LMS Extensions instance (ltigeneric profile)
- cloudflared (for Content Picker return / Caliper)
- Playwright + Chromium (E2E tests only)
