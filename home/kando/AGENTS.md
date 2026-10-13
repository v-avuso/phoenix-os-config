# Kando integration

- Verify menu commands against the installed Hyprland Lua CLI. Plugin docs may
  still show legacy `dispatch plugin:action argument` syntax; use `hyprctl eval`
  for direct Lua plugin calls. Exercise new overview actions in a disposable
  compositor before deployment; a successful package build does not verify the CLI.
- Preserve and recheck the main D-Bus/systemd activation environment around
  disposable compositor tests; restore verified main-session display variables
  if changed. A stale temporary Wayland socket breaks user-service restarts;
  do not assume nested compositors isolate activation state.
