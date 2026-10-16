# NixOS driver only; all paths and systemd operations refer to the disposable guest.
import time
import json
import shlex

start_all()
root = "/var/lib/reservation-lifetime"
unit = "phoenix-reservation-lifetime.service"
def phase(name):
    print("reservation-phase=" + name + " elapsed=" + str(round(time.monotonic()-started, 2)), flush=True)

def management(operation, file=None, task=None, seconds=None, user="client", success=True):
    args = ["setpriv", "--reuid="+user, "--regid=users", "--init-groups", "phoenix-reservation"]
    if file: args += ["--capability-file", "/home/client/"+file+".json"]
    if task: args += ["--task", task, "--command", "deployment.test"]
    if seconds: args += ["--seconds", str(seconds)]
    args += [operation]
    status, output = machine.execute(shlex.join(args) + " </dev/null", timeout=8)
    assert (status == 0) == success, "management status mismatch: " + operation
    return json.loads(output) if success else None

started = time.monotonic()
try:
    machine.wait_for_unit("multi-user.target", timeout=30)
    machine.succeed(python + " -I " + helper + " setup")
    phase("packaged-management")
    machine.wait_for_unit("phoenix-admin.socket", timeout=10)
    first = management("acquire", "first", "first-task")
    second = management("acquire", "second", "second-task")
    assert first["state"] == "owned" and second["state"] == "queued"
    assert first["generation"] < second["generation"]
    management("status", user="outsider", success=False)
    machine.succeed(python + " -I " + helper + " spoof")
    machine.succeed(python + " -I " + helper + " bind")
    phase("mutation-client-loss")
    command = ("systemd-run --quiet --wait --collect --service-type=exec "
               "--property=RuntimeMaxSec=30 --property=TimeoutStopSec=5 --unit=" + unit + " "
               + python + " -I " + controller + " " + root + "/config.json activate-reserved " + "a" * 64)
    machine.succeed("(exec " + command + ") </dev/null >" + root + "/submit.log 2>&1 & echo $! >" + root + "/submit.pid")
    machine.wait_until_succeeds("test -f " + root + "/ready", timeout=15)
    machine.succeed("systemctl show -p MainPID -p ControlGroup -p RuntimeMaxUSec -p TimeoutStopUSec " + unit + " >" + root + "/unit-before.log")
    # Verify exec removed the wrapper and the service has a distinct owner PID.
    submit_pid = machine.succeed("cat " + root + "/submit.pid").strip()
    assert submit_pid.isdigit()
    assert machine.succeed("cat /proc/" + submit_pid + "/comm").strip() == "systemd-run"
    service_pid = machine.succeed("systemctl show -p MainPID --value " + unit).strip()
    assert service_pid.isdigit() and int(service_pid) > 1 and service_pid != submit_pid
    # Kill only the submitting systemd-run client, never the service/helper.
    machine.succeed("kill -KILL $(cat " + root + "/submit.pid)")
    machine.succeed("systemctl is-active " + unit)
    machine.fail(python + " -I " + controller + " " + root + "/config.json activate-reserved " + "b" * 64 + " >" + root + "/competitor.log 2>&1", timeout=5)
    machine.succeed("grep -Fq 'DeploymentFailure: activation: mutation-still-running' " + root + "/competitor.log")
    machine.succeed("test ! -f " + root + "/finished && kill -0 $(cat " + root + "/ready)")
    phase("renew-expiry-with-held-gate")
    management("renew", "first", seconds=2)
    assert management("status")["owners"]
    time.sleep(2.2)
    promoted = management("poll", "second")
    assert promoted["state"] == "owned"
    machine.succeed(python + " -I " + helper + " bind-second")
    management("renew", "first", seconds=2, success=False)
    # Expiry has not killed/rolled back the recorder or released its kernel gate.
    machine.succeed("systemctl is-active " + unit + " && test ! -f " + root + "/finished")
    machine.fail(python + " -I " + controller + " " + root + "/config.json activate-reserved " + "b" * 64 + " >" + root + "/competitor.log 2>&1", timeout=5)
    machine.succeed("grep -Fq 'mutation-still-running' " + root + "/competitor.log")
    machine.succeed("touch " + root + "/release")
    machine.wait_until_succeeds("test -f " + root + "/descendant-done && test -f " + root + "/finished && ! systemctl is-active --quiet " + unit, timeout=10)
    phase("runtime-lease-recovery")
    # Expiry promoted task two without releasing its lease at recorder completion.
    # Recovery revokes that exact generation before a fresh task enters.
    assert management("status")["owners"][0]["generation"] == second["generation"]
    machine.succeed(python + " -I " + helper + " recover")
    assert not management("status")["owners"]
    management("poll", "second", success=False)
    machine.succeed("rm /home/client/first.json")
    assert management("acquire", "first", "fresh-task")["state"] == "owned"
    machine.succeed(python + " -I " + helper + " bind")
    machine.succeed(python + " -I " + controller + " " + root + "/config.json activate-reserved " + "a" * 64, timeout=8)
    assert management("status")["owners"], "successful mutation released runtime lease"
    machine.succeed(python + " -I " + helper + " probe")
    machine.succeed(python + " -I " + helper + " timeout", timeout=5)
    time.sleep(1)
    machine.succeed("test -f " + root + "/gate-free && test -f " + root + "/timeout-returned && test ! -f " + root + "/escaped")
    machine.succeed(python + " -I " + helper + " probe")
    phase("disruption-real-manager")
    management("renew", "first", seconds=60)
    machine.succeed("systemctl start user@1000.service", timeout=15)
    machine.succeed("systemctl --user --machine=client@.host start kando.service", timeout=10)
    for case in ("unchanged", "changed", "unsupported"):
        machine.succeed(python + " -I " + helper + " disruption-" + case, timeout=15)
    machine.succeed("systemctl stop user@1000.service", timeout=15)
    management("release", "first")
    assert not management("status")["owners"]
    machine.succeed(python + " -I " + helper + " audit")
    phase("passed")
finally:
    machine.execute("journalctl -b --no-pager -u " + unit + " > /tmp/reservation-lifetime-journal.log", timeout=10)
    machine.copy_from_machine("/tmp/reservation-lifetime-journal.log", "evidence")
    # Never export capability/config/envelope contents.
    for name in ("unit-before.log", "submit.log", "competitor.log"):
        status, _ = machine.execute("test -f " + root + "/" + name + " && cp " + root + "/" + name + " /tmp/" + name, timeout=5)
        if status == 0:
            machine.copy_from_machine("/tmp/" + name, "evidence")
