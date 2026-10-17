"""Fixed immutable image import/configuration for the opt-in shutdown bundle."""
import hashlib
import io
import json
from pathlib import Path
import re
import socket
import subprocess
import sys
import tarfile
import time


class BackendError(Exception):
    pass


def sha256_file(path):
    with open(path, "rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def validate_images(images):
    if set(images) != {"runtime", "supervisor"}:
        raise BackendError("image-manifest-invalid")
    for image in images.values():
        if not str(image.get("archive", "")).startswith("/nix/store/") or any(
            re.fullmatch("[a-f0-9]{64}", image.get(key, "")) is None
            for key in ("id", "sha256", "binarySha256")
        ):
            raise BackendError("image-manifest-invalid")


def image_record(archive, binary):
    with tarfile.open(archive) as image:
        manifest = json.load(image.extractfile("manifest.json"))
        if len(manifest) != 1:
            raise BackendError("image-manifest-invalid")
        entry = manifest[0]
        config = image.extractfile(entry["Config"]).read()
        with tarfile.open(fileobj=io.BytesIO(image.extractfile(entry["Layers"][-1]).read())) as layer:
            files = [member for member in layer.getmembers() if member.isfile()]
            if len(files) != 1 or files[0].name.lstrip("./") != Path(binary).name:
                raise BackendError("image-layer-invalid")
            if hashlib.sha256(layer.extractfile(files[0]).read()).hexdigest() != sha256_file(binary):
                raise BackendError("image-binary-mismatch")
    return {"archive": archive, "id": hashlib.sha256(config).hexdigest(),
            "sha256": sha256_file(archive), "binarySha256": sha256_file(binary)}


def configure_gateway(template, images):
    validate_images(images)
    for role in ("runtime", "supervisor"):
        marker = "@PHOENIX_" + role.upper() + "_IMAGE@"
        if template.count(marker) != 1:
            raise BackendError("gateway-template-invalid")
        template = template.replace(marker, "sha256:" + images[role]["id"])
    return template


def wait_for_socket(path, deadline):
    # Requires/After with Type=simple does not imply the API socket is listening.
    # Retry only kernel-level not-ready states, under the same import deadline.
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise BackendError("image-import-timeout")
        try:
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as peer:
                peer.settimeout(min(1, remaining))
                peer.connect(path)
            return
        except (FileNotFoundError, ConnectionRefusedError):
            time.sleep(min(0.05, remaining))
        except OSError:
            raise BackendError("image-api-unavailable") from None


def import_images(config, images, runner=subprocess.run):
    validate_images(images)
    if not config["podman"].startswith("/nix/store/") or config["socket"] != "/run/user/1000/phoenix-openshell-podman.sock":
        raise BackendError("image-import-config-invalid")
    command = [config["podman"], "--remote", "--url", "unix:" + config["socket"]]
    environment = {"HOME": config["home"], "XDG_RUNTIME_DIR": config["runtimeDirectory"]}
    deadline = time.monotonic() + 20  # One shared socket/import budget.
    wait_for_socket(config["socket"], deadline)

    def invoke(arguments, allow_missing=False):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise BackendError("image-import-timeout")
        try:
            result = runner(command + arguments, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, env=environment, timeout=remaining)
        except subprocess.TimeoutExpired:
            raise BackendError("image-import-timeout") from None
        except OSError:
            raise BackendError("image-import-unavailable") from None
        if allow_missing and result.returncode == 1:
            return None
        if result.returncode:
            raise BackendError("image-import-failed")
        return result.stdout.decode("ascii", errors="replace").strip()

    for role in ("runtime", "supervisor"):
        image = images[role]
        # Podman 5.8.7 image-exists: 0 present, 1 missing, 125 storage error.
        # An existing content ID needs neither archive scan nor repeated import.
        if invoke(["image", "exists", "sha256:" + image["id"]], allow_missing=True) is None:
            if sha256_file(image["archive"]) != image["sha256"]:
                raise BackendError("image-archive-mismatch")
            # Immutable addition only. Never take launch.lock here: launcher
            # holds it while synchronously starting this unit.
            invoke(["load", "--input", image["archive"]])
        actual = invoke(["image", "inspect", "--format", "{{.Id}}", "sha256:" + image["id"]])
        if actual.removeprefix("sha256:") != image["id"]:
            raise BackendError("image-id-mismatch")


def main(argv):
    try:
        if len(argv) == 6 and argv[0] == "metadata":
            images = {role: image_record(archive, binary) for role, archive, binary in
                      (("runtime", argv[1], argv[3]), ("supervisor", argv[2], argv[4]))}
            Path(argv[5]).write_text(json.dumps(images, sort_keys=True))
        elif len(argv) == 4 and argv[0] == "configure":
            images = json.loads(Path(argv[2]).read_text())
            Path(argv[3]).write_text(configure_gateway(Path(argv[1]).read_text(), images))
        elif len(argv) == 2 and argv[0] == "import":
            config = json.loads(Path(argv[1]).read_text())
            import_images(config, json.loads(Path(config["manifest"]).read_text()))
        else:
            raise BackendError("image-command-invalid")
    except (OSError, ValueError, KeyError, tarfile.TarError):
        print("phoenix-shutdown: image-input-invalid", file=sys.stderr)
        return 1
    except BackendError as error:
        print("phoenix-shutdown: " + str(error), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
