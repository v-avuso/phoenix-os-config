"""Pinned Community menu seam; preserve existing quit/window implementations."""
from pathlib import Path
import sys


def patch(directory):
    files = list(Path(directory).glob('main-*.js'))
    matches = [(path, path.read_text()) for path in files if '{...j(`newWindow`),click:async' in path.read_text()]
    if len(matches) != 1:
        raise ValueError('Expected one pinned new-window menu owner')
    path, source = matches[0]
    needle = '{...j(`newWindow`),click:async'
    if source.count(needle) != 1:
        raise ValueError('Expected one pinned new-window descriptor')
    for evidence in ('codexLinuxQuitPromptPending', 'canQuitWithoutPrompt()', 'ose()',
                     'desktop.quitConfirmation.cancel', 'n.markQuitApproved();g.app.quit()',
                     'g.app.on(`activate`', 'r.showLastActivePrimaryWindow()'):
        if evidence not in source:
            raise ValueError('Pinned graceful quit/activation seam changed')
    link = 'w(e=>{let t=Rd(e),n=f.r(t);if(We.deepLinks.queueProcessArgs(e)){n&&Je();return}if(n){Je();return}Je({channel:`shortcut`,source:`shortcut`})})'
    if source.count(link) != 1:
        raise ValueError('Expected one pinned second-instance callback')
    # Retain the exact callback registered upstream; add only fixed typed-link routing.
    source = source.replace(link, 'w((e=>{g.app.on(`phoenix-shared-open-link`,t=>e([process.execPath,t]));return e;})(' + link[2:-1] + '))')
    source = source.replace(needle, '{...j(`newWindow`),id:`phoenix-shared-new-window`,click:async')
    path.write_text(source)


if __name__ == '__main__':
    patch(sys.argv[1])
