# NixOS driver script; variables images/policy supplied by shutdown-openshell.nix.
import json
import re
import shlex
import time


def user(command):
    environment = "export XDG_RUNTIME_DIR=/run/user/1000 DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus OPENSHELL_GATEWAY=openshell OPENSHELL_LOCAL_TLS_DIR=/home/fixture/.local/state/phoenix-openshell/tls; "
    return "su fixture -l -c " + shlex.quote(environment + command)


def run(command, timeout=30):
    return machine.succeed(user(command), timeout=timeout)


def capture(stage, containers):
    # Public disposable fixture only; bound every capture and retain on failure.
    machine.log("CAPTURE " + stage)
    machine.succeed(user("mkdir -p /tmp/shutdown-evidence"))
    for role, identifier in containers.items():
        if not re.fullmatch("[a-f0-9]{64}", identifier):
            continue
        machine.execute(user("podman logs --tail 200 --timestamps " + identifier + " > /tmp/shutdown-evidence/" + role + ".log 2>&1"), timeout=10)
        machine.execute(user("podman inspect " + identifier + " > /tmp/shutdown-evidence/" + role + ".json"), timeout=10)
    machine.execute(user("openshell logs shutdown-acceptance -n 200 --source sandbox > /tmp/shutdown-evidence/gateway-sandbox.log 2>&1"), timeout=10)
    machine.execute("journalctl -b --no-pager -n 400 -u user@1000.service > /tmp/shutdown-evidence/user-manager.log", timeout=10)
    machine.execute(user("journalctl --user -b --no-pager -n 400 > /tmp/shutdown-evidence/user-units.log"), timeout=10)
    for name in ("shutdown-stream.log", "workload-stdout.log", "workload-status", "create-driver.log"):
        machine.execute("test ! -f /tmp/" + name + " || cp /tmp/" + name + " /tmp/shutdown-evidence/" + name, timeout=5)
    machine.copy_from_machine("/tmp/shutdown-evidence", stage)


start_all()
containers = {}
stage = "guest-setup"
try:
    machine.wait_for_unit("multi-user.target", timeout=60)
    machine.succeed("loginctl enable-linger fixture")
    machine.wait_for_unit("user@1000.service", timeout=30)
    run("systemctl --user is-system-running --wait")
    machine.log(machine.succeed("systemctl --version").splitlines()[0])
    machine.log(run("podman --version").strip())
    stage = "image-load"
    for role, image in images.items():
        run("podman load --input " + shlex.quote(image["archive"]), timeout=60)
        loaded = run("podman image inspect --format '{{.Id}}' sha256:" + image["id"]).strip()
        assert loaded.removeprefix("sha256:") == image["id"], "loaded image ID mismatch: " + role
    stage = "gateway-ready"
    run("mkdir -p ~/.local/state/phoenix-openshell")
    run("systemctl --user start phoenix-openshell-gateway.service", timeout=35)
    run("openshell gateway add --local --name openshell https://127.0.0.1:17670")
    run("openshell status")
    stage = "sandbox-create"
    workload = "trap 'printf \"ACCEPT_TERM\\n\"; sleep 1; printf \"ACCEPT_FINAL\\n\"; exit 0' TERM; echo ACCEPT_READY; while :; do echo ACCEPT_TICK; sleep 1; done"
    create = ("openshell sandbox create --name shutdown-acceptance --no-auto-providers --no-tty --from sha256:"
              + images["workload"]["id"] + " --policy " + shlex.quote(policy)
              + " --cpu 2 --memory 512Mi -- /bin/bash -c " + shlex.quote(workload))
    # Keep the supported attached create stream: canonical process output is
    # multiplexed by OpenShell and need not appear in Podman's runtime stdout.
    run("(timeout 120 " + create + " > /tmp/workload-stdout.log 2>&1; echo $? > /tmp/workload-status) </dev/null >/tmp/create-driver.log 2>&1 &")
    machine.wait_until_succeeds(user("grep -q ACCEPT_READY /tmp/workload-stdout.log"), timeout=60)
    records = json.loads(run("podman ps -a --filter label=openshell.managed=true --format json"))
    for record in records:
        role = record.get("Labels", {}).get("openshell.ai/isolation-role")
        if role in {"sandbox", "supervisor"}:
            assert role not in containers, "unexpected duplicate fixture role"
            containers[role] = record["Id"]
    assert set(containers) == {"sandbox", "supervisor"}, "expected one workload and supervisor"
    for identifier in containers.values():
        assert re.fullmatch("[a-f0-9]{64}", identifier)
    stage = "supervisor-policy-event"
    # Deliberately denied guest-local HTTP, no provider or external destination.
    status, _ = machine.execute(user("openshell sandbox exec --name shutdown-acceptance --timeout 5 --no-tty -- /bin/curl --max-time 2 http://127.0.0.1:17671/readyz </dev/null"), timeout=10)
    assert status != 0, "default-deny guest policy unexpectedly allowed HTTP"
    supervisor_events = run("openshell logs shutdown-acceptance -n 100 --source sandbox")
    assert re.search(r"denied|deny", supervisor_events, re.IGNORECASE), "supervisor deny event missing; stdout is not log evidence"
    # A bounded supported live log reader spans the ordinary stop.
    run("(timeout 90 openshell logs shutdown-acceptance --tail --source sandbox) </dev/null >/tmp/shutdown-stream.log 2>&1 & echo $! > /tmp/shutdown-stream.pid")
    machine.wait_until_succeeds(user("test -s /tmp/shutdown-stream.log && kill -0 $(cat /tmp/shutdown-stream.pid)"), timeout=10)
    capture("before-stop", containers)
    run("kill -0 $(cat /tmp/shutdown-stream.pid)")
    stage = "ordinary-stop"
    machine.log("PHASE ordinary-stop entered")
    started = time.monotonic()
    run("openshell sandbox stop shutdown-acceptance", timeout=50)
    elapsed = time.monotonic() - started
    machine.log("PHASE ordinary-stop completed seconds=" + str(round(elapsed, 3)))
    stage = "ordinary-stop-assertions"
    machine.wait_until_succeeds(user("test -f /tmp/workload-status"), timeout=5)
    output = run("cat /tmp/workload-stdout.log")
    assert run("cat /tmp/workload-status").strip() == "0", "attached workload transport did not exit zero"
    assert "ACCEPT_TERM" in output and "ACCEPT_FINAL" in output, "workload final markers missing"
    for role, identifier in containers.items():
        state = json.loads(run("podman inspect --format '{{json .State}}' " + identifier))
        assert not state["Running"], "fixture container survived: " + role
        assert state["ExitCode"] == 0, "fixture forced/nonzero exit: " + role
    assert elapsed < 10, "cooperative ordinary stop exceeded ten seconds; preserve 45s fallback"
    machine.log("Ordinary stop markers and container exit passed; final supervisor drain is separate evidence")
finally:
    capture(stage, containers)
    machine.execute(user("test ! -f /tmp/shutdown-stream.pid || kill $(cat /tmp/shutdown-stream.pid)"), timeout=5)
    for name in ("shutdown-stream.log", "workload-stdout.log", "workload-status", "create-driver.log"):
        machine.execute("test ! -f /tmp/" + name + " || cp /tmp/" + name + " /tmp/shutdown-evidence/" + name, timeout=5)
    machine.copy_from_machine("/tmp/shutdown-evidence", "final")
