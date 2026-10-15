# NixOS driver only: actual activation and rollback happen inside this guest.
import json
import shlex
import time

start_all()
root = "/var/lib/activation-runtime"
units = []
try:
    machine.wait_for_unit("multi-user.target", timeout=30)
    machine.succeed("mkdir -m 700 " + root)
    baseline_runtime = machine.succeed("readlink -f /run/current-system").strip()
    # Some test images omit the system profile; initialize guest-only provenance.
    machine.succeed("test -e /nix/var/nix/profiles/system || { mkdir -p /nix/var/nix/profiles; ln -s " + baseline_runtime + " /nix/var/nix/profiles/system; }")
    profile = machine.succeed("readlink -f /nix/var/nix/profiles/system").strip()
    candidates = {name: machine.succeed("readlink -f " + baseline_runtime + "/specialisation/" + name).strip()
                  for name in ("good", "failing")}
    config = dict(baseline="/etc/phoenix-agent/activated-source", activationLock=root + "/activation.lock",
                  activationEnvironment=activation_environment, reviewScript=review)
    machine.succeed("printf %s " + shlex.quote(json.dumps(config)) + " >" + root + "/config.json; chmod 600 " + root + "/config.json")
    results: dict[str, object] = {}
    for name in ("good", "failing"):
        unit = "phoenix-activation-" + name + ".service"
        units.append(unit)
        arguments = [python, "-I", controller, root + "/config.json", "activate", candidates[name], "test",
                     "--expected-base", source, "--expected-source", source, "--expected-profile", profile]
        command = ("timeout 60 systemd-run --quiet --wait --collect --service-type=exec "
                   "--property=RuntimeMaxSec=55 --property=TimeoutStopSec=5 --unit=" + unit + " "
                   + " ".join(shlex.quote(value) for value in arguments))
        entered = time.monotonic()
        status, _ = machine.execute(command + " >" + root + "/" + name + ".log 2>&1", timeout=65)
        runtime = machine.succeed("readlink -f /run/current-system").strip()
        marker = machine.succeed("cat /etc/activation-runtime-marker").strip()
        current_profile = machine.succeed("readlink -f /nix/var/nix/profiles/system").strip()
        results[name] = dict(status=status, seconds=round(time.monotonic() - entered, 3),
                             runtime=runtime, marker=marker, bootProfile=current_profile)
        machine.succeed("printf %s " + shlex.quote(json.dumps(results)) + " >" + root + "/receipt.json")
        assert current_profile == profile, "temporary activation changed boot profile"
        if name == "good":
            assert status == 0 and runtime == candidates["good"] and marker == "good", "good specialisation did not activate"
        else:
            assert status != 0 and status != 124, "failing activation did not return bounded failure"
            assert machine.succeed("cat " + root + "/failure-observed").strip() == "failing", "real failing activation did not change /etc before error"
            assert runtime == candidates["good"] and marker == "good", "production rollback did not restore previous runtime and marker"
    machine.succeed("test -f " + root + "/activation.lock && test $(stat -c %u:%a " + root + "/activation.lock) = 0:600")
finally:
    machine.execute("journalctl -b --no-pager " + " ".join("-u " + unit for unit in units) + " > /tmp/activation-runtime-journal.log", timeout=10)
    machine.copy_from_machine("/tmp/activation-runtime-journal.log", "evidence")
    for name in ("good.log", "failing.log", "receipt.json", "failure-observed"):
        status, _ = machine.execute("test -f " + root + "/" + name + " && cp " + root + "/" + name + " /tmp/" + name, timeout=5)
        if status == 0:
            machine.copy_from_machine("/tmp/" + name, "evidence")
