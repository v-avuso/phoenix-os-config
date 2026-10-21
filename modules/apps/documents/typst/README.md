# Typst document publishing

## Intentions

Generate professional German letters from Markdown or standalone Typst with
predictable layout, justified text, automatic hyphenation and private metadata.
Keep reusable designs independent of Obsidian and configuration easy to maintain.

Phoenix Letter uses A4/DIN 5008-B geometry, Liberation Sans, a window-address field,
fold/punch marks and discreet “Seite X von Y” pagination. There is no cover or TOC.
The return row uses 8pt dark gray; body text is 10pt. Links have dark dotted
underlines. Long return rows fail clearly instead of clipping.

See [DOCU.md](DOCU.md) for design decisions, history, Letterhead attribution,
precise spacing/colors, dependency/licensing audit and future considerations.

## Requirements and architecture

The Phoenix NixOS/Home Manager module supplies Typst, fonts (including
`liberation_ttf`), and the pinned official Letter Pro 3.0.0 archive. The first Nix
build may need network/cache access; installed Phoenix letters compile offline.
The reusable `@local/phoenix-letter:0.1.0` package links to this repository's
`templates/phoenix-letter/`; saved changes are immediately available. Keep the
configured `user.repoDirectory` checkout available. This is a live source link,
not an immutable design snapshot.

For Markdown export, install Omd2Typst separately in the vault (tested: 0.9.0,
Typst 0.14.2). `template-adapters/omd2typst/` maps the supported metadata/content
to the design. The original four flat files in `templates/` are separate existing
adapters, not standalone designs; their original cache/download behavior remains.
Their distribution stays at `~/.local/share/phoenix/typst/templates`.

## Installation and Obsidian

Activate the Phoenix configuration using the normal reviewed deployment flow.
Install Omd2Typst separately in the vault. Then, with Obsidian closed (or the
plugin disabled), register the vault once:

```sh
phoenix-typst-vault --register /absolute/path/to/vault
```

This creates one **directory symlink** at
`3-misc/phoenix-typst/omd2typst` pointing to this checkout's
`template-adapters/omd2typst` directory. Its parent folders remain regular vault
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
Live exports and visual output were accepted by the operator on 2026-10-21. Check the template picker/export in
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

## Standalone Typst

After Phoenix installation, compile the example:

```sh
typst compile modules/apps/documents/typst/tests/standalone.typ /tmp/letter.pdf
```

Or create a source independent of Obsidian:

```typst
#import "@local/phoenix-letter:0.1.0": phoenix-letter
#show: phoenix-letter.with(
  sender: (name: "Erika Beispiel", address: "Musterstraße 12, 12345 Musterstadt"),
  recipient: [Sozialgericht Musterstadt\ Gerichtsstraße 1\ 12345 Musterstadt],
  subject: "Stellungnahme", date: "19.10.2026", language: "de",
)
Sehr geehrte Damen und Herren,

= Sachverhalt
Hier steht der Brieftext.

Mit freundlichen Grüßen
```

`signature` has the same closing-name behavior as the adapter. Set
`link-underline: "solid"` to use conventional solid link underlines; the default is
`"dotted"`. Body text/destinations stay unchanged. Repository-relative imports also
work when upstream is available; a local-package installation is not mandatory.

## Validation

Use short address lines. The recipient grows downward in the nominal field;
six fixture lines fit, but extra/wrapped lines may not. To check an individual PDF,
supply every expected address line, including its return row:

```sh
python3 modules/apps/documents/typst/tests/window.py /path/to/letter.pdf \
  "Erika Beispiel · Musterstraße 12 · 12345 Musterstadt" \
  "Sozialgericht Musterstadt" "Gerichtsstraße 1" "12345 Musterstadt"
```

The checker fails on missing, wrapped or out-of-bounds lines. It measures nominal
PDF geometry, not actual envelopes/printer tolerances. No complete DIN certification
is claimed; the recipient overflow checker is not run automatically on every export.

Normal Obsidian PDF export stays unchanged. For opt-in PDF/UA-1 checks on exported
Typst source, supply the vault root for its vault-relative adapter import:

```sh
typst compile --root /path/to/vault --pdf-standard ua-1 /path/to/vault/letter.typ /tmp/letter-ua.pdf
verapdf --flavour ua1 /tmp/letter-ua.pdf
```

Strict export requires a nonempty `subject`/PDF title and valid heading hierarchy.
The adapter normalizes the shallowest Markdown heading depth to H1, preserving
relative levels. Automated PDF/UA checks do not certify screen-reader usability
or every content-dependent accessibility requirement. Inspect PDFs visually too.

For the complete regression suite, use the repository's locked test dependencies:

```sh
letter_nixpkgs="$(nix eval --raw --no-write-lock-file .#nixosConfigurations.metal.pkgs.path)"
nix-shell -I "nixpkgs=$letter_nixpkgs" \
  -p typst nodejs poppler-utils verapdf 'python3.withPackages (p: [ p.pypdf ])' \
  --run 'python3 modules/apps/documents/typst/tests/run.py /path/to/omd-to-typst/main.js'
```

The runner owns disposable fixtures/vaults; it checks standalone/converter exports,
layout, pagination, address overflow, links, privacy, font subsets and strict UA-1
output with independent veraPDF validation. Cached checks took about 5.2 seconds
locally; initial downloads include Java. `PHOENIX_PDF_PYTHON` and `VERAPDF` can
select alternate test executables. Never aim the lower-level adapter-reload test at
a live vault or the repository adapter: it deliberately edits its disposable copy.

## Attribution and licenses

Phoenix Letter imports [Letter Pro 3.0.0](https://github.com/Sematre/typst-letter-pro)
(MIT), uses [Typst](https://github.com/typst/typst) (Apache-2.0) and embeds Liberation
Sans (OFL-1.1). [Letterhead](https://github.com/johannes-kaindl/obsidian-letterhead)
inspired the typography; its plugin code is not bundled. Omd2Typst is separately
installed. See [the provenance audit](DOCU.md#provenance-licensing-and-credit) for
exact plugin licenses, redistribution considerations and other existing templates.
No new Phoenix software license is assigned by this documentation.

When updating upstream, verify its API/license, adjust the pinned import and the
archive URL/hash in `default.nix`, and rerun representative German/English and
accessibility checks. Compiler/fonts come from locked nixpkgs.
