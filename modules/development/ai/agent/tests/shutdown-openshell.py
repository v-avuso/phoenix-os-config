# NixOS driver script; variables images/policy supplied by shutdown-openshell.nix.
import json
import re
import shlex
import time
from typing import Any


def user(command):
    # Root driver drops identity directly: PAM sessions could restart the user
    # manager and invalidate the manager-stop observation/captures.
    environment = ("/run/current-system/sw/bin/env -i HOME=/home/fixture USER=fixture LOGNAME=fixture "
                   "PATH=/run/current-system/sw/bin XDG_RUNTIME_DIR=/run/user/1000 "
                   "DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus "
                   "OPENSHELL_GATEWAY=openshell "
                   "OPENSHELL_LOCAL_TLS_DIR=/home/fixture/.local/state/phoenix-openshell/tls ")
    return ("/run/current-system/sw/bin/setpriv --reuid=1000 --regid=$(id -g fixture) --init-groups "
            + environment + "/run/current-system/sw/bin/bash -c "
            + shlex.quote("cd /home/fixture && " + command))


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
    for name in ("shutdown-stream.log", "workload-stdout.log", "workload-status", "create-driver.log", "probe-baseline.log", "probe-keepid.log", "transaction-outcome.json", "transaction-units.log", "transaction-stop.log", "durable-sandbox.log", "shutdown-stream.status", "transaction-cgroups.json"):
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
        # Exact 0.1.2 network_broker.rs:824 keeps loopback local. Nonloopback
        # TCP enters staged mediation; supervisor-network/proxy.rs:700 emits
        # this destination-bound denial before any upstream connection.
        status, _ = machine.execute(user("openshell sandbox exec --name shutdown-acceptance --timeout 5 --no-tty -- /bin/curl --noproxy '*' --connect-timeout 2 --max-time 3 http://192.0.2.1/ </dev/null"), timeout=10)
        assert status != 0, "default-deny guest policy unexpectedly allowed HTTP"
        log_deadline = time.monotonic() + 10
        while True:
            supervisor_events = run("openshell logs shutdown-acceptance -n 100 --source sandbox", timeout=5)
            denied = any("192.0.2.1:80" in line and "denied staged transparent connection" in line.lower()
                         for line in supervisor_events.splitlines())
            if denied or time.monotonic() >= log_deadline:
                break
            time.sleep(1)
        assert denied, "destination-bound supervisor deny event missing; curl failure/stdout is not log evidence"
        # A bounded supported live log reader spans the ordinary stop.
        run("(timeout 90 openshell logs shutdown-acceptance --tail --source sandbox; echo $? > /tmp/shutdown-stream.status) </dev/null >/tmp/shutdown-stream.log 2>&1 & echo $! > /tmp/shutdown-stream.pid")
        machine.wait_until_succeeds(user("test -s /tmp/shutdown-stream.log && kill -0 $(cat /tmp/shutdown-stream.pid)"), timeout=10)
        capture("before-stop", containers)
        run("kill -0 $(cat /tmp/shutdown-stream.pid)")
        if stop_mode in {"transaction", "manager"}:
            # Exact recorded scopes only; never enumerate or stop unrelated units.
            scopes = ["libpod-" + containers[role] + ".scope" for role in ("sandbox", "supervisor")]
            for scope in scopes:
                assert run("systemctl --user show -p LoadState --value " + scope).strip() == "loaded", "recorded container scope not loaded"
            units = "phoenix-openshell-gateway.service " + " ".join(scopes)
            run("systemctl --user show -p Id -p LoadState -p Before -p ControlGroup -p TimeoutStopUSec " + units + " > /tmp/transaction-units.log")
            placements: dict[str, Any] = {}
            for role, identifier in containers.items():
                scope = "libpod-" + identifier + ".scope"
                before = run("systemctl --user show -p Before --value " + scope).split()
                control_group = run("systemctl --user show -p ControlGroup --value " + scope).strip()
                # Podman 5.8 inspect exposes the conmon PID file, not a portable
                # top-level ConmonPid field. Read only this fixture's file.
                metadata = json.loads(run("podman inspect " + identifier))[0]
                pid_file = metadata["ConmonPidFile"]
                assert pid_file.startswith("/run/user/1000/containers/"), "unexpected fixture conmon PID location"
                conmon_pid = run("cat " + shlex.quote(pid_file)).strip()
                assert conmon_pid.isdigit() and int(conmon_pid) > 1
                workload_pid = metadata["State"]["Pid"]
                assert isinstance(workload_pid, int) and workload_pid > 1
                conmon_cgroup = machine.succeed("cat /proc/" + conmon_pid + "/cgroup")
                workload_cgroup = machine.succeed("cat /proc/" + str(workload_pid) + "/cgroup")
                placements[role] = dict(scope=scope, before=before, controlGroup=control_group,
                                        conmonCgroup=conmon_cgroup, workloadCgroup=workload_cgroup)
            machine.succeed("printf %s " + shlex.quote(json.dumps(placements)) + " > /tmp/transaction-cgroups.json")
            capture("transaction-placement", containers)
            if ordering_configured:
                for placement in placements.values():
                    assert "phoenix-openshell-gateway.service" in placement["before"], "configured scope Before missing gateway"
                    assert placement["controlGroup"], "container scope resource cgroup missing"
                    conmon_paths = [line.split(":", 2)[2] for line in placement["conmonCgroup"].splitlines()]
                    workload_paths = [line.split(":", 2)[2] for line in placement["workloadCgroup"].splitlines()]
                    scope_path = placement["controlGroup"].rstrip("/")
                    assert not any(path == scope_path or path.startswith(scope_path + "/") for path in conmon_paths), "conmon remains inside container scope"
                    assert any(path == scope_path or path.startswith(scope_path + "/") for path in workload_paths), "workload missing container resource cgroup"
            run("kill -0 $(cat /tmp/shutdown-stream.pid)")
            stage = stop_mode + "-stop"
            machine.log("PHASE " + stage + " entered")
            started = time.monotonic()
            stop_command = ("timeout 50 systemctl stop user@1000.service" if stop_mode == "manager"
                            else user("timeout 50 systemctl --user stop " + units))
            status, _ = machine.execute(stop_command + " > /tmp/transaction-stop.log 2>&1", timeout=55)
            elapsed = time.monotonic() - started
            # Observe before any fixture-identity command; no PAM/session start.
            manager_active_status = machine.execute("systemctl is-active user@1000.service", timeout=5)[0]
            outcome: dict[str, Any] = dict(mode=stop_mode, stopStatus=status, stopSeconds=round(elapsed, 3))
            # Record independent results before assertions; known attached-create
            # and bootstrap failures must not prevent observing the transaction.
            outcome["transportStatus"] = machine.succeed("cat /tmp/workload-status 2>/dev/null || echo pending").strip()
            outcome["logReaderStatus"] = machine.succeed("cat /tmp/shutdown-stream.status 2>/dev/null || echo pending").strip()
            outcome["logReaderAlive"] = machine.execute(user("kill -0 $(cat /tmp/shutdown-stream.pid)"), timeout=5)[0] == 0
            output = machine.succeed("cat /tmp/workload-stdout.log")
            outcome["termMarker"] = "ACCEPT_TERM" in output
            outcome["finalMarker"] = "ACCEPT_FINAL" in output
            outcome["containers"] = {}
            for role, identifier in containers.items():
                # Direct local Podman needs no D-Bus, but may fail after the
                # runtime directory is removed. Capture that limitation; do not
                # restart the manager or synthesize runtime state to hide it.
                try:
                    inspect_status, state_output = machine.execute(user("podman inspect --format '{{json .State}}' " + identifier), timeout=10)
                except Exception:
                    inspect_status, state_output = 124, ""
                outcome.setdefault("inspectStatus", {})[role] = inspect_status
                if inspect_status == 0:
                    outcome["containers"][role] = json.loads(state_output)
            outcome["managerActiveStatus"] = manager_active_status
            machine.succeed("printf %s " + shlex.quote(json.dumps(outcome)) + " > /tmp/transaction-outcome.json")
            capture("after-transaction", containers)
            # A first stall ends the experiment after evidence, without restart.
            assert status == 0 and elapsed < 10, "combined stop failed or stalled; retain 45s fallback and captured phase"
            if stop_mode == "transaction":
                stage = "transaction-restart-observation"
                run("systemctl --user start phoenix-openshell-gateway.service", timeout=35)
                observed = run("openshell logs shutdown-acceptance -n 200 --source sandbox", timeout=10)
                machine.succeed("printf %s " + shlex.quote(observed) + " > /tmp/durable-sandbox.log")
                outcome["postRestartDenyObserved"] = any("192.0.2.1:80" in line and "denied staged transparent connection" in line.lower() for line in observed.splitlines())
                outcome["logStorageContract"] = "gateway process-memory tail; restart query is not durability proof"
                machine.succeed("printf %s " + shlex.quote(json.dumps(outcome)) + " > /tmp/transaction-outcome.json")
                capture("after-gateway-restart", containers)
            else:
                assert outcome["managerActiveStatus"] != 0, "guest user manager survived stop"
            assert len(outcome["containers"]) == 2, "post-stop local Podman inspection unavailable; see inspectStatus, no restart attempted"
            assert outcome["termMarker"] and outcome["finalMarker"], "transaction workload final markers missing"
            assert all(not state["Running"] for state in outcome["containers"].values()), "transaction container survived"
            assert outcome["transportStatus"] == "0", "transaction attached transport incomplete/nonzero; timing alone is not full acceptance"
            assert all(state["ExitCode"] == 0 for state in outcome["containers"].values()), "transaction bootstrap/container nonzero exit"
        else:
            stage = "ordinary-stop"
            machine.log("PHASE ordinary-stop entered")
            started = time.monotonic()
            run("openshell sandbox stop shutdown-acceptance", timeout=50)
            elapsed = time.monotonic() - started
            machine.log("PHASE ordinary-stop completed seconds=" + str(round(elapsed, 3)))
            stage = "ordinary-stop-assertions"
            machine.wait_until_succeeds(user("test -f /tmp/workload-status"), timeout=5)
            output = machine.succeed("cat /tmp/workload-stdout.log")
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
