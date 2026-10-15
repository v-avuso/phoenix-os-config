"""Test-only invocation budget; not a hostile-reviewer security boundary."""
import fcntl
import os
from pathlib import Path
import sys


def consume(path):
    with path.open('r+') as token:
        fcntl.flock(token, fcntl.LOCK_EX)
        if token.read() != '0':
            raise ValueError('trial-call-limit')
        token.seek(0); token.write('1'); token.truncate(); token.flush(); os.fsync(token.fileno())


def main(mode, executable, arguments):
    if mode == 'bwrap':
        # Production adapter binds .../requests/request-*/review/work at /work.
        index = arguments.index('/work')
        work = Path(arguments[index - 1]).resolve(strict=True)
        root = work.parents[3]
        if (work.name != 'work' or work.parent.name != 'review' or work.parents[2].name != 'requests'
                or not str(root).startswith('/var/tmp/phoenix-checkpoint-trial-') or root.stat().st_uid != 0):
            raise ValueError('trial-work-binding-invalid')
        arguments = ['--bind', str(root / 'budget'), '/trial-gate', *arguments]
    elif mode == 'codex':
        consume(Path('/trial-gate/used'))
    else:
        raise ValueError('trial-mode-invalid')
    os.execv(executable, [executable, *arguments])


if __name__ == '__main__':
    try:
        main(sys.argv[1], sys.argv[2], sys.argv[3:])
    except Exception:
        print('trial invocation gate refused', file=sys.stderr)
        raise SystemExit(125)
