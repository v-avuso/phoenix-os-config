"""Exercise native heading stickiness and widow/orphan control near page boundaries."""
from pathlib import Path
import subprocess
import tempfile
import xml.etree.ElementTree as ET

ns = {'x': 'http://www.w3.org/1999/xhtml'}
splits, two_line_starts = 0, 0
with tempfile.TemporaryDirectory(prefix='phoenix-pagination-') as directory:
    source, pdf = Path(directory)/'letter.typ', Path(directory)/'letter.pdf'
    # Vary natural preceding text and paragraph length, never insert page breaks.
    for filler in range(180, 421, 20):
        for length in (1, 40, 180):
            source.write_text('''#import "@local/phoenix-letter:0.1.0": phoenix-letter
#show: phoenix-letter.with(
 sender: (name: "Erika Beispiel", address: "Musterstraße 12, 12345 Musterstadt"),
 recipient: [Sozialgericht Musterstadt], subject: "Seitenumbruchprüfung")
''' + 'Fuellwort '*filler + '\n\n= Abschnittstest\n\n'
                + '#text(hyphenate: false)[' + 'Textwort '*length + ']\n\n'
                + 'Schlusswort.\n')
            subprocess.run(['typst', 'compile', str(source), str(pdf)], check=True)
            root = ET.fromstring(subprocess.check_output(['pdftotext', '-bbox-layout', str(pdf), '-']))
            pages = [[' '.join(w.text or '' for w in line) for line in page.findall('.//x:line', ns)]
                     for page in root.findall('.//x:page', ns)]
            heading_page = next(i for i, lines in enumerate(pages) if 'Abschnittstest' in lines)
            counts = [sum(line.startswith('Textwort') for line in lines) for lines in pages]
            first = next(i for i, count in enumerate(counts) if count)
            assert heading_page == first, 'Heading stranded without paragraph text'
            occupied = [count for count in counts if count]
            if len(occupied) > 1:
                splits += 1
                assert min(occupied) >= 2, 'Single-line widow or orphan'
                two_line_starts += counts[first] == 2
assert splits and two_line_starts, 'Fixture must exercise splitting and the accepted two-line minimum'
print(f'PASS: 39 pagination variants, {splits} split paragraphs, {two_line_starts} two-line starts; no stranded headings or single-line fragments')
