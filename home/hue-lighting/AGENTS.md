# Hue source consent

- Always retain the native Screen/Window/Region picker for a new capture grant.
  App IDs are forgeable UX hints: use them only to default the remember checkbox,
  never to emit a selection or bypass initial source consent.
- Normal starts preserve Huenicorn's restore token. Clear it only for an explicit
  source-change action after stopping its owner; let upstream save the replacement.
- Verify portal routing with `tests/portal-runtime.py` on an isolated bus and
  private state. Confirm both Hue and unrelated apps still need native consent;
  do not restart shared desktop services merely to test changes.
