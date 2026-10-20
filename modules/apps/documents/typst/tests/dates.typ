#import "@local/phoenix-letter:0.1.0": phoenix-letter, numeric-date
#assert.eq(numeric-date("2026-10-19"), "19.10.2026")
#assert.eq(numeric-date("19. Oktober 2026"), "19.10.2026")
#assert.eq(numeric-date("1.3.2026"), "01.03.2026")
#assert.eq(numeric-date("1. März 2026"), "01.03.2026")
#assert.eq(numeric-date(datetime(year: 2026, month: 10, day: 19)), "19.10.2026")
#assert.eq(numeric-date("Nach Vereinbarung"), "Nach Vereinbarung")
#show: phoenix-letter.with(
  sender: (name: "Erika Beispiel", address: "Musterstraße 12, 12345 Musterstadt"),
  subject: "Datumsformate",
  date: "2026-10-19",
  recipient: [Sozialgericht Musterstadt],
)
Sehr geehrte Damen und Herren,

Die Datumsanzeige bleibt unabhängig von der Eingabeschreibweise.
