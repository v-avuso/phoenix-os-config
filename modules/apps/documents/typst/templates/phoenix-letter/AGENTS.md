# Phoenix Letter maintenance

- `template/` owns the standalone package; `adapters/omd2typst/` owns conversion.
  Keep the public `@local/phoenix-letter:0.1.0` import and `phoenix-letter` adapter
  identifier stable during structural changes. Retain outer `lib.typ`/`typst.toml`
  compatibility links while old deployed package links remain in use; see the
  [integration boundaries](README.md#integration-boundaries-and-decisions).
- Read [template/DOCU.md](template/DOCU.md) before consequential template/design
  changes and update its affected rationale, alternatives and tradeoffs. Integration
  decisions belong in [README.md](README.md), not the standalone design history.
- Use Letter Pro’s composable helpers for wrapper-owned styles and metadata.
  Its simple preset disables hyphenation and assumes a sender author; verify
  rejected missing sender fields as well as actual German PDF line endings.
- Require sender name/address and recipient instead of silently omitting letter
  identity. Check the top-right sender block separately from the return row;
  one occurrence of the sender name does not prove both are present.
- Use flat sender keys. Numbered chamber-address lines can become enum items;
  verify compact spacing with the actual converter. Normalize address content
  before list realization: replacing an enum in a show rule can leave invalid PDF
  list tags. Use source heading depth for normalization; querying a level changed
  by the same rule can prevent layout convergence.
- Match reference typography against its actual exporter and the intended viewer's
  font mapping; Poppler substitution does not establish Obsidian glyphs. Measure
  line, heading and information-row baselines separately, not just one paragraph gap.
- Check the return-address row separately from recipient/window containment.
  Keep the top return row, reserved postal area and DIN B recipient start distinct;
  changing return-rule padding must not shift the recipient into the postal area.
- Use this component's [test runner](tests/run.py) with the installed Omd2Typst
  plugin; it covers standalone and converter behavior using disposable sources.
  The lower-level reload fixture deliberately edits its adapter: never point it
  at a live vault or repository adapter. See [integration checks](README.md#integration-checks)
  and [template checks](template/README.md#validation) for commands and limits.
