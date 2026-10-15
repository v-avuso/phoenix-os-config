"""Fail closed when the packaged launcher no longer execs its allowed identity."""
import os
import subprocess
import sys
import tempfile
import time


def check(launcher, expected):
    with tempfile.TemporaryDirectory() as home:
        env = dict(os.environ, HOME=home, CODEX_HOME=home)
        process = subprocess.Popen(
            [launcher, "app-server"], stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=env, cwd=home,
        )
        observed = None
        try:
            deadline = time.monotonic() + 10
            while time.monotonic() < deadline and process.poll() is None:
                try:
                    observed = os.readlink(f"/proc/{process.pid}/exe")
                except FileNotFoundError:
                    continue
                if observed == expected:
                    # The app-server must stay alive with its input pipe open.
                    time.sleep(0.1)
                    if process.poll() is None and os.readlink(f"/proc/{process.pid}/exe") == expected:
                        return
                time.sleep(0.01)
            raise SystemExit(f"Codex kernel executable mismatch: expected {expected}, observed {observed}")
        finally:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
            process.stdin.close()


if __name__ == "__main__":
    check(*sys.argv[1:])
