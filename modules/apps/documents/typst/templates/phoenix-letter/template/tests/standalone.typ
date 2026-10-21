#import "@local/phoenix-letter:0.1.0": phoenix-letter
#show: phoenix-letter.with(
  sender: (name: "Erika Beispiel", address: "Musterstraße 12, 12345 Musterstadt"),
  recipient: [Sozialgericht Musterstadt\ Gerichtsstraße 1\ 12345 Musterstadt],
  subject: "Stellungnahme zum gerichtlichen Verfahren",
  date: "19. Oktober 2026",
  reference: "S 00 AS 123/26",
)
Sehr geehrte Damen und Herren,

= Sachverhalt
#for i in range(18) [
  Die Sozialversicherungsbeitragsberechnung und die Krankenversicherungsbeitragspflicht erfordern eine nachvollziehbare Verhältnismäßigkeitsprüfung. Die Verwaltungsverfahrensvorschriften gewährleisten eine vollständige Sachverhaltsaufklärung. Die Lebenshaltungskostenentwicklung bleibt zu berücksichtigen.

]
= Antrag
Ich bitte um Berücksichtigung meiner Stellungnahme.

Mit freundlichen Grüßen

Erika Beispiel
