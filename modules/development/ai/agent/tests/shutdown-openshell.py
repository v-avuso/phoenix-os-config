# NixOS driver script; variables images/policy supplied by shutdown-openshell.nix.
import json
import re
import shlex
import time
from typing import Any

peer_unavailable = False


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
            + shlex.quote("cd /home/fixture || exit 1; " + command))


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
    if not probe_create_only and not peer_unavailable:
        bounded(user("openshell logs shutdown-acceptance -n 200 --source sandbox > /tmp/shutdown-evidence/gateway-sandbox.log 2>&1"))
    bounded("journalctl -b --no-pager -n 400 -u user@1000.service > /tmp/shutdown-evidence/user-manager.log")
    bounded(user("journalctl --user -b --no-pager -n 400 > /tmp/shutdown-evidence/user-units.log"))
    bounded("printf %s " + shlex.quote(json.dumps(probe_timings)) + " > /tmp/shutdown-evidence/probe-timing.json")
    for name in ("shutdown-stream.log", "workload-stdout.log", "workload-status", "create-driver.log", "probe-baseline.log", "probe-keepid.log", "transaction-outcome.json", "transaction-units.log", "transaction-stop.log", "durable-sandbox.log", "shutdown-stream.status", "transaction-cgroups.json", "terminal-delivery-outcome.json", "runtime-classification-outcome.json", "log-drain-outcome.json", "post-stop-gateway-sandbox.log", "negative-outcome.json", "negative-stop.log", "peer-shutdown-markers", "cold-module-startup.json"):
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
    if cold_module_units:
        assert run("podman images --quiet").strip() == "", "cold module fixture store is not empty"
        assert machine.execute(user("systemctl --user is-active --quiet phoenix-openshell-gateway.service"), timeout=3)[0] != 0, "module gateway started before controlled cold start"
    for role, image in images.items():
        if cold_module_units:
            continue  # Importer, not the driver, must load the backend images.
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
        if cold_module_units:
            stage = "cold-module-gateway-start"
            started = time.monotonic()
            status, _ = machine.execute(user("flock -n ~/.local/state/phoenix-openshell/launch.lock systemctl --user start phoenix-openshell-gateway.service"), timeout=55)
            imported_ids: dict[str, Any] = {}
            startup = dict(startStatus=status, startupSeconds=round(time.monotonic() - started, 3),
                           launchLockHeldDuringStart=True, storeInitiallyEmpty=True, importedIDs=imported_ids)
            for role in ("runtime", "supervisor"):
                inspect_status, value = machine.execute(user("podman image inspect --format '{{.Id}}' sha256:" + images[role]["id"]), timeout=5)
                imported_ids[role] = dict(status=inspect_status, id=value.strip())
            machine.succeed("printf %s " + shlex.quote(json.dumps(startup)) + " > /tmp/cold-module-startup.json")
            machine.log("COLD_MODULE_STARTUP " + json.dumps(startup, sort_keys=True))
            assert status == 0, "actual module cold start failed; retain importer/unit journals"
            for role, observed in imported_ids.items():
                assert observed["status"] == 0 and observed["id"].removeprefix("sha256:") == images[role]["id"], "actual module importer image binding mismatch"
            # Only the small workload is driver-loaded, after the module importer proof.
            run("podman load --input " + shlex.quote(images["workload"]["archive"]), timeout=60)
        else:
            run("systemctl --user start phoenix-openshell-gateway.service", timeout=35)
        run("openshell gateway add --local --name openshell https://127.0.0.1:17670")
        run("openshell status")
        stage = "sandbox-create"
        workload = "trap 'printf \"ACCEPT_TERM\\n\"; sleep 1; printf \"ACCEPT_FINAL\\n\"; exit 0' TERM; echo ACCEPT_READY; while :; do echo ACCEPT_TICK; sleep 1; done"
        if negative_case == "term-ignore":
            workload = "trap 'echo ACCEPT_TERM_IGNORED' TERM; echo ACCEPT_READY; while :; do echo ACCEPT_TICK; sleep 1; done"
        elif negative_case == "gateway-unavailable":
            # Finish independent evidence before touching the failed relay's stdout.
            workload = "trap 'printf \"ACCEPT_TERM\\n\" >> /sandbox/shutdown-markers; sleep 1; printf \"ACCEPT_FINAL\\n\" >> /sandbox/shutdown-markers; printf \"ACCEPT_TERM\\nACCEPT_FINAL\\n\"; exit 0' TERM; : > /sandbox/shutdown-markers; echo ACCEPT_READY; while :; do echo ACCEPT_TICK; sleep 1; done"
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
        runtime_binding = None
        supervisor_binding = None
        if negative_case is not None or acceptance_scope in {"runtime-classification", "log-drain", "ordered-lifecycle"}:
            actual = json.loads(run("podman inspect " + containers["sandbox"]))[0]
            source = actual["Config"]["Labels"]["openshell.ai/runtime-binary-source"]
            expected = "/home/fixture/.local/share/openshell/podman-sandbox/" + images["runtime"]["id"] + "/openshell-sandbox"
            assert source == expected, "runtime binary source does not bind selected image ID"
            pid = actual["State"]["Pid"]
            assert isinstance(pid, int) and pid > 1
            executable_hash = machine.succeed("sha256sum /proc/" + str(pid) + "/exe").split()[0]
            assert executable_hash == images["runtime"].get("binarySha256", "745245e8f79e6a5050a78570a79b24ac3488c50dd3636ec5c8409755ec418d94"), "running runtime ELF differs from independently verified image record"
            runtime_binding = dict(imageID=images["runtime"]["id"], binarySource=source, executableSha256=executable_hash)
        if negative_case is not None or acceptance_scope in {"log-drain", "ordered-lifecycle"}:
            supervisor_actual = json.loads(run("podman inspect " + containers["supervisor"]))[0]
            assert supervisor_actual["Image"].removeprefix("sha256:") == images["supervisor"]["id"], "running supervisor image differs from selected artifact"
            assert supervisor_actual["Config"]["Labels"]["openshell.ai/sandbox-id"] == actual["Config"]["Labels"]["openshell.ai/sandbox-id"]
            pid = supervisor_actual["State"]["Pid"]
            assert isinstance(pid, int) and pid > 1
            executable_hash = machine.succeed("sha256sum /proc/" + str(pid) + "/exe").split()[0]
            assert executable_hash == images["supervisor"].get("binarySha256", "14c412633c65c57a2c20fc2f3c093c6a181238f25628a854ffe95abd43f88f8c"), "running supervisor ELF differs from independently verified image record"
            supervisor_binding = dict(imageID=images["supervisor"]["id"], executableSha256=executable_hash,
                                      sandboxID=supervisor_actual["Config"]["Labels"]["openshell.ai/sandbox-id"])
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
        if stop_mode in {"transaction", "manager"} or negative_case is not None:
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
            if acceptance_scope == "ordered-lifecycle" or negative_case is not None:
                scope_path = placements["sandbox"]["controlGroup"].rstrip("/")
                limits = {name: machine.succeed("cat /sys/fs/cgroup" + scope_path + "/" + name).strip()
                          for name in ("memory.max", "pids.max")}
                machine.log("ORDERED_RESOURCE_LIMITS " + json.dumps(limits, sort_keys=True))
                assert limits == {"memory.max": "536870912", "pids.max": "512"}, "requested workload resource limits missing"
            run("kill -0 $(cat /tmp/shutdown-stream.pid)")
        if negative_case is not None:
            stage = "negative-" + negative_case
            machine.log("PHASE " + stage + " entered")
            restart = run("systemctl --user show -p Restart --value phoenix-openshell-gateway.service").strip()
            assert restart == "no", "peer injection requires gateway restart disabled"
            started = time.monotonic()
            if negative_case == "gateway-unavailable":
                run("systemctl --user kill --kill-whom=main --signal=SIGKILL phoenix-openshell-gateway.service")
                machine.wait_until_fails(user("systemctl --user is-active --quiet phoenix-openshell-gateway.service"), timeout=3)
                peer_unavailable = True
                # Mirror the pinned driver's exact supervisor-then-runtime stop order.
                # The unavailable gateway CLI is deliberately not the stop transport.
                command = "podman stop --time 45 " + containers["supervisor"] + " && podman stop --time 45 " + containers["sandbox"]
            else:
                command = "openshell sandbox stop shutdown-acceptance"
            stop_status, _ = machine.execute(user("timeout 50 bash -c " + shlex.quote(command) + " > /tmp/negative-stop.log 2>&1"), timeout=55)
            elapsed = time.monotonic() - started
            observation_started = time.monotonic()
            deadline = observation_started + (peer_client_observation_seconds if negative_case == "gateway-unavailable" else 5)
            while machine.execute("test -f /tmp/workload-status", timeout=2)[0] != 0 and time.monotonic() < deadline:
                time.sleep(0.1)
            transport_status = machine.succeed("cat /tmp/workload-status 2>/dev/null || echo pending").strip()
            output = machine.succeed("cat /tmp/workload-stdout.log")
            states = {role: json.loads(run("podman inspect --format '{{json .State}}' " + identifier)) for role, identifier in containers.items()}
            supervisor_log = run("podman logs --tail 200 " + containers["supervisor"] + " 2>&1")
            pattern = re.compile(r"openshell: log push shutdown LogPushOutcome \{ accepted_tail_acknowledged: (true|false), local_dropped_lines: ([0-9]+), prior_stream_delivery_uncertain: (true|false), incomplete: ([A-Za-z()]+) \}")
            receipts = [match.groups() for line in supervisor_log.splitlines() if (match := pattern.fullmatch(line))]
            scope_active = {role: machine.execute(user("systemctl --user is-active --quiet libpod-" + identifier + ".scope"), timeout=3)[0] for role, identifier in containers.items()}
            marker_copy_status, local_markers = None, ""
            if negative_case == "gateway-unavailable":
                marker_copy_status, _ = machine.execute(user("timeout 5 podman cp " + containers["sandbox"] + ":/sandbox/shutdown-markers /tmp/peer-shutdown-markers"), timeout=6)
                if marker_copy_status == 0:
                    local_markers = machine.succeed("head -c 256 /tmp/peer-shutdown-markers")
            cancel = "openshell: terminal delivery cancelled by administrative shutdown" in output
            # main.rs keeps sandboxes by default: the supervised route reports its
            # fixed recovery expiry. Ephemeral cleanup errors are distinct; arbitrary
            # nonzero status is not typed proof.
            peer_cleanup_failure = "ephemeral cleanup failed:" in output or "Failed to delete sandbox shutdown-acceptance:" in output
            peer_recovery_timeout = "Unable to restore the sandbox connection within 60 seconds." in output
            peer_client_proved = (transport_status == "255" and peer_recovery_timeout) or (transport_status.isdecimal() and int(transport_status) not in {0, 124, 137} and peer_cleanup_failure)
            outcome = dict(scope="negative-shutdown", negativeCase=negative_case, stopSeconds=round(elapsed, 3), stopStatus=stop_status,
                           fallbackCommandBoundSeconds=50, initialTimingTargetSeconds=10, transportStatus=transport_status,
                           clientObservationBudgetSeconds=peer_client_observation_seconds, clientObservationSeconds=round(time.monotonic() - observation_started, 3),
                           peerCleanupDiagnosticMatched=peer_cleanup_failure, peerRecoveryTimeoutDiagnosticMatched=peer_recovery_timeout, peerClientFailureProved=peer_client_proved,
                           adminCancellationMessage=cancel, clientFailureProved=cancel and transport_status == "1",
                           clientDiagnostic="".join(c for c in output[-1000:] if c in "\n\t" or 32 <= ord(c) < 127),
                           markerCopyStatus=marker_copy_status, localMarkers=local_markers,
                           localTermMarker="ACCEPT_TERM" in local_markers, localFinalMarker="ACCEPT_FINAL" in local_markers,
                           ignoredTermMarker="ACCEPT_TERM_IGNORED" in output, termMarker="ACCEPT_TERM" in output,
                           finalMarker="ACCEPT_FINAL" in output, priorGatewayEventProved=denied, containers=states,
                           runtimeBinding=runtime_binding, supervisorBinding=supervisor_binding, scopeActiveStatus=scope_active,
                           gatewayRestart=restart, gatewayActiveStatus=machine.execute(user("systemctl --user is-active --quiet phoenix-openshell-gateway.service"), timeout=3)[0],
                           rpcReceiptCount=len(receipts), rpcReceipt=receipts[0] if len(receipts) == 1 else None,
                           pid1SigkillProved=False, allLogsProved=False)
            machine.succeed("printf %s " + shlex.quote(json.dumps(outcome)) + " > /tmp/negative-outcome.json")
            machine.log("NEGATIVE_SHUTDOWN " + json.dumps(outcome, sort_keys=True))
            assert stop_status == 0 and elapsed < 10, "negative stop exceeded initial ten-second gate; preserve captured fifty-second fallback result"
            assert all(not state["Running"] and not state["OOMKilled"] for state in states.values()), "negative workload survived or OOM"
            assert all(status != 0 for status in scope_active.values()), "negative container scope remains active"
            assert len(receipts) == 1, "negative stop lacks one actual log outcome"
            if negative_case == "term-ignore":
                # lib.rs waits five seconds then Boundary Terminate maps to Kill;
                # 137 is reported workload status, not evidence PID1 was SIGKILLed.
                assert outcome["ignoredTermMarker"] and not outcome["finalMarker"], "TERM-ignore stimulus or missing-final evidence invalid"
                assert states["supervisor"]["ExitCode"] == 137 and states["sandbox"]["ExitCode"] == 0, "forced workload status differs from pinned termination contract"
                assert outcome["clientFailureProved"], "TERM-ignore client cancellation not explicit"
                assert receipts[0] == ("true", "0", "false", "None"), "TERM-ignore accepted-tail acknowledgement incomplete"
            else:
                assert outcome["gatewayActiveStatus"] != 0, "failed gateway restarted"
                assert marker_copy_status == 0 and outcome["localTermMarker"] and outcome["localFinalMarker"], "peer-loss independent TERM/FINAL evidence missing"
                assert all(state["ExitCode"] == 0 for state in states.values()), "peer-loss cooperative local cleanup incomplete"
                assert receipts[0][0] == "false" and receipts[0][3] in {"Some(NotConnected)", "Some(RpcError)", "Some(Timeout)"}, "peer-loss log outcome falsely acknowledges or lacks typed cause"
                if peer_client_observation_seconds == 75:
                    assert outcome["peerClientFailureProved"], "peer client did not complete with a recognized pinned failure within the observation bound"
                # Unknown/pending CLI errors prove no client success or typed cause.
                # This case's acceptance is local cleanup plus explicit log failure.
                if not outcome["peerClientFailureProved"]:
                    machine.log("PEER_LOSS_CLIENT_CLAIM_UNPROVED: see bounded clientDiagnostic")
        elif stop_mode in {"transaction", "manager"}:
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
            if stop_mode == "transaction" and acceptance_scope != "ordered-lifecycle":
                stage = "transaction-restart-observation"
                run("systemctl --user start phoenix-openshell-gateway.service", timeout=35)
                observed = run("openshell logs shutdown-acceptance -n 200 --source sandbox", timeout=10)
                machine.succeed("printf %s " + shlex.quote(observed) + " > /tmp/durable-sandbox.log")
                outcome["postRestartDenyObserved"] = any("192.0.2.1:80" in line and "denied staged transparent connection" in line.lower() for line in observed.splitlines())
                outcome["logStorageContract"] = "gateway process-memory tail; restart query is not durability proof"
                machine.succeed("printf %s " + shlex.quote(json.dumps(outcome)) + " > /tmp/transaction-outcome.json")
                capture("after-gateway-restart", containers)
            elif stop_mode == "manager":
                assert outcome["managerActiveStatus"] != 0, "guest user manager survived stop"
            assert len(outcome["containers"]) == 2, "post-stop local Podman inspection unavailable; see inspectStatus, no restart attempted"
            assert outcome["termMarker"] and outcome["finalMarker"], "transaction workload final markers missing"
            assert all(not state["Running"] for state in outcome["containers"].values()), "transaction container survived"
            if acceptance_scope == "ordered-lifecycle":
                # No gateway restart/GetLogs: capture the actual local RPC receipt.
                supervisor_log = run("podman logs --tail 200 " + containers["supervisor"] + " 2>&1")
                runtime_log = run("podman logs --tail 200 " + containers["sandbox"] + " 2>&1")
                pattern = re.compile(r"openshell: log push shutdown LogPushOutcome \{ accepted_tail_acknowledged: (true|false), local_dropped_lines: ([0-9]+), prior_stream_delivery_uncertain: (true|false), incomplete: ([A-Za-z()]+) \}")
                receipts = [match.groups() for line in supervisor_log.splitlines() if (match := pattern.fullmatch(line))]
                outcome.update(scope=acceptance_scope, runtimeBinding=runtime_binding, supervisorBinding=supervisor_binding,
                               adminCancellationMessage="openshell: terminal delivery cancelled by administrative shutdown" in output,
                               rpcReceiptCount=len(receipts), rpcReceipt=receipts[0] if len(receipts) == 1 else None,
                               runtimeConfirmationWarningPresent="before supervisor confirmation" in runtime_log,
                               fullGracefulShutdownProved=False, gatewayRestartDurabilityProved=False)
                machine.succeed("printf %s " + shlex.quote(json.dumps(outcome)) + " > /tmp/transaction-outcome.json")
                machine.log("ORDERED_LIFECYCLE " + json.dumps(outcome, sort_keys=True))
                assert outcome["transportStatus"].isdecimal() and int(outcome["transportStatus"]) not in {0, 124, 137}, "ordered client did not finish with bounded explicit failure"
                assert outcome["adminCancellationMessage"], "ordered client cancellation missing; unknown disconnect requires diagnosis"
                assert len(receipts) == 1 and receipts[0] == ("true", "0", "false", "None"), "cooperative ordered accepted-tail RPC acknowledgement incomplete"
                assert not outcome["runtimeConfirmationWarningPresent"], "ordered runtime confirmation missing"
                assert all(not state["OOMKilled"] and state["ExitCode"] != 137 for state in outcome["containers"].values()), "ordered container OOM/SIGKILL"
            else:
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
            transport_status = run("cat /tmp/workload-status").strip()
            states = {role: json.loads(run("podman inspect --format '{{json .State}}' " + identifier))
                      for role, identifier in containers.items()}
            if acceptance_scope in {"terminal-delivery", "runtime-classification", "log-drain"}:
                runtime_log = run("podman logs --tail 200 " + containers["sandbox"] + " 2>&1")
                outcome = dict(scope=acceptance_scope, stopSeconds=round(elapsed, 3),
                               transportStatus=transport_status,
                               adminCancellationMessage="openshell: terminal delivery cancelled by administrative shutdown" in output,
                               termMarker="ACCEPT_TERM" in output, finalMarker="ACCEPT_FINAL" in output,
                               containers=states, runtimeBinding=runtime_binding, supervisorBinding=supervisor_binding,
                               runtimeConfirmationWarningPresent="before supervisor confirmation" in runtime_log,
                               fullGracefulShutdownProved=False, finalLogFlushProved=False)
                machine.succeed("printf %s " + shlex.quote(json.dumps(outcome)) + " > /tmp/terminal-delivery-outcome.json")
                machine.log("TERMINAL_DELIVERY " + json.dumps(outcome, sort_keys=True))
                if acceptance_scope in {"runtime-classification", "log-drain"}:
                    machine.succeed("printf %s " + shlex.quote(json.dumps(outcome)) + " > /tmp/runtime-classification-outcome.json")
                    assert all(state["ExitCode"] == 0 for state in states.values()), "runtime classification scope requires both container exits zero"
                    assert not outcome["runtimeConfirmationWarningPresent"], "runtime still reports unconfirmed supervisor termination"
                if acceptance_scope == "log-drain":
                    stage = "final-log-drain-receipt"
                    supervisor_log = run("podman logs --tail 200 " + containers["supervisor"] + " 2>&1")
                    final_marker = "Supervisor lifecycle completed; closing log push"
                    pattern = re.compile(r"openshell: log push shutdown LogPushOutcome \{ accepted_tail_acknowledged: (true|false), local_dropped_lines: ([0-9]+), prior_stream_delivery_uncertain: (true|false), incomplete: ([A-Za-z()]+) \}")
                    receipts = [match.groups() for line in supervisor_log.splitlines() if (match := pattern.fullmatch(line))]
                    gateway_logs = run("openshell logs shutdown-acceptance -n 200 --source sandbox", timeout=5)
                    machine.succeed("printf %s " + shlex.quote(gateway_logs) + " > /tmp/post-stop-gateway-sandbox.log")
                    outcome.update(localFinalMarkerCount=sum(final_marker in line for line in supervisor_log.splitlines()),
                                   liveGatewayFinalMarkerCount=sum(final_marker in line for line in gateway_logs.splitlines()),
                                   rpcReceiptCount=len(receipts), rpcReceipt=receipts[0] if len(receipts) == 1 else None,
                                   acceptedTailRpcProved=False, gatewayRestartDurabilityProved=False)
                    machine.succeed("printf %s " + shlex.quote(json.dumps(outcome)) + " > /tmp/log-drain-outcome.json")
                    machine.log("LOG_DRAIN " + json.dumps(outcome, sort_keys=True))
                    # Pinned console logging defaults to WARN; the independent push layer
                    # accepts INFO. Local INFO-marker count is diagnostic, not a drain gate.
                    assert outcome["liveGatewayFinalMarkerCount"] == 1, "unique final marker absent from fresh sandbox live gateway tail"
                    assert len(receipts) == 1 and receipts[0] == ("true", "0", "false", "None"), "accepted-tail RPC acknowledgement incomplete or prior loss observed"
                    outcome["acceptedTailRpcProved"] = True
                    machine.succeed("printf %s " + shlex.quote(json.dumps(outcome)) + " > /tmp/log-drain-outcome.json")
                assert transport_status.isdecimal() and int(transport_status) not in {0, 124, 137}, "administrative transport did not finish with explicit bounded failure"
                assert outcome["adminCancellationMessage"], "exact administrative cancellation message missing"
                assert all(not state["Running"] and state["ExitCode"] != 137 for state in states.values()), "container survived or required SIGKILL"
            else:
                assert transport_status == "0", "attached workload transport did not exit zero"
                for role, state in states.items():
                    assert not state["Running"], "fixture container survived: " + role
                    assert state["ExitCode"] == 0, "fixture forced/nonzero exit: " + role
            assert "ACCEPT_TERM" in output and "ACCEPT_FINAL" in output, "workload final markers missing"
            assert elapsed < 10, "cooperative ordinary stop exceeded ten seconds; preserve 45s fallback"
            machine.log("Ordinary stop scope " + acceptance_scope + " passed; full graceful shutdown and final log flush require their separate assertions")
finally:
    capture(stage, containers)
    machine.execute(user("test ! -f /tmp/shutdown-stream.pid || kill $(cat /tmp/shutdown-stream.pid)"), timeout=5)
    for name in ("shutdown-stream.log", "workload-stdout.log", "workload-status", "create-driver.log"):
        machine.execute("test ! -f /tmp/" + name + " || cp /tmp/" + name + " /tmp/shutdown-evidence/" + name, timeout=5)
    machine.copy_from_machine("/tmp/shutdown-evidence", "final")
