#import "@local/phoenix-letter:0.1.0": phoenix-letter

// Omd2Typst scans this literal dictionary for its language picker.
#let _lang_strings = (
  "de": (page: "Seite", of: "von"),
  "en": (page: "Page", of: "of"),
)

#let template(fm: (:), doc) = {
  // Explicit allowlist. Never forward arbitrary frontmatter to the design.
  let lines(value) = {
    // The converter treats a literal address line such as "29. Kammer" as
    // an enum. Render its number as address text, without list block spacing.
    show enum: list => list.children.enumerate().map(((index, item)) => {
      let number = item.number
      if number == none { number = list.start + index }
      [#number. #item.body]
    }).join()
    if type(value) == str { value.split("\n").join(linebreak()) } else { value }
  }
  let recipient = fm.at("recipient", default: none)
  assert(recipient != none and recipient != [] and
    (type(recipient) != str or recipient.trim() != ""),
    message: "Phoenix letter: recipient fehlt. Empfänger im YAML ergänzen.")
  phoenix-letter(
    sender: (
      name: fm.at("sender_name", default: none),
      address: fm.at("sender_address", default: none),
      extra: lines(fm.at("sender_extra", default: none)),
    ),
    recipient: lines(recipient),
    subject: fm.at("subject", default: none),
    date: fm.at("date", default: none),
    reference: fm.at("reference", default: none),
    signature: fm.at("signature", default: none),
    language: fm.at("language", default: "de"),
    doc,
  )
}

#let callout(kind, title, body) = [#strong(title) #linebreak() #body]
