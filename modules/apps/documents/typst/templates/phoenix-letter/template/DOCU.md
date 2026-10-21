# Phoenix Letter: design, history and provenance

## Intentions and evidence

Provide attractive, reusable German formal letters with justified text, automatic
hyphenation and predictable PDF output. Preserve the accepted appearance, keep
private identity/content outside public sources, and minimize maintenance.
[README.md](README.md) owns installation and everyday use; this document owns
rationale, trade-offs and provenance. No future implementation is authorized here.

Implementation was audited at commit `2e1d70a`, with Letter Pro 3.0.0, Typst 0.14.2,
Letterhead 1.10.0 and Omd2Typst 0.9.0. Source/tests establish current behavior;
Git establishes committed changes. The operator's supplied design account records
personal preferences and earlier experiences that Git cannot independently prove.
Visual acceptance was reported on 2026-10-21. No private letter or conversation
link is reproduced here.

## Evolution and alternatives

| Decision or correction | Reason and trade-off | Evidence |
| --- | --- | --- |
| Start with Letter Pro rather than create a letter engine | The operator preferred its example's alignment, sender/recipient arrangement and proportions when considering Letter Pro and Briefs. That was an initial visual judgment, not a comparative quality study. | Operator account; existing pinned adapters |
| Use Typst/Omd2Typst for production | The operator found Letterhead's desktop printing workflow inconvenient, and its tested vector export did not deliver the desired German hyphenation and justification. Typst provides those capabilities plus scriptable standalone output. This records the evaluated workflow/version, not a universal claim about future Letterhead releases. | Operator account; installed exporters; `3c2420c` |
| Refine the initial Letter Pro-based appearance | Early Phoenix output did not match the desired paragraph, heading and address rhythm. Letterhead supplied a concrete visual reference. Those criticisms concerned Phoenix's result, not proof that Letter Pro itself is poorly designed. | `bcb772b`, `5eff558` |
| Replace polling copies with a directory symlink | The initial recurring copy mechanism was unnecessary, had not established symlink incompatibility, and introduced redirected-path risks. One directory link exposes source edits/new adapters immediately without a synchronization process. Migration preserves previous copies. | `a187a8a`, deployment fixture; operator-confirmed live exports |
| Measure the intended viewer/exporter | An early approximate font/spacing match was insufficient. Inspecting Letterhead's exporter and the actual Obsidian PDF viewer distinguished glyph substitution from PDF geometry. | `5eff558` |
| Use composable Letter Pro helpers instead of `letter-simple` | Phoenix needed direct ownership of the return rule, metadata validation and typography. The simple preset disables hyphenation and assumes a sender author; composition avoids modifying upstream. | `17aee9f`, current wrapper |
| Reject incomplete sender/recipient data | Temporarily accepting absent sender fields silently produced an incomplete letter. Missing identity should be actionable failure, not a successful-looking PDF. | `17aee9f` followed by correction `ead47c3` |
| Generate the closing name | Reuse sender metadata, retain signing space and avoid repetitive Markdown. Explicit override/suppression remains possible; an existing plain sender-name paragraph is removed to avoid duplication. | `ead47c3` |
| Reduce secondary text weight, then strengthen the tiny return row | A calculated contrast threshold suited pagination; small address text benefited from a larger size and darker gray after review. | `9556850`, `2e1d70a` |
| Add targeted layout and accessibility regressions | Compilation alone missed appearance and missing-block problems. Check both sender locations, window bounds, actual converter output and semantic structure. | `833905f`, `2e1d70a` |

Font experiments were deliberately uncommitted. Their absence from commit history
is expected; the accepted source again explicitly selects Liberation Sans.

## Why Letterhead's spacing appealed

The strongest technical explanation is a coordinated visual rhythm: regular line
steps, distinct paragraph boundaries, deliberate space around headings and the
closing, and restrained administrative details. Alignment repeats across the
page, while gray secondary text gives the recipient and body stronger emphasis.
These are plausible design explanations for the operator's preference, not a
scientific demonstration that one template is universally more readable.

The installed Letterhead vector exporter uses a line-height factor of 1.45.
Phoenix's reference-derived 10pt body therefore has 14.5pt line baselines. Across
ordinary paragraphs the baseline distance becomes 21.5pt: paragraphs are visibly
separate without adding empty Markdown paragraphs. Heading transitions use their
own distances rather than the same generic gap everywhere. The reserved signing
space makes the ending feel intentional and supports printing and signing.

| Current Phoenix measure | Purpose and qualification |
| --- | --- |
| 10pt Liberation Sans; 14.5pt line baselines | Restrained text size and predictable line rhythm; `leading: 4.5pt` is added to explicit text edges |
| 21.5pt paragraph-boundary baselines | Distinguish paragraphs; Typst's `spacing: 11.5pt` is not itself this baseline distance |
| 12.5pt headings; 28.375pt body-to-heading and 20.925pt heading-to-body baselines | Make sections easy to scan, with greater separation before a section than within it |
| 23pt greeting-to-body baselines | Separate the salutation without manual blank lines |
| 12.15pt information-row baselines | Avoid a cramped reference/date block |
| About 31.14pt before the conventional closing; about 21mm to the closing name | Deliberate ending and space for a handwritten signature |

These are baseline distances, not interchangeable CSS margins or glyph bounding
boxes. For example, the PDF test's 22.745pt heading/body bounding-box distance
includes a font-ascent difference; it represents the 20.925pt baseline target.
The implementation and [layout fixture](../tests/layout.py) are the authoritative
values. Some values were translated from inspected exporter behavior and measured
output into native Typst settings; Letterhead JavaScript is not bundled.

Larger spacing everywhere was never the rule. Early Phoenix versions used different
font sizes and relative spacing, so there is no single valid claim that every gap
increased. The improvement came from consistent proportions, appropriate text
edges/font rendering, hierarchy and repeated visual review. Comparing PDFs at
different zoom levels or through different font substitutes can obscure this.

## Typography and font choice

Readability and a quiet formal appearance take priority over ornament. Justified
German paragraphs and automatic language-specific hyphenation stay enabled.
Long compounds otherwise create difficult line breaks and uneven word spacing;
hyphenation helps justification without adding discretionary hyphens to Markdown.
The body explicitly sets `lang: "de"` by default; hyphenation costs are unchanged.

| Candidate | Recorded evaluation |
| --- | --- |
| Liberation Sans | Operator preferred its clarity, balance and suitability for formal correspondence; final choice. Regular/bold are explicitly embedded as subsets. |
| Source Sans 3 | Installed temporarily and compared in exported PDFs, then rejected. No more specific separate reason was recorded in this chat. |
| Open Sans | The supplied operator account describes a smaller/compressed impression. This session's executable experiment used Source Sans 3, IBM Plex Sans and Geist; an Open Sans installation/export was not independently verified. |
| IBM Plex Sans | Operator account describes distinctive letterforms, numerals and capital-I shapes as too decorative or dated for this use. |
| Geist | Operator account describes a modern appearance but comparatively cramped dates/numerals and some word spacing. A separate personal system-font installation remains outside the letter design. |

These are personal judgments about real comparisons, not measured readability
rankings. The initial wrapper used Source Sans Pro, an intermediate revision used
TeX Gyre Heros, and `5eff558` selected Liberation Sans. Source Sans Pro and Source
Sans 3 should not be treated as identical releases/family names.

The Letterhead reference PDF used unembedded Helvetica. Obsidian PDF.js's Helvetica
fallback informed the Liberation Sans choice; another viewer can select another
substitute. We do not redistribute Helvetica or assume Letterhead bundled it.
Phoenix embeds its installed font, giving consistent glyphs across viewers.
Different releases/substitutes need not be pixel-identical. Nix explicitly provides
`liberation_ttf`, rather than relying on a coincidental installed font.

## Geometry, hierarchy and accessibility decisions

| Decision | Reason, alternatives and limits |
| --- | --- |
| A4 with upstream DIN 5008-B geometry | Reuse established letter structure. Body margins remain 25mm left, 20mm right/bottom; following pages start at 25mm. No cover or TOC. |
| Nominal address field x=20–105mm, y=45–90mm | Separate the top 5mm return row, 12.7mm reserved postal area and 27.3mm recipient zone. Recipient is top-aligned at about 62.7mm and grows downward. Letterhead's reference starts its recipient around 54mm, leaving a smaller gap below the return rule. Both sample blocks fit the nominal field, but their internal allocation differs. |
| Retain the reserved postal area | Prefer upstream DIN B allocation over matching Letterhead's earlier recipient position. Tests show six fixture lines fit and a seventh overflows; this is not a guarantee for arbitrary line lengths, fonts or envelopes. |
| Middle dots, 80mm rule, 1.2mm clearance | Distinguish sender components and make the return row less crowded. The 8pt `#666666` text is measured before rendering; excessive width fails instead of clipping/shrinking silently. |
| Right-hand reference/date block | Cluster lookup information near the recipient without adding rows above the subject. Values align with the body's right edge. This is a house-style/workflow judgment, not a demonstrated case-worker productivity result. Numeric dates are normalized when recognized; no date is invented. |
| First-page fold marks at 105/210mm, punch mark at 148.5mm | Edge-starting 5/8/5mm marks help folding/alignment. Retain the thin 0.25pt stroke. First-page-only and mark lengths are design preferences; printers can clip edge content. |
| Primary text `#1a1a1a`; administrative labels/return row `#666666` | Restrained neutral palette. `#666666` gives about 5.74:1 on white, exceeding the 4.5:1 normal-text contrast criterion and providing more margin for the small return row. |
| 9pt pagination `#767676` | About 4.542:1 on white, the lightest whole-byte neutral gray meeting 4.5:1. Adjacent `#777777` gives only 4.478:1. A fixed calculated value avoids a runtime solver; no physical print-contrast guarantee follows. |
| Sticky semantic headings and default widow/orphan protection | Keep a heading with following text and prevent single-line split-paragraph fragments. Two lines below a heading remain acceptable; do not keep entire paragraphs together. Typst 0.14.2 lacks the requested robust native three-line minimum. Manual breaks/line-height estimates would be fragile; retain native behavior. |
| Dark native dotted link underline | Give a non-color cue without blue text or added bold. Rounded 0.6pt dots are deliberately visible at normal zoom and in print, with 1.8pt offset. Native links retain semantic tags/clickable wrapped quadrilaterals. `link-underline: "solid"` remains available. Hover highlights belong to the PDF viewer, not the template. |
| Bold for body emphasis | Use semantic strong emphasis where the author writes it, without making every link another competing emphasis style. |

[Letter Pro 3.0.0 source](https://github.com/typst/packages/blob/main/packages/preview/letter-pro/3.0.0/src/lib.typ)
provides the actual layout implementation. The
[Klett DIN teaching diagram](https://www.klett.de/inhalt/media_fast_path/32/DO01_3-12-007171_Onlinematerialien_DIN5008.58281.pdf)
illustrates the 17.7mm upper/27.3mm recipient zones. We have not independently
certified the complete paid DIN standard and reproduce none of its protected text.
The coordinate tests are best-effort nominal PDF checks, not envelope-tolerance tests.
For contrast, see [WCAG 1.4.3](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html);
meeting this particular digital criterion alone does not establish overall accessibility.
See [Typst's pagination limitation](https://github.com/typst/typst/issues/5931).

## Template boundary

The compiler supplies shaping, German hyphenation, justification, pagination,
PDF tagging and font subsetting. The imported Letter Pro package supplies layout
helpers. `lib.typ` owns presentation, sender validation, document metadata/date
handling, typography, return row, reference block, marks, closing name and links.
It contains no Obsidian integration.

The [integration package](../README.md#integration-boundaries-and-decisions) owns
Omd2Typst metadata normalization and its implementation history. The surrounding
[Typst module](../../../README.md) owns Nix/Home Manager, pinned upstream installation,
live local packages and adapter aggregation. Source directories were separated
after `b1c434d`; those commits retain their historical paths. An extraction would
still need dependency provisioning and licensing decisions, not a layout rewrite.

## Validation and its limits

The template fixtures are in `tests/`; the [integration runner](../tests/run.py)
exercises converter output. The [module README](../../../README.md) gives the locked
Nix test environment. Runtime requires Typst, font and Letter Pro; Markdown export also
requires Obsidian and its separately installed Omd2Typst plugin. Python powers the
registration helper. Node/plugin doubles, Poppler, pypdf, veraPDF and its Java
runtime are test tools, not requirements for ordinary standalone compilation.

- Standalone/default-date/solid-link compilation exercises the independent package.
- The installed plugin's actual WASM converter/export is used against a disposable
  vault and copied adapter. Same-folder output, metadata filtering and rereading
  edited adapter source are checked without changing real notes.
- PDF geometry/text/vector checks cover both sender locations, compact chamber lines,
  line/heading/paragraph rhythm, signing space, page totals, hyphenation, font subsets,
  first-page marks and all expected address lines. Six-line and overflow cases are
  contrasted; a longer return row fits and an excessive row is rejected.
- Strict `--pdf-standard ua-1` compilation and independent veraPDF 1.28.2 UA-1
  validation must pass. The report's compliance result is checked, not just exit status.
  pypdf checks German language/title, H1/H2 hierarchy, expected structural reading
  sequence, artifacts, link tags/wrapped destinations and decoded metadata privacy.
  A skipped heading level is deliberately rejected.
- Thirty-nine naturally paginated variants exercise short/long paragraphs and varied
  preceding text. Eight split cases included two two-line starts without stranded
  headings or single-line fragments. No product hard-coded breaks were introduced.
- Representative PDFs were inspected visually, followed by operator acceptance.
  This is manual visual QA plus automated geometry checks, not a pixel-diff suite.

The complete cached suite took about 5.2 seconds on the development machine;
initial tool downloads, especially Java, are separate costs. Measurements are
observations, not performance guarantees. Automated checks cannot establish
screen-reader usability, every possible reading order, meaningful author-provided
link descriptions, future images/tables, arbitrary address lengths, or physical
printing/envelope fit. Normal Omd2Typst export does not automatically enforce UA-1;
strict export/validation is opt-in and documented separately.

## Dependency audit: how much Letter Pro remains?

Four imported APIs are directly used. Their function definitions remain in upstream
`src/lib.typ`; none of those definitions was vendored into the Phoenix package.
Phoenix's composition also retains/adapts recognizable `letter-simple` idioms:
header padding/alignment and subject placement (10% right padding and 0.65em gap).
The wrapper is an upstream-based adaptation, not a claimed clean-room design;
those small composition expressions should retain Letter Pro provenance too.

| API | Work still delegated | What Phoenix supplies instead |
| --- | --- | --- |
| `letter-generic` | A4/page margins, first-page header/address/information layout, body transition, page-count handling and footer placement/alignment | Actual header/address/info content, top margin override, custom numbering text/style; disables upstream marks/reference-sign rows |
| `header-simple` | Name/address/extra assembly, strong sender name, 10pt header text | Sender values, line splitting and header padding/alignment |
| `address-tribox` | Fixed 5mm/12.7mm/27.3mm address-zone grid | Return row, empty postal annotations and recipient content |
| `recipient-box` | 10pt recipient text, top alignment, 5mm left inset | Normalized recipient content |

Phoenix additionally owns body/heading typography, hyphenation enablement,
closing/signing treatment, links, decorative marks, data validation and metadata.
Upstream still supplies the structural skeleton; the current visible style is
largely Phoenix policy. We no longer use `letter-simple`, `sender-box`,
`annotations-box`, `address-duobox`, upstream mark drawing or reference-sign rows.
The entire imported package remains a compilation dependency.

**A bounded percentage proxy:** at `2e1d70a`, ignoring blank/comment-only lines,
the four imported function declarations contain 149 source lines (111 + 14 + 19 + 5),
and the Phoenix wrapper contains 120. That is approximately **55% upstream / 45%
Phoenix** of those combined declarations. Counting the upstream format dictionary
adds 12 lines, giving about 57%/43%. This is reproducible by counting each `#let`
declaration up to the next one in the pinned source, dropping blank and `//` lines.
It includes unused upstream branches and excludes Typst internals, adapter, Nix,
tests and docs. It is neither an execution percentage, a measure of visual authorship,
nor “55% of Letter Pro's whole package is used.” **0% of upstream files were modified.**
A single percentage of design “overridden” has no objective denominator.

**Independence later:** replacing four small layout helpers is feasible. A rough,
unvalidated planning allowance is 0.5–2 developer days for implementation plus
representative layout/UA/export checks, depending on whether tagged-PDF reading
order remains stable. Copying MIT helpers is a vendored derivative with notices,
not provenance-free independence; an independently written layout still needs
geometry and regression verification. Benefits would be one fewer package/archive
and direct ownership of the page skeleton. Costs are taking over margins, zone
allocation, footer placement and associated compatibility/semantic behavior.

**Recommendation:** retain Letter Pro for this accepted release. It is pinned,
offline-capable and no longer blocks the design; no concrete upstream maintenance
failure justifies replacing working layout now. Reconsider during a separately
scoped standalone-package extraction, when reducing distribution dependencies
has a clear owner and acceptance budget. Removing Letter Pro would not remove
Typst, fonts or optional integration/tool licensing obligations.

## Provenance, licensing and credit

| Project/material | Verified source/license | Actual use |
| --- | --- | --- |
| [Letter Pro 3.0.0](https://github.com/typst/packages/tree/main/packages/preview/letter-pro/3.0.0) | MIT; package LICENSE credits Sematre and contributors, 2024 | Four functions imported unchanged; official archive installed through Nix with its LICENSE retained; header/subject composition also adapts upstream idioms |
| [Typst 0.14.2](https://github.com/typst/typst/blob/v0.14.2/LICENSE) | Apache-2.0 | Compiler/runtime, native layout and PDF semantics; installed through Nix, not vendored into Phoenix source |
| [Letterhead 1.10.0](https://github.com/johannes-kaindl/obsidian-letterhead/tree/56c63f472300ea9c06a10a1d27a22785761495f8) | [package.json](https://github.com/johannes-kaindl/obsidian-letterhead/blob/56c63f472300ea9c06a10a1d27a22785761495f8/package.json): AGPL-3.0-or-later; accompanying LICENSE is AGPL v3 | Design inspiration and inspected exporter metrics; no plugin code/font files imported, copied or bundled into Phoenix |
| [Omd2Typst 0.9.0](https://github.com/tIsGoud/Obsidian-Omd2Typst/tree/a700fa2db58091a588a4ab43d8aa83ae02955257) | [package.json](https://github.com/tIsGoud/Obsidian-Omd2Typst/blob/a700fa2db58091a588a4ab43d8aa83ae02955257/package.json): AGPL-3.0-only; accompanying LICENSE is AGPL v3 | Separately installed converter/plugin, invoked by a thin Phoenix adapter; no plugin implementation vendored |
| [Liberation Fonts 2.1.5](https://github.com/liberationfonts/liberation-fonts/blob/2.1.5/LICENSE) | Installed LICENSE: SIL OFL 1.1; Google/Red Hat copyrights and reserved names | Explicit font package; regular/bold subsets embedded in PDFs |

The exact release declarations matter: do not substitute GitHub's generic “AGPL-3.0”
label for the project's explicit `only`/`or-later` choice. The local installed plugin
manifests confirm versions; their release-tag source supplies license evidence.
Letterhead's metrics/appearance were translated into independently written Typst
settings rather than copied JavaScript. Source inspection establishes that reuse
boundary, not a general legal ruling about all visual imitation or derived works.

Keep Letter Pro's MIT copyright/license with redistributed copies or substantial
copied portions. Redistributing modified Apache-licensed compiler code requires
its applicable license/notices and change notices; applicable AGPL obligations
must be assessed if distributing/deriving from plugin code. Mere credit is not a
replacement for those obligations. Likewise, inspiration alone should not be used
to automatically assign an upstream code license to all Phoenix sources. If an
adapter or future app changes the integration/reuse boundary, review the actual
combined distribution rather than assuming separation resolves every license issue.

OFL permits font embedding; retain font notices/licenses when redistributing font
software and respect reserved-name conditions for modifications. Do not assume
font embedding makes the letter text OFL-licensed. No Phoenix-specific public
license file was found in this repository audit; choosing a license for a future
standalone release is an explicit owner decision, not part of this documentation
change. Credit to Letterhead is intentional even without bundled plugin code.

## Exploratory future scope

The surrounding integration package's [VISION.md](../VISION.md) owns possible
application/distribution ideas. They are not commitments and are not template
requirements. The dependency audit above records the current recommendation to
retain Letter Pro and the limits of a later independent implementation.
