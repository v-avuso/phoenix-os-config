# Typst publishing

- Keep shared compiler/font installation, upstream package provisioning and vault
  deployment in this module. Components own their template and adapter sources;
  `template-adapters/omd2typst/` aggregates canonical adapters with relative links,
  not copies. Preserve the common module root so those links retain their targets.
- For Phoenix Letter changes, explicitly read its [component guidance](templates/phoenix-letter/AGENTS.md).
  It owns letter-specific metadata, layout and design-maintenance checks.
- After source/layout moves, use the [README validation commands](README.md#validation):
  `tests/source-layout.nix` checks Git-flake store links and isolated templates;
  also build/inspect affected Home Manager data-file sources, including the live
  local-package link. Run `tests/run.py` with the installed converter for functional
  acceptance; store resolution alone does not establish export behavior.
- Omd2Typst adapters expose `template`/`callout`; do not mistake them for
  standalone designs. Keep reusable presentation independent of conversion.
- Test metadata with the installed converter: Omd2Typst 0.9.0 flattens nested
  YAML mappings and treats multiline values as Typst markup. Keep each adapter's
  metadata allowlist explicit.
- Omd2Typst inline frontmatter is an insertion template, not export-time defaults.
  Check the installed plugin’s merge/export semantics before changing YAML keys.
- Distinguish filesystem-backed plugin tests from live Obsidian indexing and
  watcher acceptance. Never infer directory-symlink discovery from CLI reads.

- For live vault adapters, try one directory symlink to the repository-owned
  adapter directory before introducing synchronization. Keep vault parents real,
  never write adapter content through the link, and preserve existing copies on
  migration. Missing live indexing evidence is not proof of incompatibility; seek
  the specific Obsidian picker/export check before choosing a fallback.

- For PDF/UA changes, compile actual converter output, not just standalone Typst.
  Pair strict UA compilation with veraPDF report checks; successful compilation
  alone does not establish accessible reading order or content quality.
