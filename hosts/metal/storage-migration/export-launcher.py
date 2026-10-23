#!/usr/bin/env python3
"""Export one portable launcher containing the complete reviewed Git source."""
import argparse
import base64
import gzip
import hashlib
import io
import json
from pathlib import Path
import subprocess
import tarfile


def export(repo, destination):
    commit = subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()
    source = subprocess.check_output(["git", "-C", str(repo), "archive", "--format=tar", "--prefix=source/", commit])
    with tarfile.open(fileobj=io.BytesIO(source)) as archive:
        lock = json.load(archive.extractfile("source/flake.lock"))
        revision = lock["nodes"][lock["nodes"]["root"]["inputs"]["nixpkgs"]]["locked"]["rev"]
    output = io.BytesIO()
    with tarfile.open(fileobj=output, mode="w") as archive:
        with tarfile.open(fileobj=io.BytesIO(source)) as original:
            for member in original:
                archive.addfile(member, original.extractfile(member) if member.isfile() else None)
        release = json.dumps({"commit": commit}).encode()
        member = tarfile.TarInfo("release.json")
        member.size = len(release)
        member.mode = 0o600
        archive.addfile(member, io.BytesIO(release))
    payload = gzip.compress(output.getvalue(), mtime=0)
    digest = hashlib.sha256(payload).hexdigest()
    header = f'''#!/usr/bin/env bash
set -euo pipefail
if [[ "${{1:-}}" == --help ]]; then
  echo 'Usage: sudo bash phoenix-migrate [--network] [--bluetooth]'
  echo 'Boot the NixOS live USB in UEFI mode with network. Prompts approve restore and installation.'
  exit 0
fi
[[ $EUID == 0 ]] || {{ echo 'Run: sudo bash phoenix-migrate' >&2; exit 1; }}
[[ -f /etc/NIXOS && -d /sys/firmware/efi/efivars ]] || {{ echo 'Boot a NixOS live USB in UEFI mode.' >&2; exit 1; }}
case "$(findmnt -nro FSTYPE --target /)" in tmpfs|overlay) ;; *) echo 'Refusing an installed system.' >&2; exit 1;; esac
[[ $(wc -l < /proc/swaps) == 1 ]] || {{ echo 'Swap is active; disable it in the live USB before retrying.' >&2; exit 1; }}
driver_command='exec python3 -B "$PHOENIX_MIGRATION_DRIVER"'
for argument in "$@"; do
  case "$argument" in
    --network|--bluetooth) driver_command+=" $argument" ;;
    *) echo 'Unknown option; use --help.' >&2; exit 1 ;;
  esac
done
work=$(mktemp -d /run/phoenix-migration.XXXXXXXX)
chmod 755 "$work"
trap 'echo "NO-GO: launcher failed. Extracted runbook: $work/source/hosts/metal/storage-migration/README.md" >&2' ERR
sed '1,/^__PHOENIX_PAYLOAD__$/d' "$0" | base64 --decode > "$work/payload.gz"
echo '{digest}  '"$work/payload.gz" | sha256sum --check --status
tar -xzf "$work/payload.gz" -C "$work"
echo 'Phoenix migration bundle: {commit}'
echo 'Preparing tools from pinned nixpkgs; network is required. No migration has started.'
export PHOENIX_MIGRATION_DRIVER="$work/source/hosts/metal/storage-migration/migrate.py"
nix-shell -I nixpkgs=https://github.com/NixOS/nixpkgs/archive/{revision}.tar.gz \\
  -p python3 openssl rsync cryptsetup btrfs-progs util-linux git acl nix nixos-install nixos-enter \\
  --run "$driver_command"
exit 0
__PHOENIX_PAYLOAD__
'''
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(header + base64.encodebytes(payload).decode())
    destination.chmod(0o755)
    print(f"{destination}\nCommit: {commit}\nSHA256: {hashlib.sha256(destination.read_bytes()).hexdigest()}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    export(Path(__file__).resolve().parents[3], args.destination)
