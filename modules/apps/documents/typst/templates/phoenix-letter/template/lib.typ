#import "@preview/letter-pro:3.0.0": letter-generic, header-simple, address-tribox, recipient-box

// Preserve the supplied date, normalizing recognised German/ISO dates only.
#let numeric-date(value) = {
  if type(value) == datetime { return value.display("[day].[month].[year]") }
  if type(value) != str { return value }
  let format(year, month, day) = datetime(year: int(year), month: int(month), day: int(day)).display("[day].[month].[year]")
  let iso = value.match(regex("^([0-9]{4})-([0-9]{2})-([0-9]{2})$"))
  if iso != none { return format(..iso.captures) }
  let digits = value.match(regex("^([0-9]{1,2})\\.([0-9]{1,2})\\.([0-9]{4})$"))
  if digits != none {
    let (day, month, year) = digits.captures
    return format(year, month, day)
  }
  let written = value.match(regex("^([0-9]{1,2})\\.\\s+([^ ]+)\\s+([0-9]{4})$"))
  if written != none {
    let (day, month, year) = written.captures
    let months = ("januar", "februar", "märz", "april", "mai", "juni", "juli", "august", "september", "oktober", "november", "dezember")
    let index = months.position(m => m == lower(month))
    if index != none { return format(year, index + 1, day) }
  }
  value
}

// Presentation only: no Obsidian metadata or private identity defaults.
#let phoenix-letter(
  sender: (:), recipient: none, subject: none, date: none,
  reference: none, language: "de", signature: none,
  link-underline: "dotted", body,
) = {
  let muted = rgb("#666666")
  // Lightest 8-bit neutral gray meeting 4.5:1 against white (4.542:1).
  let secondary = rgb("#767676")
  let name = sender.at("name", default: none)
  let address = sender.at("address", default: none)
  for (field, value) in (("sender_name", name), ("sender_address", address)) {
    assert(type(value) == str and value.trim() != "",
      message: "Phoenix letter: " + field + " fehlt. Absender im YAML ergänzen; in Obsidian: Omd2Typst: Insert frontmatter.")
  }
  assert(recipient != none and recipient != [] and
    (type(recipient) != str or recipient.trim() != ""),
    message: "Phoenix letter: recipient fehlt. Empfänger im YAML ergänzen.")
  assert(signature == none or type(signature) == str,
    message: "Phoenix letter: signature muss Text sein.")
  let closing-name = if signature == none or signature == "" { name } else { signature.trim() }
  set document(title: if subject == none { "" } else { subject }, author: name)
  set text(font: "Liberation Sans", lang: language, size: 10pt, fill: rgb("#1a1a1a"))
  // First-sheet handling aids. Edge-to-edge printing remains printer-dependent.
  set page(foreground: context {
    if here().page() == 1 {
      for (position, length) in ((105mm, 5mm), (148.5mm, 8mm), (210mm, 5mm)) {
        place(top + left, dy: position, pdf.artifact(line(length: length, stroke: 0.25pt + black)))
      }
    }
  })
  letter-generic(
    format: "DIN-5008-B",
    margin: (top: 25mm),
    header: pad(left: 25mm, right: 20mm, top: 25mm, bottom: 5mm,
      align(bottom + right, header-simple(name,
        if address == none { none } else { address.split(", ").join(linebreak()) },
        extra: sender.at("extra", default: none),
      )),
    ),
    address-box: address-tribox({
      let parts = (name,) + address.split(", ")
      if parts.len() > 0 {
        pad(left: 5mm, top: 0.5mm, stack(dir: ttb, spacing: 1.2mm,
          context {
            let row = text(size: 8pt, fill: muted, top-edge: 0.75em, bottom-edge: -0.25em, parts.join(" · "))
            assert(measure(row).width <= 80mm,
              message: "Phoenix letter: Rücksendeadresse ist zu lang für das 80-mm-Feld. Absenderangaben kürzen.")
            row
          },
          pdf.artifact(line(length: 80mm, stroke: 0.25pt + black)),
        ))
      }
    }, [], recipient-box(recipient)),
    information-box: pad(right: 10mm, {
      set text(size: 9pt, top-edge: 0.75em, bottom-edge: -0.25em)
      set par(justify: false, leading: 0.45em, spacing: 0pt)
      let rows = ()
      if reference != none {
        rows += (text(fill: muted)[Aktenzeichen], align(right, reference))
      }
      if date != none {
        rows += (text(fill: muted)[Datum], align(right, numeric-date(date)))
      }
      grid(columns: (auto, 1fr), column-gutter: 3mm, row-gutter: 3.15pt, ..rows)
    }),
    folding-marks: false,
    hole-mark: false,
    page-numbering: (current, total) => text(size: 9pt, fill: secondary)[Seite #current von #total],
    {
      if subject != none {
        pad(right: 10%, strong(subject))
        v(0.65em)
      }
      // Explicit text edges preserve 14.5pt line and 21.5pt paragraph baselines.
      set text(lang: language, hyphenate: true, top-edge: 0.75em, bottom-edge: -0.25em)
      set par(justify: true, leading: 4.5pt, spacing: 11.5pt)
      // Retain the original link element so PDF annotations and tags survive.
      show link: element => underline(
        stroke: (paint: rgb("#1a1a1a"), thickness: 0.6pt, dash: link-underline, cap: "round"),
        offset: 1.8pt, element,
      )
      set heading(numbering: none)
      show heading: set text(size: 12.5pt)
      show heading: set block(sticky: true, above: 16.5pt, below: 10.3pt)
      // Content stays in Markdown. Only whole, plain paragraphs are styled;
      // mentions of the sender within ordinary text are unaffected.
      show par: paragraph => {
        if paragraph.body == text(name) {
          []
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
      if closing-name != "" {
        block(above: 17.6mm, below: 0pt, breakable: false, box(closing-name))
      }
    },
  )
}
