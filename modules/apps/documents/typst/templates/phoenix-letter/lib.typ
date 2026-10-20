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
    // Helvetica-compatible, already installed by Phoenix; embedded by Typst.
    font: "TeX Gyre Heros",
    sender: (
      name: name,
      address: sender.at("address", default: none),
      extra: sender.at("extra", default: none),
    ),
    recipient: recipient,
    subject: subject,
    information-box: pad(right: 10mm, {
      set text(size: 9pt)
      set par(justify: false, leading: 0.45em, spacing: 0pt)
      let rows = ()
      if reference != none {
        rows += (text(fill: muted)[Aktenzeichen], align(right, reference))
      }
      if date != none {
        rows += (text(fill: muted)[Datum], align(right, date))
      }
      grid(columns: (auto, 1fr), column-gutter: 3mm, row-gutter: 1.2mm, ..rows)
    }),
    folding-marks: true,
    hole-mark: true,
    page-numbering: (current, total) => text(size: 9pt, fill: muted)[Seite #current von #total],
    {
      // Must be INSIDE letter-simple's body: upstream sets hyphenate: false.
      // Fixed text edges give 14pt baselines and 23pt paragraph baselines,
      // matching the reference letter's rhythm without Markdown spacers.
      set text(lang: language, hyphenate: true, top-edge: 0.75em, bottom-edge: -0.25em)
      set par(justify: true, leading: 4pt, spacing: 13pt)
      set heading(numbering: none)
      show heading: set text(size: 12.5pt)
      show heading: set block(sticky: true, above: 6mm, below: 2mm)
      // Content stays in Markdown. Only whole, plain paragraphs are styled;
      // mentions of the sender within ordinary text are unaffected.
      show par: paragraph => {
        if name != none and paragraph.body == text(name) {
          block(above: 17.6mm, below: 0pt, breakable: false, paragraph)
        } else if paragraph.body == [Mit freundlichen Grüßen] {
          block(above: 6mm, below: 0pt, sticky: true, paragraph)
        } else {
          paragraph
        }
      }
      v(1.6mm)
      body
    },
  )
}
