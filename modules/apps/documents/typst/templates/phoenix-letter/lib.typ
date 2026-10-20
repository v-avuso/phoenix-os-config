#import "@preview/letter-pro:3.0.0": letter-simple

// Presentation only: no Obsidian metadata or private identity defaults.
#let phoenix-letter(
  sender: (:), recipient: none, subject: none, date: none,
  reference: none, language: "de", body,
) = {
  let muted = rgb("#666666")
  let name = sender.at("name", default: none)
  set text(lang: language, size: 10pt, fill: rgb("#1a1a1a"))
  letter-simple(
    format: "DIN-5008-B",
    margin: (top: 25mm),
    // Matches Obsidian PDF.js's Helvetica substitute family; embed it.
    font: "Liberation Sans",
    sender: (
      name: name,
      address: sender.at("address", default: none),
      extra: sender.at("extra", default: none),
    ),
    // An empty annotations area selects upstream's three-row address box.
    // Without it, letter-simple bottom-aligns the return line near 57mm.
    annotations: [],
    recipient: recipient,
    subject: subject,
    information-box: pad(right: 10mm, {
      set text(size: 9pt, top-edge: 0.75em, bottom-edge: -0.25em)
      set par(justify: false, leading: 0.45em, spacing: 0pt)
      let rows = ()
      if reference != none {
        rows += (text(fill: muted)[Aktenzeichen], align(right, reference))
      }
      if date != none {
        rows += (text(fill: muted)[Datum], align(right, date))
      }
      grid(columns: (auto, 1fr), column-gutter: 3mm, row-gutter: 3.15pt, ..rows)
    }),
    folding-marks: true,
    hole-mark: true,
    page-numbering: (current, total) => text(size: 9pt, fill: muted)[Seite #current von #total],
    {
      // Must be INSIDE letter-simple's body: upstream sets hyphenate: false.
      // Letterhead's vector exporter: 10pt × 1.45 = 14.5pt line step;
      // +7pt after paragraphs = 21.5pt step across a paragraph boundary.
      // Explicit text edges make those baseline distances font-independent.
      set text(lang: language, hyphenate: true, top-edge: 0.75em, bottom-edge: -0.25em)
      set par(justify: true, leading: 4.5pt, spacing: 11.5pt)
      set heading(numbering: none)
      show heading: set text(size: 12.5pt)
      show heading: set block(sticky: true, above: 16.5pt, below: 10.3pt)
      // Content stays in Markdown. Only whole, plain paragraphs are styled;
      // mentions of the sender within ordinary text are unaffected.
      show par: paragraph => {
        if name != none and paragraph.body == text(name) {
          block(above: 17.6mm, below: 0pt, breakable: false, paragraph)
        } else if paragraph.body == [Sehr geehrte Damen und Herren,] {
          block(above: 13pt, below: 13pt, paragraph)
        } else if paragraph.body == [Mit freundlichen Grüßen] {
          block(above: 21.14pt, below: 0pt, sticky: true, paragraph)
        } else {
          paragraph
        }
      }
      v(1.6mm)
      body
    },
  )
}
