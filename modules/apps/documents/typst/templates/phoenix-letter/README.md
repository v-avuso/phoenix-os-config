# Phoenix Letter integration

## Intentions

Keep a reusable formal-letter template and thin adapters together, while preserving
independent template use and a single canonical adapter source.

## Integration boundaries and decisions

`template/` is the standalone Typst package. `adapters/omd2typst/` owns the single
canonical converter adapter. The module-wide collection contains a relative link
to that file; the vault links to the entire collection. Public identifiers remain
`@local/phoenix-letter:0.1.0` and `phoenix-letter`.

The outer directory can later be extracted as an integration repository, while
`template/` could become an independent repository/submodule. No submodule exists
now. The template still imports Letter Pro 3.0.0, provided offline by Phoenix;
font/compiler and vault registration belong to the parent Nix module. See its
[README](../../README.md) for declarative installation and source-store checks.

Two compatibility links, `lib.typ` and `typst.toml`, point into `template/` so the
previously installed local-package link continues working without activation.
New Home Manager configuration points directly at `template/`. Keep the bridges
until old deployed package links are no longer used; they contain no duplicate code.

The initial periodic copying service was rejected: symlink incompatibility had
not been established, synchronization was unnecessary and redirected parents
introduced risks (`a187a8a`). One directory link makes saved edits/new adapters
available immediately; migration preserves old copies. Nix pins/fetches upstream,
but the local design remains a live checkout link, not an immutable output snapshot.

Private defaults stay in the vault. Inline/file frontmatter templates are insertion
sources rather than background export defaults; note values remain explicit.
Unknown keys are excluded by an allowlist, though intermediate generated `.typ`
files can contain them. These are converter semantics, not template styling.

The adapter reconstructs numbered chamber-address items as text before list
realization. A show-rule-only replacement previously left invalid PDF list tags.
It normalizes the shallowest Markdown heading depth to H1 using semantic show-set
rules, preserves relative hierarchy and rejects skipped levels in strict UA export.
It queries source depth rather than the changing rendered level to avoid convergence
loops. These conversion responsibilities stay outside the reusable template.

## Installation and Obsidian

Activate the Phoenix configuration using the normal reviewed deployment flow.
Install Omd2Typst separately in the vault. Then, with Obsidian closed (or the
plugin disabled), register the vault once:

```sh
phoenix-typst-vault --register /absolute/path/to/vault
```

This creates one **directory symlink** at
`3-misc/phoenix-typst/omd2typst` pointing to this checkout's
`template-adapters/omd2typst` aggregation directory. Its parent folders remain regular vault
directories. Saved edits and new adapters are visible through the link immediately;
there is no copying service, timer, or persistent vault registry. Keep the configured
checkout available. Edit adapters in Phoenix; editing through the vault link also
edits the repository. A second machine needs its own valid local link.

`--register` registers `phoenix-letter` and sets PDF output to `same-folder`.
Existing templates, the default template and unrelated plugin settings are preserved.
Enable/reload Omd2Typst after registration so it reads the settings. Choose
**Export as PDF with template… → phoenix-letter** for letters. A note
`folder/Name.md` exports to `folder/Name.pdf` (replacing an existing PDF).

For an existing copied adapter directory, migrate once:

```sh
phoenix-typst-vault --migrate-copies /absolute/path/to/vault
```

The previous directory is preserved as hidden `.omd2typst.before-symlink` beside
the new link; an existing backup or unexpected link is never replaced. Existing plugin
paths remain valid, so migration needs no settings rewrite. The command refuses
symlinked parent directories beneath the vault and never copies adapter contents
through the destination link. To restore the copies, remove only the `omd2typst`
symlink and rename `.omd2typst.before-symlink` back to `omd2typst`.

Omd2Typst requires a vault-indexed `TFile`. The filesystem-backed installed-plugin
fixture verifies export and rereading edited adapters through a directory link;
live Obsidian directory-link discovery was also confirmed in the template list.
Live exports and visual output were accepted before this structural refactor;
filesystem/store checks cover the new link chain. Check the template picker/export in
Obsidian after creating the link; reload Obsidian if needed. Folder symlinks have
[documented Obsidian limitations](https://obsidian.md/help/symlinks), especially
with syncing and overlapping link targets. If this installation cannot index the
folder reliably, retain regular copies and refresh them manually rather than
introducing background polling.

## Letter frontmatter

Use these exact **flat** YAML keys. Omd2Typst 0.9.0 flattens nested YAML mappings,
so `sender: {name: ...}` is not supported. Replace all placeholders privately:

```yaml
---
subject: "Stellungnahme im Verfahren …"
date: "19.10.2026"
reference: "S … …/…"
language: de
sender_name: "Vorname Nachname"
sender_address: "Straße Hausnummer, PLZ Ort"
sender_extra: "Optionale Telefonnummer oder E-Mail"
recipient: |
  Sozialgericht Ort
  Straße Hausnummer
  PLZ Ort
---
```

Omd2Typst’s inline frontmatter editor defines an **insertion template**, not
export-time defaults. Run **Omd2Typst: Insert frontmatter** in an existing note
to merge missing keys from it, preserving existing values. Keep the flat keys
above, not `sender.name`. This applies to both inline and Markdown-file
insertion sources; neither supplies export-time fallback metadata. The plugin’s separate default-language setting does
not supply sender fields; repeating `language: de` is harmless.

ISO dates, German numeric dates and written German month names are rendered as
`DD.MM.YYYY`; custom date text is preserved. `sender_extra`, `reference` and
`date` may be omitted; no date is invented.
Nonblank `sender_name`, `sender_address` and a nonempty `recipient` are required.
Missing required identity/address fields stop compilation with a descriptive error;
there are no public personal defaults. `recipient`
uses YAML literal multiline syntax. `subject` also supplies the PDF title and
`sender_name` supplies the author. `signature` controls only the closing name, never PDF authorship. Only these listed keys reach
the wrapper. Unrelated metadata such as `chatgpt_chat` stays out of rendered text
and PDF metadata, though the plugin can include it in intermediate `.typ` source.
`title`, cover and TOC metadata are deliberately unused by this letter adapter.
Keep the greeting and closing as plain Markdown paragraphs. The closing name is
generated from `sender_name` with signing space. Omit `signature` or use `signature: ""`
for that default; use `signature: "Other name"` to override or `signature: " "` to
suppress it. An existing plain body paragraph exactly matching `sender_name` is
removed to avoid duplication; inline mentions remain unchanged.

Language defaults to German (`de`); `en` is accepted for English body hyphenation,
while the requested footer/reference labels remain German.

## Integration checks

Run `python3 tests/run.py /path/to/omd-to-typst/main.js` from this directory with
Typst, Node, Poppler, pypdf and veraPDF available. The [module runner](../../tests/run.py)
also checks shared vault deployment; its README supplies a locked Nix shell.
The component runner owns disposable fixtures and an aggregation-to-canonical
adapter link. Never run its lower-level reload fixture against a live vault or
repository adapter: it deliberately edits its disposable copy.

The installed plugin's real WASM conversion/export is exercised with filesystem
Obsidian doubles. It checks same-folder export, source reload, metadata filtering,
address normalization, layout, regular/bold font subsets and links. Strict UA-1
compilation plus veraPDF report checks must pass; the structural checker verifies
German language/title, H1/H2, expected reading sequence, artifacts, wrapped link
quadrilaterals and decoded metadata exclusion. A deliberately skipped heading level
must fail. Core standalone/pagination fixtures remain in `template/tests/`.

Runtime needs the separately installed Obsidian/Omd2Typst plugin and the standalone
template dependencies. Node/Poppler/pypdf/veraPDF/Java are development-test tools,
not ordinary export requirements. Python powers Phoenix's shared registration helper.
The previous full cached suite took about 5.2 seconds; initial Java downloads are
separate costs. This is not a performance guarantee. Live Electron discovery,
screen-reader usability and all future content-dependent cases are not established
by the doubles or machine checks. See the template's [rationale](template/DOCU.md)
for visual QA history, accessibility limits and upstream attribution.

## Future scope

[VISION.md](VISION.md) records exploratory standalone application ideas, not an
implementation commitment. Letter Pro remains in use; no extraction or upstream
rewrite is part of this directory refactor.

Extraction would still require Nix source/input wiring, dependency/font provisioning,
an explicit public-license decision and distribution checks. A future nested Git
submodule is not automatically a recursively captured Nix-flake input. Update the
central aggregation link and source-store fixture as part of such a separately
scoped change; the current layout alone does not solve future source pinning.
