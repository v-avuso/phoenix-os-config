# Symbol input

- When changing symbol mappings, prefer native XKB symbol levels and single
  keyd chords. Literal Unicode uses keyd's private Compose encoding; even standard
  Compose macros can behave differently between applications (observed in
  Obsidian versus Codex). Parser/Compose-table success alone does not establish
  application output. Check actual keyd press/release events through the configured
  XKB state with `tests/symbols.nix`, verify both desktop consumers receive the
  variant/options, and retain live application acceptance as a separate check.
