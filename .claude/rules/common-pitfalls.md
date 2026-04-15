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
| Documenting SERVICE_FORBIDDEN actions | Customers can't use documented features, guide loses trust | Test every action with a customer KS before documenting. Exclude actions returning SERVICE_FORBIDDEN |
| Tests catching errors as "expected" | Test passes but the feature doesn't work for customers. Masks inaccessible actions | Tests must succeed with actual API responses. If a test expects FORBIDDEN/PERMISSION errors, the feature should not be documented |
| Linking to non-existent guides | Broken references in Related Guides and cross-references | Only link to published guides. Remove or replace references to planned/future guides |
| Bundling unrelated services in one guide | Guide grows unwieldy, each service gets shallow coverage, hard to find information | One guide per service boundary. Split if services don't share actions, don't depend on each other, and aren't always used together |
| Metadata XML field order wrong | Validation failure on metadata.add | Match field order exactly to XSD sequence; field names are case-sensitive |
| Exceeding 4 searchable Date/Integer fields per metadata profile | Fields silently not indexed in eSearch | Use text fields for non-filterable dates/numbers |
| Listing beyond 10K results | Pager returns empty after page ~20 | Use `createdAtGreaterThanOrEqual` date-range filter to window results |
| Embedding API secrets in mobile apps | Security vulnerability — secrets are permanent and cannot be rotated | Use server-side KS generation or AppToken flow |
| KS hardcoded in compiled mobile binary | KS expires, app stops working; users can extract it | Generate KS on server, pass to client per-session |
| Multirequest without per-result error checking | One failed sub-request silently ignored | Check each array element for `objectType: "KalturaAPIException"` |
| Assigning more than 32 categories to an entry | `categoryEntry.add` throws `MAX_CATEGORIES_FOR_ENTRY_REACHED` | Default limit is 32; accounts with `FEATURE_DISABLE_CATEGORY_LIMIT` get 1000. Design hierarchies accordingly |
| Publishing guide without updating GUIDE_MAP.md | AI agents miss the new guide or traverse incorrectly | Update GUIDE_MAP.md when adding or modifying guides |
| Entry status 7 confused with DELETED | Agent treats NO_CONTENT entries as deleted, or deletes the wrong entries | 7=NO_CONTENT (draft/empty), 3=DELETED. Full enum: -2=ERROR_IMPORTING, -1=ERROR_CONVERTING, 0=IMPORT, 1=PRECONVERT, 2=READY, 3=DELETED, 4=PENDING, 5=MODERATE, 6=BLOCKED, 7=NO_CONTENT |
| CategoryEntryStatus 1/2 swapped | Agent filters for ACTIVE entries but gets PENDING, or vice versa | 1=PENDING, 2=ACTIVE (not the reverse). Verify all status enums against `api_v3/api_schema.php` |
| Passing string booleans to filter parameters | `"true"` silently ignored — API expects `KalturaNullableBoolean` integers | Use `-1`=null, `0`=false, `1`=true for boolean filter fields |
| Cleanup registered after assertions in tests | If assertion fails, cleanup never runs — resources leak | Register cleanup immediately after resource creation, BEFORE any assertions |
