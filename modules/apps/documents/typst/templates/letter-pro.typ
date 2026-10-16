#import "@preview/letter-pro:3.0.0": letter-simple

#let _lang_strings = (
  "en": (toc: "Table of Contents", appendix: "Appendix", figures: "List of Figures", summary: "Summary", version: "Version", status: "Status", date: "Date", author: "Author", page: "Page", of: "of", fig_nr: "Figure", fig_desc: "Description"),
  "de": (toc: "Inhaltsverzeichnis", appendix: "Anhang", figures: "Abbildungsverzeichnis", summary: "Zusammenfassung", version: "Version", status: "Status", date: "Datum", author: "Autor", page: "Seite", of: "von", fig_nr: "Abbildung", fig_desc: "Beschreibung"),
)

#let template(fm: (:), doc) = {
  let lang = fm.at("language", default: "en")
  let subject = fm.at("subject", default: fm.at("title", default: none))
  set text(lang: lang)
  show: letter-simple.with(subject: subject)
  doc
}

#let callout(kind, title, body) = [#strong(title) #linebreak() #body]
