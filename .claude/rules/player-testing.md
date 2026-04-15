# Player Testing (Browser-Based)

For guides involving player features (Multi-Stream, Player Embed):

1. Generate an HTML file with Player v7 (`KalturaPlayer.setup()`) during the test
2. Pass a short-lived USER KS (type=0, 1hr expiry) to the player provider config — the player needs API access to discover related entries
3. Include interactive controls (buttons for layout switching, etc.)
4. Include a debug log section that shows plugin service status and events
5. Open in browser with `webbrowser.open()`
6. Use `--keep` flag to preserve entries while testing in browser

## Player v7 Runtime API

`player.configure()` sets initial config only. To change plugin state at runtime, use the service-based approach:

```javascript
var svc = player.getService('dualScreen');
svc.ready.then(function() {
  var ds = player.plugins.dualscreen;
  ds._switchToPIP({ force: true }, true);
  ds._switchToSideBySide({ force: true }, true);
});
```

Wait for the `dualScreen` service `ready` promise (resolves after secondary media loads), then call `_switchTo*` methods on the plugin instance.
