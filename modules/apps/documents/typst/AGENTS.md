# Typst publishing

- Omd2Typst adapters expose `template`/`callout`; do not mistake them for
  standalone designs. Keep reusable presentation independent of conversion.
- Test metadata with the installed converter: Omd2Typst 0.9.0 flattens nested
  YAML mappings and treats multiline values as Typst markup. Numbered chamber
  lines can become enum items; verify compact address spacing with the actual
  converter. Use flat sender keys, and keep the adapter allowlist explicit.
- Use Letter Pro’s composable helpers for wrapper-owned styles and metadata.
  Its simple preset disables hyphenation and assumes a sender author; verify
  rejected missing sender fields as well as actual German PDF line endings.
- Require sender name/address and recipient instead of silently omitting letter
  identity. Check the top-right sender block separately from the return row;
  one occurrence of the sender name does not prove both are present.
- Omd2Typst inline frontmatter is an insertion template, not export-time defaults.
  Check the installed plugin’s merge/export semantics before changing YAML keys.
- Distinguish filesystem-backed plugin tests from live Obsidian indexing and
  watcher acceptance. Never infer directory-symlink discovery from CLI reads.

- For live vault adapters, try one directory symlink to the repository-owned
  adapter directory before introducing synchronization. Keep vault parents real,
  never write adapter content through the link, and preserve existing copies on
  migration. Missing live indexing evidence is not proof of incompatibility; seek
  the specific Obsidian picker/export check before choosing a fallback.

- Match reference typography against its actual exporter and the intended viewer's
  font mapping; Poppler substitution does not establish Obsidian glyphs. Measure
  line, heading and information-row baselines separately, not just one paragraph gap.
- Check the return-address row separately from recipient/window containment.
  Keep the top return row, reserved postal area and DIN B recipient start distinct;
  changing return-rule padding must not shift the recipient into the postal area.

- For PDF/UA changes, compile actual converter output, not just standalone Typst.
  Replacing an enum in a show rule can leave invalid list tags; normalize address
  content before list realization. Use heading depth for normalization, since
  querying a level that the same rule changes can prevent layout convergence.
- Pair strict UA compilation with veraPDF report checks; successful compilation
  alone does not establish accessible reading order or content quality.
