# Typst document publishing

## Intentions

Keep local Markdown-to-PDF publishing reproducible and easy to maintain. Phoenix
owns compiler, reusable designs and adapters; vaults retain private notes, identity
fields, plugin installation and unrelated settings. Preserve upstream letter design.

## Architecture and dependencies

- `templates/phoenix-letter/`: reusable `@local/phoenix-letter:0.1.0` package,
  independent of Obsidian. Wraps `@preview/letter-pro:3.0.0` without modifying it.
- `template-adapters/omd2typst/`: thin YAML/content adapter exposing Omd2Typst's
  `template`, `callout` and language-discovery dictionary.
- The original four flat files in `templates/` remain unchanged Omd2Typst
  adapters, including `letter-pro.typ`. They are not standalone letter designs.

Letter Pro’s composable `letter-generic` and address/header helpers provide A4
DIN 5008-B geometry and right-aligned multipage footers. Phoenix supplies the
return-address rule, information block and first-sheet handling marks. Phoenix uses embedded
Liberation Sans (explicitly provided by `liberation_ttf`), with 10pt body text and
12.5pt headings. Obsidian's PDF.js maps unembedded Helvetica to its Liberation Sans
fallback; Poppler can choose a different substitute. Do not infer a viewer's actual
glyphs from another renderer's font report. Phoenix embeds the installed font so
its own output is consistent across viewers; different Liberation releases are
not claimed to be identical.

The spacing follows Letterhead 1.10.0's vector-export code: 14.5pt line baselines,
21.5pt baseline distance across ordinary paragraph boundaries, 23pt after the
standard greeting, 28.375pt from the preceding body line to a heading baseline,
20.925pt from heading to body baseline, and 12.15pt information-row baselines.
These are measured baseline distances, not CSS margins or Typst edge spacing.
Following pages have a 25mm top margin. This retains justification and explicit German automatic hyphenation in the body;
hyphenation costs are unchanged. The generic upstream entry point avoids the
simple preset’s implicit author and body-style overrides. Body margins remain upstream's 25mm left and 20mm right.

Aktenzeichen and date share the right-hand information block beside the recipient,
with values aligned to the body's right edge. They no longer add rows above the
subject. Multipage footers read “Seite X von Y” in 9pt `#666666` (about 5.74:1
contrast on white, above the [WCAG normal-text 4.5:1 threshold](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html)).
This contrast check alone is not a claim of complete PDF accessibility.

There is no cover or TOC. Keep the greeting, closing and sender name as separate
plain Markdown paragraphs; no spacing commands or new YAML fields are required.
The conventional “Mit freundlichen Grüßen” paragraph gets about 31.14pt baseline
separation from the preceding paragraph and stays with the following signature. A plain paragraph exactly matching
`sender_name` receives about 21mm baseline-to-baseline signing space above it;
ordinary inline mentions are unchanged. The template does not append duplicate
names or invent a greeting. Sender address remains a single line separated with
`, `; upstream splits it into header lines.

The adapter neutralizes enumerated-list layout in multiline address metadata:
Omd2Typst otherwise interprets a line such as `29. Kammer` as Typst enumeration,
adding unwanted spacing. Addresses remain compact with the number retained.
Phoenix places the return address in the top 5mm row, with a 1.2mm gap before
an 80mm rule. The reserved postal area and recipient zone starting at 62.7mm
remain unchanged. Letterhead’s compact recipient begins earlier; it is not used
to redefine the DIN B recipient zone. Fold marks extend 5mm from the left page
edge at 105mm and 210mm; the punch mark extends 8mm at 148.5mm. All use a 0.25pt
stroke and appear on the first page only. Printing to the edge depends on the printer.
The typography takes inspiration from [Letterhead](https://github.com/johannes-kaindl/obsidian-letterhead);
Phoenix includes no Letterhead code or fonts.

The fixture checks the return row separately from the recipient and checks the
nominal 85 × 45mm Form B field (x=20–105mm, y=45–90mm), with recipient text starting near y=62.7mm. This is a
PDF geometry check; actual window visibility also depends on envelope and folding.
See the [Klett DIN 5008 teaching diagram](https://www.klett.de/inhalt/media_fast_path/32/DO01_3-12-007171_Onlinematerialien_DIN5008.58281.pdf)
for the 17.7mm upper zone and 27.3mm recipient zone. This is not a certification
against the full paid standard. Do a print/fold check before first postal use.
Keep sender/recipient lines short enough for the window; the template does not shrink overflowing addresses silently.

Home Manager installs the wrapper as a local package link to the configured
`user.repoDirectory`: saved design changes are immediately visible to Typst. This
is deliberately a live source link, not an immutable design snapshot. It requires
that checkout to remain available. The original template distribution remains at
`~/.local/share/phoenix/typst/templates`.

The existing pinned import/cache was offline-capable only after a successful
network download. Phoenix now fetches the official Letter Pro 3.0.0 archive with
a fixed SHA-256 and installs it in the Typst **data** package directory, which
precedes the cache. No vendored upstream copy or additional package framework is
needed. Nix's first build needs network/cache access; subsequent letter compilation
needs neither. Other original adapters retain their cache/download behavior.
Typst and fonts come from locked nixpkgs. See [Typst package documentation](https://github.com/typst/packages#local-packages)
and [Letter Pro source](https://github.com/Sematre/typst-letter-pro).

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
Export from the live UI remains a user check. Check the template picker/export in
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
above, not `sender.name`. The plugin’s separate default-language setting does
not supply sender fields; repeating `language: de` is harmless.

ISO dates, German numeric dates and written German month names are rendered as
`DD.MM.YYYY`; custom date text is preserved. `sender_extra`, `reference` and
`date` may be omitted; no date is invented.
All sender fields default to empty, with no public personal defaults. `recipient`
uses YAML literal multiline syntax. `subject` also supplies the PDF title and
`sender_name` supplies the author. Missing sender fields compile safely with no
identity or PDF author; signing-space recognition requires `sender_name`. Only these listed keys reach
the wrapper. Unrelated metadata such as `chatgpt_chat` stays out of rendered text
and PDF metadata, though the plugin can include it in intermediate `.typ` source.
`title`, cover and TOC metadata are deliberately unused by this letter adapter.
Language defaults to German (`de`); `en` is accepted for English body hyphenation,
while the requested footer/reference labels remain German.

## Standalone CLI and checks

After installation:

```sh
typst compile modules/apps/documents/typst/tests/standalone.typ /tmp/letter.pdf
```

Import `@local/phoenix-letter:0.1.0` and apply
`#show: phoenix-letter.with(sender: (name: "…", address: "…"), recipient: […],
subject: "…", date: "…", reference: "…", language: "de")`.
No Obsidian or Markdown converter is needed. The source package also supports
relative imports for repository-local use; upstream must still be available.

Focused checks (Node, Typst and Poppler `pdftotext`/`pdfinfo` on PATH):

```sh
typst compile modules/apps/documents/typst/tests/optional-sender.typ /tmp/optional-sender.pdf
python3 modules/apps/documents/typst/tests/deployment.py
# Use a disposable vault; its adapter link must point to a disposable copy:
node modules/apps/documents/typst/tests/omd2typst.cjs /path/to/omd-to-typst/main.js /tmp/test-vault
```

The latter executes the installed plugin's actual WASM converter and PDF export
path with filesystem-backed Obsidian test doubles. It checks a representative
three-page German letter, automatic hyphenation, sender/recipient, page totals,
metadata exclusion, same-folder output, missing-sender export and rereading adapter edits. Its PDF layout
check also measures window bounds, numbered chamber-line spacing, paragraph rhythm,
signature space and embedded fonts. Never aim the reload test at the live vault or
the repository adapter: it deliberately edits its disposable source copy. It does not
prove live Electron template discovery. Inspect PDFs visually as well; source
fixtures use fictional identity data. Compilation alone cannot establish layout.

## Upstream templates

| Obsidian name | Pinned import | Origin and license |
| --- | --- | --- |
| Letter Pro | `@preview/letter-pro:3.0.0` | [Sematre / typst-letter-pro](https://typst.app/universe/package/letter-pro/), MIT |
| Briefs | `@preview/briefs:0.4.0` | [Tobias Enderle / briefs](https://typst.app/universe/package/briefs), MIT |
| Formal | `@preview/formal:0.2.0` | [Vsevolod Shegolev / formal](https://typst.app/universe/package/formal/), MIT package code; MIT-0 templates |
| Metropole Report | `@preview/metropole-report:0.1.0` | [Haydn Trowell / metropole-report](https://typst.app/universe/package/metropole-report/), GPL-3.0-or-later |

Typst Universe pages are the source for versions and licensing; this README
records the versions selected for Phoenix. To update a design, check its
upstream API and license, change the pinned import (for Phoenix letters also update the fixed archive
URL/hash in `default.nix`), compile representative English and German documents,
and update this table.
Nixpkgs supplies the compiler version; it is intentionally not pinned through a
separate package framework.
