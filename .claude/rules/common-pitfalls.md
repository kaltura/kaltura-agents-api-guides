# Common Pitfalls

| Pitfall | What happens | Fix |
|---------|-------------|-----|
| Using `player.configure()` for runtime plugin changes | Config updates silently ignored — plugins read config only at setup | Use `player.plugins.{name}._switchTo*()` methods after service `ready` promise |
| Using playManifest URL with `addFromUrl` | Server follows redirect to HLS manifest, not MP4 — import hangs at status 0 | Use direct MP4 download URLs (e.g., `cfvod.kaltura.com/...`) |
| Negative framing in guides | Agents interpret "X doesn't work" as instructions about X, get confused | Rewrite as positive: "Use Y to accomplish this" |
| Python/language-specific examples in guides | Limits agents to one language, adds maintenance burden | Use curl only — agents adapt to their target language |
| System env vars overriding test `.env` | Tests run against wrong Kaltura account | The `.env` loader force-sets with `os.environ[key] = value` |
| `input()` in non-interactive shell | EOF received immediately, cleanup runs before user can test | Check `sys.stdin.isatty()` before `input()`, support `--keep` flag |
| Listing children immediately after `addFromUrl` | New entry not yet indexed — filter returns 0 | Wait for child to reach READY status, or retry with delay |
| Hardcoded URLs in curl examples | Breaks for non-default regions/deployments | Use `$SERVICE_URL`, `$KS`, `$PARTNER_ID` shell variables |
| Missing `format=1` in API v3 calls | Response comes back as XML instead of JSON | Always include `format=1` in every API v3 request |
| Events Platform string IDs | API expects integers for event IDs | Use integers: `12345` not `"evt_abc123"` |
