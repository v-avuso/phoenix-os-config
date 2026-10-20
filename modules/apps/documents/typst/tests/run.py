"""Run letter checks with disposable vaults; pass the installed plugin's main.js."""
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

tests = Path(__file__).resolve().parent
plugin = Path(sys.argv[1]).resolve()
assert plugin.is_file(), 'Pass the installed Omd2Typst main.js'
with tempfile.TemporaryDirectory(prefix='phoenix-letter-checks-') as directory:
    root = Path(directory)
    source = root/'adapters'
    shutil.copytree(tests.parent/'template-adapters/omd2typst', source)
    vault = root/'vault'
    target = vault/'3-misc/phoenix-typst/omd2typst'
    target.parent.mkdir(parents=True)
    target.symlink_to(source, target_is_directory=True)
    for fixture in ('standalone', 'dates'):
        subprocess.run(['typst', 'compile', '--pdf-standard', 'ua-1',
                        str(tests/f'{fixture}.typ'), str(root/f'{fixture}.pdf')], check=True)
    solid = root/'solid-link.typ'
    solid.write_text((tests/'standalone.typ').read_text().replace(
        '  sender:', '  link-underline: "solid",\n  sender:', 1)
        + '\n#link("https://www.gesetze-im-internet.de/sgb_2/__12.html")[Rechtliche Grundlage]\n')
    subprocess.run(['typst', 'compile', '--pdf-standard', 'ua-1',
                    str(solid), str(root/'solid-link.pdf')], check=True)
    subprocess.run(['node', str(tests/'omd2typst.cjs'), str(plugin), str(vault)], check=True)
    for script in ('pagination.py', 'deployment.py'):
        subprocess.run([sys.executable, str(tests/script)], check=True)
