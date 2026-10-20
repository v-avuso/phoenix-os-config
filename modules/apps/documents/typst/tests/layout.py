"""Check observable layout in the synthetic Omd2Typst letter, using Poppler."""
import subprocess
import sys
import xml.etree.ElementTree as ET

pdf = sys.argv[1]
root = ET.fromstring(subprocess.check_output(['pdftotext', '-bbox-layout', pdf, '-']))
ns = {'x': 'http://www.w3.org/1999/xhtml'}
pages = []
for page in root.findall('.//x:page', ns):
    pages.append([(' '.join(w.text or '' for w in line), line.attrib)
                  for line in page.findall('.//x:line', ns)])


def find(needle, lines):
    return next((text, box) for text, box in lines if needle in text)


# Recipient belongs to the DIN B window and numbered address lines are not lists.
mm = 72 / 25.4
window = [(text, box) for text, box in pages[0]
          if 45 * mm <= float(box['yMin']) <= 90 * mm and float(box['xMin']) < 105 * mm]
address = [next(box for text, box in window if text.startswith(s))
           for s in ('Sozialgericht', '29. Kammer', 'Gerichtsstraße', '12345 Musterstadt')]
assert all(20 * mm <= float(b['xMin']) < float(b['xMax']) <= 105 * mm for b in address)
assert 62 * mm <= float(address[0]['yMin']) and float(address[-1]['yMax']) <= 90 * mm
steps = [float(b['yMin']) - float(a['yMin']) for a, b in zip(address, address[1:])]
assert max(steps) - min(steps) < 0.2, 'Numbered chamber line introduced list spacing'
reference = find('Aktenzeichen', pages[0])[1]
assert float(reference['xMin']) >= 120 * mm and float(reference['yMin']) < 65 * mm

# Greeting-to-first-paragraph baseline gap matches the reference's 23pt rhythm.
greeting = find('Sehr geehrte', pages[0])[1]
opening = find('hiermit übersende', pages[0])[1]
assert abs(float(opening['yMin']) - float(greeting['yMin']) - 23) < 0.2

# The conventional closing and plain sender-name signature stay together.
last = pages[-1]
closing = find('Mit freundlichen Grüßen', last)[1]
signature = find('Erika Beispiel', last)[1]
assert abs((float(signature['yMin']) - float(closing['yMin'])) / mm - 21.1) < 0.3
fonts = subprocess.check_output(['pdffonts', pdf], text=True)
assert 'TeXGyreHeros-Regular' in fonts and 'TeXGyreHeros-Bold' in fonts
assert all('yes' in line for line in fonts.splitlines()[2:] if line.strip())
print('PASS: window bounds, compact chamber line, right reference, paragraph rhythm, signing space, embedded Heros')
