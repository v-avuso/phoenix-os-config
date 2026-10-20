#import "@local/phoenix-letter:0.1.0": phoenix-letter

// Omd2Typst scans this literal dictionary for its language picker.
#let _lang_strings = (
  "de": (page: "Seite", of: "von"),
  "en": (page: "Page", of: "of"),
)

#let template(fm: (:), doc) = {
  // Explicit allowlist. Never forward arbitrary frontmatter to the design.
  let lines(value) = {
    // Rebuild numbered address items as text before list realization/tagging.
    if type(value) == str { return value.split("\n").join(linebreak()) }
    if type(value) != content { return value }
    if value.func() == enum.item { return [#value.number. #lines(value.body)] }
    if value.has("children") { return value.children.map(lines).join() }
    value
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
    context {
      // Notes often use ## for their first section. Preserve relative hierarchy.
      let depths = query(heading).map(h => h.depth)
      let base = if depths.len() == 0 { 1 } else { calc.min(..depths) }
      show heading.where(depth: base + 0): set heading(level: 1)
      show heading.where(depth: base + 1): set heading(level: 2)
      show heading.where(depth: base + 2): set heading(level: 3)
      show heading.where(depth: base + 3): set heading(level: 4)
      show heading.where(depth: base + 4): set heading(level: 5)
      show heading.where(depth: base + 5): set heading(level: 6)
      doc
    },
  )
}

#let callout(kind, title, body) = [#strong(title) #linebreak() #body]
