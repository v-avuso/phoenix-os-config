"""Check every supplied address line against the nominal DIN B address field."""
import subprocess
import sys
import xml.etree.ElementTree as ET

pdf, *expected = sys.argv[1:]
assert expected, 'Supply expected address lines, including any overflow lines'
root = ET.fromstring(subprocess.check_output(['pdftotext', '-bbox-layout', pdf, '-']))
ns = {'x': 'http://www.w3.org/1999/xhtml'}
page = root.find('.//x:page', ns)
lines = [(' '.join(w.text or '' for w in line), line.attrib)
         for line in page.findall('.//x:line', ns)]
mm = 72 / 25.4
for text in expected:
    matches = [box for value, box in lines if value == text]
    assert len(matches) == 1, f'Address line missing, duplicated or wrapped: {text}'
    box = matches[0]
    assert (20*mm <= float(box['xMin']) <= float(box['xMax']) <= 105*mm
            and 45*mm <= float(box['yMin']) <= float(box['yMax']) <= 90*mm), \
        f'Address line outside nominal window: {text}'
print(f'PASS: all {len(expected)} address lines contained in nominal DIN B window')
