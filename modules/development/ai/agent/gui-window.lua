-- Keep the contained app tiled beside Native. Electron may restore a saved
-- maximized window after ready-to-show; use the compositor's supported rule
-- instead of rewriting its private profile or patching its bundled source.
-- Fullscreen requests (F11) and compositor-driven layout remain available.
hl.window_rule({
  name = "phoenix-contained-chatgpt-window",
  match = { class = "^codex-desktop-sandboxed$" },
  suppress_event = "maximize",
})
