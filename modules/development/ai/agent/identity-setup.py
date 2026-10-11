"""Offline-only narrow retained-gateway relocation and declared-workspace ACL setup."""
import json
import importlib.util
import errno
import hashlib
import shutil
import tempfile
import pwd
import grp
import os
from pathlib import Path
import stat
import subprocess
import sys
import uuid

STAGE = "configuration"
DIRECTORY = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC


def directory(path):
    """Walk from / using held descriptors; never follow an operator symlink."""
    fd = os.open("/", DIRECTORY)
    try:
        for part in Path(path).parts[1:]:
            nxt = os.open(part, DIRECTORY, dir_fd=fd)
            os.close(fd)
            fd = nxt
        return fd
    except BaseException:
        os.close(fd)
        raise



def history_file(path, uid, *, create=False):
    parent = directory(str(Path(path).parent))
    try:
        try:
            fd = os.open(Path(path).name, os.O_RDWR | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=parent)
        except FileNotFoundError:
            if not create:
                raise
            fd = os.open(Path(path).name, os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600, dir_fd=parent)
            os.fchown(fd, uid, -1)
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_uid != uid:
            os.close(fd)
            raise ValueError("history lock has unexpected type/ownership")
        return fd
    finally:
        os.close(parent)

def quiescent(uid):
    # This is a refusal check, not a logout/session-exclusion mechanism.
    for entry in Path("/proc").iterdir():
        if entry.name.isdecimal():
            try:
                if entry.stat().st_uid == uid:
                    raise ValueError("operator processes still exist; use an isolated offline maintenance window")
            except FileNotFoundError:
                pass



def allocated_ranges(path, config):
    parent = directory(str(Path(path).parent))
    try:
        fd = os.open(Path(path).name, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=parent)
        try:
            info = os.fstat(fd)
            if not stat.S_ISREG(info.st_mode) or info.st_uid != config.get("readyOwner", 0) or info.st_nlink != 1 or info.st_size > 1024 * 1024:
                raise ValueError("subordinate allocation file is not trusted")
            raw = os.read(fd, 1024 * 1024 + 1)
            if len(raw) > 1024 * 1024:
                raise ValueError("subordinate allocation file grew beyond bound")
            data = raw.decode()
        finally:
            os.close(fd)
    finally:
        os.close(parent)
    entries = []
    for line in data.splitlines():
        if not line or line.startswith("#"):
            continue
        name, start, count = line.split(":")
        start, count = int(start), int(count)
        if start < 0 or count <= 0:
            raise ValueError("invalid subordinate allocation")
        entries.append((name, start, count))
    return entries


def validate_allocations(config):
    account = pwd.getpwnam("phoenix-agent")
    group = grp.getgrnam("phoenix-agent")
    if account.pw_uid != config["uid"] or account.pw_gid != config["gid"] or group.gr_gid != config["gid"] or config["uid"] == config["operatorUid"]:
        raise ValueError("dedicated installed account differs from configuration")
    if any(entry.pw_uid == config["uid"] and entry.pw_name != "phoenix-agent" for entry in pwd.getpwall()) or any(entry.gr_gid == config["gid"] and entry.gr_name != "phoenix-agent" for entry in grp.getgrall()):
        raise ValueError("dedicated installed identity collides")
    for path in ("/etc/subuid", "/etc/subgid"):
        entries = allocated_ranges(path, config)
        assigned = False
        for name, start, count in entries:
            if name in ("phoenix-agent", str(config["uid"])):
                if (start, count) != (config["subordinateStart"], config["subordinateCount"]):
                    raise ValueError("dedicated subordinate allocation differs")
                assigned = True
            elif start < config["subordinateStart"] + config["subordinateCount"] and config["subordinateStart"] < start + count:
                raise ValueError("dedicated subordinate range collides")
        if not assigned:
            raise ValueError("dedicated subordinate allocation is absent")

def own_tree(fd, uid, gid, *, apply=True):
    info = os.fstat(fd)
    if not stat.S_ISDIR(info.st_mode):
        raise ValueError("gateway state is not a directory")
    if apply:
        os.fchown(fd, uid, gid)
        os.fchmod(fd, 0o700)
    os.lseek(fd, 0, os.SEEK_SET)
    for name in os.listdir(fd):
        info = os.stat(name, dir_fd=fd, follow_symlinks=False)
        if stat.S_ISDIR(info.st_mode):
            child = os.open(name, DIRECTORY, dir_fd=fd)
            try:
                own_tree(child, uid, gid, apply=apply)
            finally:
                os.close(child)
        elif stat.S_ISREG(info.st_mode) and info.st_nlink == 1:
            child = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=fd)
            try:
                opened = os.fstat(child)
                if (opened.st_dev, opened.st_ino) != (info.st_dev, info.st_ino):
                    raise ValueError("gateway state changed during relocation")
                if apply:
                    os.fchown(child, uid, gid)
                    os.fchmod(child, 0o600)
                    os.fsync(child)
            finally:
                os.close(child)
        else:
            raise ValueError("gateway state contains a link or special file; review offline")



def gateway_manifest(fd):
    """Pinned DB/KEK layout only; never print credential bytes or fingerprints."""
    files = {}
    directories = set()
    total = 0
    allowed = {"openshell.db", "openshell.db-wal", "openshell.db-shm", "credentials/key-encryption-key.bin"}
    def visit(current, prefix=""):
        nonlocal total
        # External FD consumers can advance directory offsets (GNU cp does).
        os.lseek(current, 0, os.SEEK_SET)
        for name in os.listdir(current):
            relative = prefix + name
            info = os.stat(name, dir_fd=current, follow_symlinks=False)
            if stat.S_ISDIR(info.st_mode) and relative == "credentials":
                child = os.open(name, DIRECTORY, dir_fd=current)
                try:
                    directories.add(relative)
                    visit(child, relative + "/")
                finally:
                    os.close(child)
            elif stat.S_ISREG(info.st_mode) and info.st_nlink == 1 and relative in allowed:
                child = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=current)
                try:
                    opened = os.fstat(child)
                    if (opened.st_dev, opened.st_ino) != (info.st_dev, info.st_ino):
                        raise ValueError("gateway source changed")
                    total += opened.st_size
                    if total > 512 * 1024 * 1024:
                        raise ValueError("gateway state exceeds bounded migration size")
                    digest = hashlib.sha256()
                    consumed = 0
                    while chunk := os.read(child, 1024 * 1024):
                        consumed += len(chunk)
                        if consumed > opened.st_size:
                            raise ValueError("gateway source grew while hashing")
                        digest.update(chunk)
                    after = os.fstat(child)
                    if (opened.st_size, opened.st_mtime_ns, opened.st_ctime_ns) != (after.st_size, after.st_mtime_ns, after.st_ctime_ns):
                        raise ValueError("gateway source changed while hashing")
                    files[relative] = (opened.st_size, digest.hexdigest())
                finally:
                    os.close(child)
            else:
                raise ValueError("gateway tree is outside pinned regular-file layout")
    visit(fd)
    if not {"openshell.db", "credentials/key-encryption-key.bin"} <= files.keys():
        raise ValueError("gateway DB/encryption key missing")
    return (directories, files)


def copied_gateway(config, source, target_parent, expected):
    """GNU cp into root-protected staging; source remains intact on EXDEV."""
    global STAGE
    parent = directory(str(Path(config["state"]).parent))
    try:
        info = os.fstat(parent)
        if info.st_uid != config.get("readyOwner", 0) or info.st_mode & 0o022:
            raise ValueError("migration staging parent is not root protected")
        staging = tempfile.mkdtemp(prefix=".phoenix-agent-migration-", dir=str(Path(config["state"]).parent))
        staging_fd = directory(staging)
        try:
            os.mkdir("gateway", 0o700, dir_fd=staging_fd)
            copied = os.open("gateway", DIRECTORY, dir_fd=staging_fd)
            try:
                STAGE = "gateway-copy"
                subprocess.run([config["cp"], "--archive", "--no-dereference", "--reflink=auto",
                                f"/proc/self/fd/{source}/.", f"/proc/self/fd/{copied}/"],
                               pass_fds=(source, copied), check=True, timeout=300,
                               stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
                STAGE = "gateway-copy-verification"
                if gateway_manifest(source) != expected or gateway_manifest(copied) != expected:
                    raise ValueError("gateway copy/source verification failed")
                own_tree(copied, config["uid"], config["gid"])
                STAGE = "gateway-copy-publication"
                os.rename("gateway", "gateway", src_dir_fd=staging_fd, dst_dir_fd=target_parent)
                os.fsync(target_parent)
            finally:
                os.close(copied)
        finally:
            os.close(staging_fd)
            # Only this generated private staging tree is cleaned up.
            shutil.rmtree(staging)
    finally:
        os.close(parent)

def acl(config, path, *, recursive=False, writable=True):
    fd = directory(path)
    try:
        mode = "rwX" if writable else "rX"
        command = [config["setfacl"], "-m", f'u:{config["uid"]}:{mode}']
        if recursive:
            command += ["-R", "-P"]
        # /proc fd is a held canonical directory, not a re-resolved operator root.
        subprocess.run(command + [f"/proc/self/fd/{fd}/"], pass_fds=(fd,), check=True)
        if writable:
            subprocess.run([config["setfacl"], "-m", f'd:u:{config["uid"]}:rwx,d:u:{config["operatorUid"]}:rwx', f"/proc/self/fd/{fd}/"], pass_fds=(fd,), check=True)
            if recursive:
                # Existing nested directories need defaults too; do not follow symlinks.
                for base, dirs, _files in os.walk(f"/proc/self/fd/{fd}/", followlinks=False):
                    dirs[:] = [name for name in dirs if not Path(base, name).is_symlink()]
                    subprocess.run([config["setfacl"], "-m", f'd:u:{config["uid"]}:rwx,d:u:{config["operatorUid"]}:rwx', base], pass_fds=(fd,), check=True)
    finally:
        os.close(fd)



def history_ready(config):
    spec = importlib.util.spec_from_file_location("history_runtime", config["historyRuntime"])
    history = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(history)
    result = history.status({"nativeHome": config["nativeHome"], "root": config["historyRoot"], "protectedReadiness": True})
    if not result.get("active"):
        raise ValueError("protected identity requires the existing enabled history handoff")


def ready(config):
    state = directory(config["state"])
    try:
        info = os.fstat(state)
        marker = os.stat("identity-ready", dir_fd=state, follow_symlinks=False)
        if info.st_uid != config["uid"] or stat.S_IMODE(info.st_mode) != 0o700:
            raise ValueError("private state has unexpected owner/mode")
        if not stat.S_ISREG(marker.st_mode) or marker.st_uid != config.get("readyOwner", 0) or marker.st_nlink != 1 or stat.S_IMODE(marker.st_mode) != 0o600:
            raise ValueError("identity readiness marker has unexpected owner/type/mode")
        gateway = directory(str(Path(config["state"]) / "openshell/gateway"))
        try:
            gateway_info = os.fstat(gateway)
            if gateway_info.st_uid != config["uid"] or stat.S_IMODE(gateway_info.st_mode) != 0o700:
                raise ValueError("private gateway state has unexpected owner/mode")
        finally:
            os.close(gateway)
    finally:
        os.close(state)
    history_ready(config)

def setup(config):
    global STAGE
    STAGE = "root-authorization"
    if os.geteuid() != 0:
        raise ValueError("offline setup requires root")
    STAGE = "installed-allocation"
    validate_allocations(config)
    STAGE = "operator-quiescence"
    quiescent(config["operatorUid"])
    quiescent(config["uid"])
    STAGE = "history-readiness"
    history_ready(config)
    STAGE = "destination"
    state = directory(config["state"])
    source_parent = directory(str(Path(config["oldState"]) / "openshell"))
    try:
        if "identity-ready" in os.listdir(state) or "openshell" in os.listdir(state):
            raise ValueError("destination is already prepared or partial; review recovery before retrying")
        STAGE = "account-selector"
        old = directory(config["oldState"])
        try:
            account_fd = os.open("account-id.json", os.O_RDONLY | os.O_NOFOLLOW, dir_fd=old)
            try:
                info = os.fstat(account_fd)
                if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_uid != config["operatorUid"]:
                    raise ValueError("account selector has unexpected type/ownership")
                account = str(uuid.UUID(json.loads(os.read(account_fd, 256))))
            finally:
                os.close(account_fd)
        finally:
            os.close(old)
        STAGE = "workspace-validation"
        for root in config["workspaces"] + [config["oldState"]]:
            if str(Path(root).resolve()) != root or root in ("/", config["operatorHome"]):
                raise ValueError("workspace/state root is broad or aliased")
            fd = directory(root)
            os.close(fd)
        history_directories = config["historyDirectories"]
        for path in history_directories:
            fd = directory(path)
            os.close(fd)
        for path in config["historyFiles"]:
            fd = history_file(path, config["operatorUid"], create=True)
            os.close(fd)
        STAGE = "gateway-validation"
        source = os.open("gateway", DIRECTORY, dir_fd=source_parent)
        try:
            info = os.fstat(source)
            if info.st_uid != config["operatorUid"]:
                raise ValueError("retained gateway ownership differs from configured operator")
            expected = gateway_manifest(source)
            own_tree(source, config["uid"], config["gid"], apply=False)
            # Hold the source parent and source inode through the atomic rename.
            os.mkdir("openshell", 0o700, dir_fd=state)
            target_parent = os.open("openshell", DIRECTORY, dir_fd=state)
            try:
                quiescent(config["operatorUid"])
                STAGE = "gateway-relocation"
                try:
                    os.rename("gateway", "gateway", src_dir_fd=source_parent, dst_dir_fd=target_parent)
                except OSError as error:
                    if error.errno != errno.EXDEV:
                        raise
                    copied_gateway(config, source, target_parent, expected)
                    migration = "verified-copy-source-retained"
                else:
                    moved = os.stat("gateway", dir_fd=target_parent, follow_symlinks=False)
                    if (info.st_dev, info.st_ino) != (moved.st_dev, moved.st_ino):
                        raise ValueError("source changed; relocated tree is quarantined")
                    STAGE = "gateway-ownership"
                    own_tree(source, config["uid"], config["gid"])
                    migration = "atomic-relocation"
                os.fchown(target_parent, config["uid"], config["gid"])
            finally:
                os.close(target_parent)
        finally:
            os.close(source)
        STAGE = "account-publication"
        out = os.open("account-id.json", os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=state)
        try:
            os.write(out, json.dumps(account).encode())
            os.fchown(out, config["uid"], config["gid"])
            os.fsync(out)
        finally:
            os.close(out)
        STAGE = "workspace-history-acl"
        for ancestor in reversed(Path(config["oldState"]).parents):
            if ancestor != Path("/"):
                fd = directory(str(ancestor))
                try:
                    subprocess.run([config["setfacl"], "-m", f'u:{config["uid"]}:--x', f"/proc/self/fd/{fd}/"], pass_fds=(fd,), check=True)
                finally:
                    os.close(fd)
        fd = directory(config["oldState"])
        try:
            subprocess.run([config["setfacl"], "-m", f'u:{config["uid"]}:--x', f"/proc/self/fd/{fd}/"], pass_fds=(fd,), check=True)
        finally:
            os.close(fd)
        for root in config["workspaces"]:
            if str(Path(root).resolve()) != root or root in ("/", config["operatorHome"]):
                raise ValueError("workspace is broad or aliased")
            for ancestor in reversed(Path(root).parents):
                if ancestor != Path("/"):
                    fd = directory(str(ancestor))
                    try:
                        subprocess.run([config["setfacl"], "-m", f'u:{config["uid"]}:--x', f"/proc/self/fd/{fd}/"], pass_fds=(fd,), check=True)
                    finally:
                        os.close(fd)
            acl(config, root, recursive=True)
        # Only existing enabled history resources receive access; no auth/profile copy.
        for path in history_directories:
            if Path(path).exists():
                for ancestor in reversed(Path(path).parents):
                    if ancestor != Path("/"):
                        fd = directory(str(ancestor))
                        try:
                            subprocess.run([config["setfacl"], "-m", f'u:{config["uid"]}:--x', f"/proc/self/fd/{fd}/"], pass_fds=(fd,), check=True)
                        finally:
                            os.close(fd)
                acl(config, path, recursive=True)
        for path in config["historyFiles"]:
            fd = history_file(path, config["operatorUid"])
            try:
                subprocess.run([config["setfacl"], "-m", f'u:{config["uid"]}:rw', f"/proc/self/fd/{fd}"], pass_fds=(fd,), check=True)
            finally:
                os.close(fd)
        STAGE = "ready-publication"
        record = os.open("identity-migration.json", os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=state)
        try:
            os.write(record, json.dumps({"schema": 1, "mode": migration, "source": config["oldState"] + "/openshell/gateway", "version": "0.1.2", "operatorUid": config["operatorUid"], "operatorGid": info.st_gid}).encode())
            os.fsync(record)
        finally:
            os.close(record)
        marker = os.open("identity-ready", os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600, dir_fd=state)
        os.fsync(marker)
        os.close(marker)
        os.fsync(state)
        print("Prepared retained gateway and declared workspace/history access; no service started.")
    finally:
        os.close(source_parent)
        os.close(state)


if __name__ == "__main__":
    try:
        if len(sys.argv) == 3 and sys.argv[1] == "--ready":
            STAGE = "ready-validation"
            ready(json.loads(Path(sys.argv[2]).read_text()))
        elif len(sys.argv) == 2:
            setup(json.loads(Path(sys.argv[1]).read_text()))
        else:
            raise ValueError("fixed configuration only")
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        category = ("unsupported-cross-filesystem" if isinstance(error, OSError) and error.errno == errno.EXDEV else
                    "root-required" if STAGE == "root-authorization" else
                    "operator-active" if STAGE == "operator-quiescence" else
                    "already-or-partial-destination" if STAGE == "destination" else
                    "acl-failed" if STAGE == "workspace-history-acl" else
                    "copy-failed" if STAGE == "gateway-copy" else
                    "copy-verification-failed" if STAGE == "gateway-copy-verification" else
                    "validation-or-io-failed")
        print(f"Offline identity setup failed: stage={STAGE} category={category}. Inspect partial state offline using the recovery documentation; no automatic restart or rollback.", file=sys.stderr)
        raise SystemExit(1)
