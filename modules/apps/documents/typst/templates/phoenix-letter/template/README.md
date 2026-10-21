# Phoenix Letter template

## Intentions

Professional German formal letters with A4/DIN 5008-B geometry, Liberation Sans,
justified text, automatic hyphenation, window addresses and discreet pagination.
Keep styling reusable independently of Obsidian and private identity defaults.

[DOCU.md](DOCU.md) records the design history, measured rhythm, font comparisons,
accessibility choices, provenance and dependency audit. The [integration README](../README.md)
owns Markdown metadata, Obsidian export and deployment.

## Dependencies and parameters

Typst 0.14.2 was tested. Import `@preview/letter-pro:3.0.0` and make Liberation Sans
available to Typst (regular/bold are embedded subsets). Phoenix Nix/Home Manager
supplies both dependencies; elsewhere install/cache the upstream package first.
Standalone use has no Obsidian, Omd2Typst, Node or Python requirement.

| Parameter | Meaning |
| --- | --- |
| `sender` | Dictionary with nonblank `name`/`address`; optional `extra`. Address uses `, ` between header lines. |
| `recipient` | Required nonempty content or text. |
| `subject` | Optional subject and PDF title; nonempty title required for strict PDF/UA-1. |
| `date` | Optional date; German written/numeric and ISO dates normalize to DD.MM.YYYY; custom text remains unchanged. No date is invented. |
| `reference` | Optional case/reference value in the right information block. |
| `language` | Defaults to `"de"`; drives language/hyphenation. Footer/reference labels stay German. |
| `signature` | Closing-name override; see below. |
| `link-underline` | Native stroke dash style, defaults to `"dotted"`; `"solid"` is available. |
| `body` | Letter content passed through the show rule. Greeting and closing stay in the content. |

The small return row is measured against its 80mm field; excessive width fails
instead of clipping. Keep recipient lines short and within the nominal window.
The template does not enforce recipient overflow on every compile. No complete
DIN certification or physical-envelope guarantee is claimed.

## Standalone Typst

After Phoenix installation, compile the example:

```sh
typst compile modules/apps/documents/typst/templates/phoenix-letter/template/tests/standalone.typ /tmp/letter.pdf
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

`signature` defaults to `sender.name`; an empty string also uses that default,
while whitespace suppresses it and other text overrides it. A plain body paragraph
exactly matching `sender.name` is removed to avoid duplicate closing names. Set
`link-underline: "solid"` to use conventional solid link underlines; the default is
`"dotted"`. Body text/destinations stay unchanged. Repository-relative imports also
work when upstream is available; a local-package installation is not mandatory.

## Validation

Compile the standalone/date fixtures in `tests/` and run `python3 tests/pagination.py`
with Typst and Poppler available. The pagination fixture varies preceding text and
paragraph lengths, retaining native sticky headings and widow/orphan protection.
`tests/window.py PDF "expected line" ...` checks every supplied address line for
presence, wrapping and containment in the nominal DIN B field. Include the return
row and all recipient lines, including any suspected overflow.

For opt-in strict output:

```sh
typst compile --pdf-standard ua-1 letter.typ letter.pdf
verapdf --flavour ua1 letter.pdf
```

The subject must provide a title and standalone semantic headings must begin at
H1 without skipped deeper levels. Decorative rules/marks use `pdf.artifact`; links
remain clickable/tagged. Automated validation does not prove every accessibility
requirement or screen-reader usability. Inspect output visually too. The surrounding
[integration tests](../tests/run.py) additionally validate real Markdown conversion,
metadata privacy and independent veraPDF compliance.

## Attribution and licenses

Imports four unchanged helpers from [Letter Pro 3.0.0](https://github.com/Sematre/typst-letter-pro)
(MIT), uses [Typst](https://github.com/typst/typst) (Apache-2.0), and embeds Liberation
Sans (OFL-1.1). [Letterhead](https://github.com/johannes-kaindl/obsidian-letterhead)
inspired the typography; its plugin implementation is not bundled. Read
[the provenance audit](DOCU.md#provenance-licensing-and-credit) before redistributing
upstream code/fonts or extracting a public package. This documentation assigns no
new Phoenix software license. The package remains dependent on Letter Pro; its
helpers have not been rewritten or vendored here.
