# Pass the evaluated production notifier serviceConfig: namespace settings must
# come from the installed module, not a second copy of its sandbox policy.
{ pkgs, notifierServiceConfig }:
let
  user = notifierServiceConfig.User;
  address = notifierServiceConfig.Environment;
  match = builtins.match "DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/([0-9]+)/bus" address;
  uid = assert match != null; builtins.fromJSON (builtins.head match);
  runtime = "/run/user/${toString uid}";
  probe = pkgs.writeText "notification-namespace.py" ''
    import os
    import socket
    import stat
    import sys

    path = "${runtime}/bus"
    if sys.argv[1] == "server":
        with open("${runtime}/hidden-sentinel", "w") as marker:
            marker.write("must remain outside notifier namespace")
        with socket.socket(socket.AF_UNIX) as listener:
            listener.bind(path)
            listener.listen(1)
            listener.settimeout(60)
            connection, _ = listener.accept()
            with connection:
                connection.settimeout(5)
                assert connection.recv(16) == b"namespace-probe"
                connection.sendall(b"socket-visible")
    else:
        assert not os.path.exists("${runtime}/hidden-sentinel"), "runtime sibling exposed"
        assert stat.S_ISSOCK(os.stat(path).st_mode), "session socket hidden"
        with socket.socket(socket.AF_UNIX) as connection:
            connection.settimeout(5)
            connection.connect(path)
            connection.sendall(b"namespace-probe")
            assert connection.recv(16) == b"socket-visible"
        print("notifier namespace round trip passed", flush=True)
  '';
in pkgs.testers.runNixOSTest {
  name = "phoenix-update-notification-namespace";
  globalTimeout = 150;
  nodes.machine = {
    virtualisation = { cores = 1; memorySize = 1024; };
    users.users.${user} = { isNormalUser = true; inherit uid; };
    systemd.tmpfiles.rules = [ "d ${runtime} 0700 ${user} users -" ];
    systemd.services.notification-socket = {
      serviceConfig = {
        Type = "simple";
        User = user;
        Group = "users";
        ExecStart = "${pkgs.python3}/bin/python3 -I ${probe} server";
        RuntimeMaxSec = 70;
      };
    };
    systemd.services.notification-probe.serviceConfig = notifierServiceConfig // {
      ExecStart = "${pkgs.python3}/bin/python3 -I ${probe} client";
      TimeoutStartSec = 15;
    };
  };
  testScript = ''
    machine.start()
    machine.wait_for_unit("multi-user.target")
    machine.succeed("systemctl start notification-socket.service", timeout=15)
    machine.wait_until_succeeds("test -S ${runtime}/bus", timeout=15)
    machine.succeed("test -f ${runtime}/hidden-sentinel")
    machine.succeed("systemctl start notification-probe.service", timeout=20)
    machine.succeed("journalctl -u notification-probe.service --no-pager | grep -F 'notifier namespace round trip passed'")
    machine.succeed("test -f ${runtime}/hidden-sentinel")
  '';
}
