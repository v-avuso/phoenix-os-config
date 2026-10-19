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

Letter Pro provides A4 DIN 5008-B geometry, address window, sender header/return
address, fold/hole marks and right-aligned multipage footers. Phoenix keeps Source
Sans Pro, adds German body hyphenation **inside** the upstream body (upstream sets
`hyphenate: false`), justified paragraphs and sticky headings. Page totals read
“Seite X von Y”. There is no cover or TOC. Greeting, closing and signature belong
in the body. Sender address is a single line separated with `, `; upstream splits
it into header lines. Keep it short enough for the return-address window.

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
date: "19. Oktober 2026"
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

`sender_extra`, `reference` and `date` may be omitted; no date is invented.
All sender fields default to empty, with no public personal defaults. `recipient`
uses YAML literal multiline syntax. `subject` also supplies the PDF title and
`sender_name` supplies the author, as in upstream. Only these listed keys reach
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
python3 modules/apps/documents/typst/tests/deployment.py
# Use a disposable vault with the plugin data.json and deployed adapter directory:
node modules/apps/documents/typst/tests/omd2typst.cjs /path/to/omd-to-typst/main.js /tmp/test-vault
```

The latter executes the installed plugin's actual WASM converter and PDF export
path with filesystem-backed Obsidian test doubles. It checks a representative
three-page German letter, automatic hyphenation, sender/recipient, page totals,
metadata exclusion, same-folder output and rereading adapter edits. It does not
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
