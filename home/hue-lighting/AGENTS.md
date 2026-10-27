# Hue source selection

- Keep the declarative default independent of connector names and the system
  picker's zero-based numbering; the panel uses spatial order from one.
- The portal picker hook serves all desktop applications. Only the explicit Hue
  app ID may use automatic source preferences; empty/other IDs and manual mode
  must retain the original Screen/Window/Region picker. App IDs route UX, not auth.
- Trace both portal hooks and native application identity before treating the
  upstream HTTP API as the capability limit. Verify automatic selection with
  `tests/portal-runtime.py` on an isolated bus and private state; a build or mock
  does not establish actual source selection. Do not restart the shared portal
  merely to test changes.
