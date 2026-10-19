#import "@local/phoenix-letter:0.1.0": phoenix-letter

// Omd2Typst scans this literal dictionary for its language picker.
#let _lang_strings = (
  "de": (page: "Seite", of: "von"),
  "en": (page: "Page", of: "of"),
)

#let template(fm: (:), doc) = {
  // Explicit allowlist. Never forward arbitrary frontmatter to the design.
  let lines(value) = if type(value) == str { value.split("\n").join(linebreak()) } else { value }
  phoenix-letter(
    sender: (
      name: fm.at("sender_name", default: none),
      address: fm.at("sender_address", default: none),
      extra: lines(fm.at("sender_extra", default: none)),
    ),
    recipient: lines(fm.at("recipient", default: none)),
    subject: fm.at("subject", default: none),
    date: fm.at("date", default: none),
    reference: fm.at("reference", default: none),
    language: fm.at("language", default: "de"),
    doc,
  )
}

#let callout(kind, title, body) = [#strong(title) #linebreak() #body]
