# Test File Standards

Every guide with API calls gets a companion test in `tests/test_{name}.py`.

## Structure

```python
#!/usr/bin/env python3
"""End-to-end validation of the [API Name]. Covers: [list]"""

import sys, os, time, requests
sys.path.insert(0, os.path.dirname(__file__))
from test_helpers import kaltura_post, TestRunner, PARTNER_ID, KS, SERVICE_URL

state = {}

def main():
    runner = TestRunner("API Name — E2E Validation")

    # ════════════════════════════════════════════
    # Phase 1: Description
    # ════════════════════════════════════════════
    def test_something():
        """Docstring describing what this test validates."""
        result = kaltura_post("service", "action", {"param": "value"})
        assert "id" in result, f"Expected id in response: {result}"
        state["resource_id"] = result["id"]
        runner.register_cleanup(f"resource {result['id']}",
                                lambda: _delete_resource(result["id"]))
        print(f"    Created: {result['id']}")

    runner.run_test("service.action — description", test_something)

    # Cleanup & Summary
    keep = "--keep" in sys.argv
    if keep:
        # Print entry IDs, skip cleanup
        pass
    else:
        if sys.stdin.isatty():
            input("Press Enter to clean up...")
        runner.cleanup()

    success = runner.summary()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
```

## Conventions

- **Phased structure.** Group related tests under phase comments (`# Phase 1: Create`, etc.)
- **State dictionary.** Store created resource IDs in `state = {}` for use across tests.
- **Register cleanup immediately.** After creating any resource, call `runner.register_cleanup()` so it gets deleted even if later tests fail.
- **Test naming.** `runner.run_test("service.action — what it validates", fn)` — name matches the API call.
- **Assertions with context.** Always include actual value: `f"Expected X, got {actual}"`.
- **Print progress.** Each test prints key details: `print(f"    Entry: {id}, status={status}")`.
- **`--keep` flag.** Support `--keep` in `sys.argv` to preserve resources for manual testing. Print a cleanup command when using `--keep`.
- **Interactive cleanup.** Check `sys.stdin.isatty()` before `input()` — non-interactive shells get EOF immediately.
- **Polling for async operations.** Use `_wait_for_ready()` with configurable `POLL_INTERVAL` and `POLL_TIMEOUT` when waiting for entry processing (status=2 READY).
- **Direct MP4 URLs for imports.** Use direct MP4 download URLs with `addFromUrl`, not playManifest redirect URLs.

## Environment Configuration

Tests load config from `tests/.env` (force-overrides system env vars):

```
KALTURA_PARTNER_ID=123456
KALTURA_KS=<admin KS>
KALTURA_SERVICE_URL=https://www.kaltura.com/api_v3
KALTURA_ADMIN_SECRET=<secret>
KALTURA_USER_ID=user@example.com
KALTURA_PLAYER_ID=56732362
KALTURA_AGENTS_MANAGER_URL=https://agents-manager.nvp1.ovp.kaltura.com
KALTURA_GENIE_URL=https://genie.nvp1.ovp.kaltura.com
```

The `.env` file takes priority over system environment variables (the loader uses `os.environ[key] = value`, not `setdefault`).

## Test Helpers (`test_helpers.py`)

| Function | Purpose |
|----------|---------|
| `kaltura_post(service, action, params)` | API v3 form-encoded POST with auto KS and format=1 |
| `agents_post(path, json_body)` | Agents Manager JSON POST with Bearer auth |
| `genie_post(path, json_body, ...)` | AI Genie JSON POST with `KS` auth header |
| `create_test_entry()` | Create a minimal media entry for testing |
| `delete_test_entry(entry_id)` | Delete a media entry (with error handling) |
| `TestRunner` | Test orchestrator with `run_test()`, `register_cleanup()`, `cleanup()`, `summary()` |
