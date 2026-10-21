"""Focused PDF/UA regression checks; not a full accessibility certification.

Requires pypdf plus Poppler. The caller must first compile with --pdf-standard ua-1.
"""
import re
import os
import subprocess
import sys
import xml.etree.ElementTree as ET
from pypdf import PdfReader
from pypdf.generic import ContentStream, IndirectObject

pdf = sys.argv[1]
# veraPDF can return success for a completed run containing validation failures;
# inspect its report rather than relying on the process exit status alone.
report = subprocess.check_output([os.environ.get('VERAPDF', 'verapdf'),
                                  '--format', 'xml', '--flavour', 'ua1', pdf])
reports = [node for node in ET.fromstring(report).iter()
           if node.tag.split('}')[-1] == 'validationReport']
assert reports and all(node.get('isCompliant') == 'true' for node in reports), report.decode()
reader = PdfReader(pdf)
assert len(reader.pages) >= 3
catalog = reader.trailer['/Root']
assert catalog['/Lang'] == 'de'
assert catalog['/MarkInfo']['/Marked']
assert reader.metadata.title == 'Stellungnahme zum gerichtlichen Verfahren'
assert reader.metadata.author == 'Erika Beispiel'
xmp = ET.fromstring(catalog['/Metadata'].get_data())
assert xmp.findtext('.//{http://www.aiim.org/pdfua/ns/id/}part') == '1'

roles = []
def visit(node):
    if isinstance(node, list):
        for child in node:
            visit(child)
    elif isinstance(node, IndirectObject):
        visit(node.get_object())
    elif isinstance(node, dict):
        if '/S' in node:
            roles.append(str(node['/S']))
        if '/K' in node:
            visit(node['/K'])
visit(catalog['/StructTreeRoot'])
headings = [int(role[2:]) for role in roles if re.fullmatch('/H[1-6]', role)]
assert headings and headings[0] == 1 and 2 in headings
assert all(b <= a+1 for a, b in zip(headings, headings[1:]))
assert '/Link' in roles
structure = subprocess.check_output(['pdfinfo', '-struct-text', pdf], text=True, errors='replace')
# Check the main reading sequence independently of visual positioning.
needles = ['Erika Beispiel', 'Sozialgericht Musterstadt', 'Stellungnahme zum gerichtlichen Verfahren',
           'Sehr geehrte Damen und Herren', 'Sachverhalt', 'Rechtlicher Rahmen', 'Mit freundlichen Grüßen']
positions = [structure.index(needle) for needle in needles]
assert positions == sorted(positions), 'Unexpected structural reading order'
assert 'Seite ' not in structure, 'Repeated pagination should remain an artifact'

# First-sheet fold/hole marks and the return-address rule must be decorative.
stack, widths, width, decorative_strokes = [], [], 1, 0
for operands, operator in ContentStream(reader.pages[0].get_contents(), reader).operations:
    if operator == b'q':
        widths.append(width)
    elif operator == b'Q':
        width = widths.pop()
    elif operator == b'w':
        width = float(operands[0])
    elif operator in (b'BMC', b'BDC'):
        stack.append(str(operands[0]) == '/Artifact')
    elif operator == b'EMC':
        stack.pop()
    elif operator in (b'S', b's') and width == 0.25 and any(stack):
        decorative_strokes += 1
assert decorative_strokes == 4, 'Expected three handling marks and one return rule as artifacts'

# The wrapped link retains visible dotted strokes with round caps.
operations = ContentStream(reader.pages[0].get_contents(), reader).operations
assert any(operator == b'd' and list(operands[0]) == [0.6, 2]
           for operands, operator in operations)
assert any(operator == b'J' and operands == [1] for operands, operator in operations)
return_rows = []
reader.pages[0].extract_text(visitor_text=lambda text, cm, tm, font, size:
    return_rows.append((text, size)) if 'Erika Beispiel ·' in text else None)
assert return_rows and all(size == 8 for _, size in return_rows)

uris, wrapped_links = [], []
for page in reader.pages:
    for reference in page.get('/Annots', []):
        action = reference.get_object().get('/A', {})
        if action.get('/S') == '/URI':
            uris.append(action['/URI'])
            if len(reference.get_object().get('/QuadPoints', [])) >= 16:
                wrapped_links.append(action['/URI'])
legal_url = 'https://www.gesetze-im-internet.de/sgb_2/__12.html'
assert legal_url in wrapped_links, 'Long link should wrap with clickable quadrilaterals'
assert all('chatgpt' not in uri.lower() for uri in uris)

# Inspect decoded objects/streams as well as rendered text and Info/XMP metadata.
for generation, entries in reader.xref.items():
    for number in entries:
        if not number:
            continue
        obj = reader.get_object(IndirectObject(number, generation, reader))
        payload = str(obj).encode() + (obj.get_data() if hasattr(obj, 'get_data') else b'')
        assert b'PRIVATE_SENTINEL' not in payload and b'chatgpt.com' not in payload.lower()
text = '\n'.join(page.extract_text() for page in reader.pages)
assert 'PRIVATE_SENTINEL' not in text
fonts = subprocess.check_output(['pdffonts', pdf], text=True)
for face in ('LiberationSans ', 'LiberationSans-Bold '):
    assert any(face in line and line.split()[4:7] == ['yes', 'yes', 'yes']
               for line in fonts.splitlines()[2:]), f'Expected embedded subset: {face}'
print('PASS: veraPDF UA-1 validation, German language/title, heading hierarchy, reading sequence, artifacts, wrapped links, font subsets and metadata exclusion')
