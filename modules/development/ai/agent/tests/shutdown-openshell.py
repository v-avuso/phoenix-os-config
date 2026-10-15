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
    # Public disposable fixture only; a failed capture must not mask the stage.
    machine.log("CAPTURE " + stage)
    machine.succeed(user("mkdir -p /tmp/shutdown-evidence"))
    def bounded(command):
        try:
            return machine.execute(command, timeout=10)
        except Exception:
            machine.log("Bounded diagnostic unavailable during " + stage)
            return 124, ""
    status, output = bounded(user("podman ps -a --filter label=openshell.managed=true --filter label=openshell.ai/sandbox-name=shutdown-acceptance --format json"))
    if status == 0:
        try:
            records = json.loads(output)
        except json.JSONDecodeError:
            records = []
            machine.log("Partial container metadata unavailable during " + stage)
        for record in records:
            role = record.get("Labels", {}).get("openshell.ai/isolation-role")
            identifier = record.get("Id", "")
            if role in {"sandbox", "supervisor"} and re.fullmatch("[a-f0-9]{64}", identifier):
                containers.setdefault(role, identifier)
    bounded(user("podman ps -a --format json > /tmp/shutdown-evidence/guest-podman-ps.json"))
    for name in ("phoenix-probe-baseline", "phoenix-probe-keepid"):
        bounded(user("podman inspect " + name + " > /tmp/shutdown-evidence/" + name + ".json 2>&1"))
    for role, identifier in containers.items():
        if not re.fullmatch("[a-f0-9]{64}", identifier):
            continue
        bounded(user("podman logs --tail 200 --timestamps " + identifier + " > /tmp/shutdown-evidence/" + role + ".log 2>&1"))
        bounded(user("podman inspect " + identifier + " > /tmp/shutdown-evidence/" + role + ".json"))
    if not probe_create_only:
        bounded(user("openshell logs shutdown-acceptance -n 200 --source sandbox > /tmp/shutdown-evidence/gateway-sandbox.log 2>&1"))
    bounded("journalctl -b --no-pager -n 400 -u user@1000.service > /tmp/shutdown-evidence/user-manager.log")
    bounded(user("journalctl --user -b --no-pager -n 400 > /tmp/shutdown-evidence/user-units.log"))
    bounded("printf %s " + shlex.quote(json.dumps(probe_timings)) + " > /tmp/shutdown-evidence/probe-timing.json")
    for name in ("shutdown-stream.log", "workload-stdout.log", "workload-status", "create-driver.log", "probe-baseline.log", "probe-keepid.log"):
        bounded("test ! -f /tmp/" + name + " || cp /tmp/" + name + " /tmp/shutdown-evidence/" + name)
    machine.copy_from_machine("/tmp/shutdown-evidence", stage)


def wait_workload_ready():
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        state = run("if grep -q ACCEPT_READY /tmp/workload-stdout.log; then echo ready; elif test -f /tmp/workload-status; then echo exited; else echo waiting; fi").strip()
        if state == "ready":
            return
        assert state != "exited", "attached create exited before readiness; inspect captured workload stream/status"
        time.sleep(1)
    raise AssertionError("workload readiness deadline exceeded")


start_all()
containers = {}
probe_timings = []
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
    if probe_create_only:
        stage = "probe-api-ready"
        run("systemctl --user start phoenix-openshell-podman.service")
        remote = "podman --remote --url unix:///run/user/1000/phoenix-openshell-podman.sock "
        for name, namespace in (("baseline", ""), ("keepid", "--userns keep-id:uid=1000,gid=1000 ")):
            stage = "probe-create-" + name
            machine.log("PHASE " + stage + " entered")
            started = time.monotonic()
            command = (remote + "create --pull=never --network=none " + namespace
                       + "--label phoenix.shutdown-fixture=create-probe --name phoenix-probe-" + name
                       + " --entrypoint /bin/true sha256:" + images["workload"]["id"])
            status, _ = machine.execute(user("timeout 35 " + command + " </dev/null >/tmp/probe-" + name + ".log 2>&1"), timeout=40)
            elapsed = time.monotonic() - started
            probe_timings.append(dict(probe=name, status=status, seconds=round(elapsed, 3)))
            machine.log("PHASE " + stage + " completed " + json.dumps(probe_timings[-1]))
            assert status == 0, "remote create failed or reached 35-second cap; stop after captures"
            capture(stage, containers)
            run(remote + "rm phoenix-probe-" + name, timeout=10)
        stage = "probe-complete"
        machine.log("Create-only probe complete; no gateway, workload start or ordinary stop attempted")
    else:
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
        wait_workload_ready()
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
