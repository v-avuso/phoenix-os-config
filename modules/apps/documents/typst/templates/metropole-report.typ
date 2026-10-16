#import "@preview/metropole-report:0.1.0": metropole

#let _lang_strings = (
  "en": (toc: "Table of Contents", appendix: "Appendix", figures: "List of Figures", summary: "Summary", version: "Version", status: "Status", date: "Date", author: "Author", page: "Page", of: "of", fig_nr: "Figure", fig_desc: "Description"),
  "de": (toc: "Inhaltsverzeichnis", appendix: "Anhang", figures: "Abbildungsverzeichnis", summary: "Zusammenfassung", version: "Version", status: "Status", date: "Datum", author: "Autor", page: "Seite", of: "von", fig_nr: "Abbildung", fig_desc: "Beschreibung"),
)

#let template(fm: (:), doc) = {
  let lang = fm.at("language", default: "en")
  set text(lang: lang)
  show: metropole.with(
    title: fm.at("title", default: none),
    subtitle: fm.at("subtitle", default: none),
    author: fm.at("author", default: none),
    language: lang,
  )
  doc
}

#let callout(kind, title, body) = [#strong(title) #linebreak() #body]
