#import "@preview/letter-pro:3.0.0": letter-simple

// Presentation only: no Obsidian metadata or private identity defaults.
#let phoenix-letter(
  sender: (:), recipient: none, subject: none, date: none,
  reference: none, language: "de", body,
) = {
  set text(lang: language, size: 11pt)
  letter-simple(
    format: "DIN-5008-B",
    font: "Source Sans Pro",
    sender: (
      name: sender.at("name", default: none),
      address: sender.at("address", default: none),
      extra: sender.at("extra", default: none),
    ),
    recipient: recipient,
    subject: subject,
    date: date,
    reference-signs: if reference == none { none } else { (([Aktenzeichen], [#reference]),) },
    folding-marks: true,
    hole-mark: true,
    page-numbering: (current, total) => [Seite #current von #total],
    {
      // Must be INSIDE letter-simple's body: upstream sets hyphenate: false.
      set text(lang: language, hyphenate: true)
      set par(justify: true, leading: 0.65em, spacing: 0.8em)
      set heading(numbering: none)
      show heading: set block(sticky: true, above: 1.2em, below: 0.5em)
      body
    },
  )
}
