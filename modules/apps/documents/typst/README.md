# Typst document publishing

## Intentions

Provide a low-maintenance local Markdown-to-PDF route from Obsidian while keeping
the compiler, templates, and adapter customizations declarative in Phoenix.
Private notes and PDFs stay in the user's vault or chosen output directory.

Phoenix installs `typst` in the system profile so Obsidian's child process can
find it on `PATH`. It installs the template files under
`~/.local/share/phoenix/typst/templates`. The four `.typ` files are thin
Omd2Typst wrappers around versioned Typst Universe packages; they are editable
in Phoenix and do not copy upstream designs into this repository.

Omd2Typst is a per-vault Obsidian community plugin and is deliberately not
installed or configured by Nix. Its template picker only registers `.typ` files
inside the active vault, and its selected/default template settings are stored
in that vault. After installing Omd2Typst manually:

1. Copy the four files from `~/.local/share/phoenix/typst/templates/` into a
   folder such as `Templates/Typst/` inside the vault.
2. In **Settings → Omd2Typst → Typst templates**, add all four `.typ` files.
3. Select **Metropole Report** as the default general document template. Set
   the default language to English or German as appropriate; a note's
   `language: en` or `language: de` frontmatter overrides that default.
4. Leave the output format as PDF. Use **Export as PDF** from the command
   palette or note context menu.

The vault copy is necessary because Omd2Typst resolves registered templates
through Obsidian's vault API. Re-copy the files after changing their Phoenix
sources. The first PDF export of each template may need network access so Typst
can fetch its pinned `@preview` package; later builds use Typst's package cache.

## Frontmatter and language

The adapters read only the presentation fields each upstream design supports
(`title`, `subtitle`, `author`, `date`, `subject`, and `language`) and expose
English and German to Omd2Typst's language selector. Other YAML keys such as
`source_chat` are ignored by the adapters and do not become PDF text. Omd2Typst
handles Markdown conversion, headings, tables, lists, callouts, cover/TOC
metadata, and pagination; Typst's
paragraph language setting provides language-aware hyphenation. Formal,
Briefs, and Letter Pro retain their upstream layout functions. The minimal
`callout` adapter emits the converted callout title and body without imposing a
new style on the upstream designs.

Letter Pro and Briefs are letter layouts. Their adapters map `subject` (falling
back to `title`) to the letter subject; they leave sender and recipient address
fields at upstream defaults, so they are selectable but need a small adapter
edit before they can produce fully addressed business letters. Briefs uses its
upstream default date when none is supplied. Metropole Report is the
recommended general-purpose default and uses the upstream title, subtitle, and
author presentation.

## Upstream templates

| Obsidian name | Pinned import | Origin and license |
| --- | --- | --- |
| Letter Pro | `@preview/letter-pro:3.0.0` | [Sematre / typst-letter-pro](https://typst.app/universe/package/letter-pro/), MIT |
| Briefs | `@preview/briefs:0.4.0` | [Tobias Enderle / briefs](https://typst.app/universe/package/briefs), MIT |
| Formal | `@preview/formal:0.2.0` | [Vsevolod Shegolev / formal](https://typst.app/universe/package/formal/), MIT package code; MIT-0 templates |
| Metropole Report | `@preview/metropole-report:0.1.0` | [Haydn Trowell / metropole-report](https://typst.app/universe/package/metropole-report/), GPL-3.0-or-later |

Typst Universe pages are the source for versions and licensing; this README
records the versions selected for Phoenix. To update a design, check its
upstream API and license, change the pinned import in the corresponding adapter,
compile representative English and German documents, and update this table.
Nixpkgs supplies the compiler version; it is intentionally not pinned through a
separate package framework.
