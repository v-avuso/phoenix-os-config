# NixOS driver only; all paths and systemd operations refer to the disposable guest.
import time

start_all()
root = "/var/lib/reservation-lifetime"
unit = "phoenix-reservation-lifetime.service"
try:
    machine.wait_for_unit("multi-user.target", timeout=30)
    machine.succeed(python + " -I " + helper + " setup")
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
    machine.succeed("touch " + root + "/release")
    machine.wait_until_succeeds("test -f " + root + "/descendant-done && test -f " + root + "/finished && ! systemctl is-active --quiet " + unit, timeout=10)
    machine.succeed(python + " -I " + helper + " probe")
    machine.succeed(python + " -I " + helper + " timeout", timeout=5)
    time.sleep(1)
    machine.succeed("test -f " + root + "/gate-free && test -f " + root + "/timeout-returned && test ! -f " + root + "/escaped")
    machine.succeed(python + " -I " + helper + " probe")
finally:
    machine.execute("journalctl -b --no-pager -u " + unit + " > /tmp/reservation-lifetime-journal.log", timeout=10)
    machine.copy_from_machine("/tmp/reservation-lifetime-journal.log", "evidence")
    # Never export capability/config/envelope contents.
    for name in ("unit-before.log", "submit.log", "competitor.log"):
        status, _ = machine.execute("test -f " + root + "/" + name + " && cp " + root + "/" + name + " /tmp/" + name, timeout=5)
        if status == 0:
            machine.copy_from_machine("/tmp/" + name, "evidence")
