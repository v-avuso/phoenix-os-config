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
return_line = next(box for text, box in window if text.startswith('Erika Beispiel,'))
assert 45 * mm <= float(return_line['yMin']) < 50 * mm, 'Return line must occupy the top 5mm row'
reference = find('Aktenzeichen', pages[0])[1]
assert float(reference['xMin']) >= 120 * mm and float(reference['yMin']) < 65 * mm
date_label = find('Datum', pages[0])[1]
assert abs(float(date_label['yMin']) - float(reference['yMin']) - 12.15) < 0.2

# Greeting-to-first-paragraph baseline gap matches the reference's 23pt rhythm.
greeting = find('Sehr geehrte', pages[0])[1]
opening = find('hiermit übersende', pages[0])[1]
assert abs(float(opening['yMin']) - float(greeting['yMin']) - 23) < 0.2

# Letterhead vector-export geometry: 14.5pt lines, 21.5pt paragraph
# boundaries and 20.925pt heading-to-body baselines. Poppler's Liberation
# Sans bounding boxes add a 1.820pt ascent difference for 12.5pt headings.
heading_index = next(i for i, (text, _) in enumerate(pages[0]) if text == 'Sachverhalt')
heading_box = pages[0][heading_index][1]
first_line = pages[0][heading_index + 1][1]
second_line = pages[0][heading_index + 2][1]
assert abs(float(second_line['yMin']) - float(first_line['yMin']) - 14.5) < 0.2
assert abs(float(first_line['yMin']) - float(heading_box['yMin']) - 22.745) < 0.2

section = next(i for i, (text, _) in enumerate(pages[0]) if text == 'Prüfung 1')
next_section = next(i for i, (text, _) in enumerate(pages[0]) if text == 'Prüfung 2')
starts = [i for i in range(section + 1, next_section)
          if pages[0][i][0].startswith('Die Sozialversicherungs')]
assert len(starts) >= 2, 'Fixture must exercise a paragraph boundary'
for i in starts[1:]:
    assert abs(float(pages[0][i][1]['yMin']) - float(pages[0][i - 1][1]['yMin']) - 21.5) < 0.2

# The conventional closing and plain sender-name signature stay together.
last = pages[-1]
closing_index = next(i for i, (text, _) in enumerate(last) if text == 'Mit freundlichen Grüßen')
closing = last[closing_index][1]
assert abs(float(closing['yMin']) - float(last[closing_index - 1][1]['yMin']) - 31.14) < 0.2
signature = find('Erika Beispiel', last)[1]
assert abs((float(signature['yMin']) - float(closing['yMin'])) / mm - 21.1) < 0.3
fonts = subprocess.check_output(['pdffonts', pdf], text=True)
assert 'LiberationSans' in fonts and 'LiberationSans-Bold' in fonts
assert all('yes' in line for line in fonts.splitlines()[2:] if line.strip())
print('PASS: top return row, window bounds, compact chamber line, reference/heading/line spacing, signing space, embedded Liberation Sans')
