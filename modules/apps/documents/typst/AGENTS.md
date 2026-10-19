# Typst publishing

- Omd2Typst adapters expose `template`/`callout`; do not mistake them for
  standalone designs. Keep reusable presentation independent of conversion.
- Test metadata with the installed converter: Omd2Typst 0.9.0 flattens nested
  YAML mappings. Use flat sender keys, and keep the adapter allowlist explicit.
- Letter Pro 3.0.0 disables hyphenation inside `letter-simple`; restore it in
  the supplied body, then check actual PDF line endings and visual layout.
- Distinguish filesystem-backed plugin tests from live Obsidian indexing and
  watcher acceptance. Never infer directory-symlink discovery from CLI reads.
