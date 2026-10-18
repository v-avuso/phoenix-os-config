"""Tag the unique upstream new-window action; leave lifecycle callbacks intact."""
from pathlib import Path
import re
import sys

# Capture the minified translation function rather than pinning its generated
# name. Only this exact semantic descriptor is modified; ambiguity fails closed.
MENU = re.compile(r"\{\.\.\.[A-Za-z_$][A-Za-z0-9_$]*\(`newWindow`\),click:async")


def patch(directory):
    matches = []
    for path in Path(directory).glob('main-*.js'):
        source = path.read_text()
        matches.extend((path, source, match) for match in MENU.finditer(source))
    if len(matches) != 1:
        raise ValueError('Expected one upstream new-window menu descriptor')
    path, source, match = matches[0]
    if 'phoenix-shared-new-window' in source:
        raise ValueError('Shared new-window menu already tagged')
    # These semantic markers establish that the upstream graceful-quit and
    # activation owners are still present; do not depend on minifier names.
    for evidence in ('codexLinuxQuitPromptPending', 'canQuitWithoutPrompt()',
                     'desktop.quitConfirmation.cancel', '.markQuitApproved()',
                     '.app.on(`activate`', '.showLastActivePrimaryWindow()'):
        if evidence not in source:
            raise ValueError('Upstream graceful quit/activation seam changed')
    descriptor = match.group()
    replacement = descriptor.replace(',click:', ',id:`phoenix-shared-new-window`,click:')
    path.write_text(source[:match.start()] + replacement + source[match.end():])


if __name__ == '__main__':
    patch(sys.argv[1])
