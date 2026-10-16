# On-demand review-enabled socket composition; OS/model boundaries are explicit doubles.
{ pkgs }:
let
  authorization = pkgs.writeText "peer-authorization.py" (builtins.readFile ../authorization/request.py);
  transport = pkgs.writeText "peer-transport.json" (builtins.readFile ../transport.json);
  controller = pkgs.replaceVars ../deployment.py { authorizationLibrary = toString authorization; deploymentTransportPolicy = toString transport; };
  review = pkgs.replaceVars ../deploy-review.py { authorizationLibrary = toString authorization; deploymentTransportPolicy = toString transport; };
  source = pkgs.runCommand "source" { } ''
    mkdir -p $out
    echo '{}' > $out/flake.nix
    echo '{}' > $out/flake.lock
  '';
  closure = pkgs.runCommand "nixos-system-peer-recorder" { } ''
    mkdir -p $out/bin $out/etc/phoenix-agent
    ln -s ${source} $out/etc/phoenix-agent/activated-source
    ln -s ${pkgs.coreutils}/bin/true $out/bin/switch-to-configuration
  '';
  descriptor = pkgs.writeText "deployment-peer.json" (builtins.toJSON {
    inherit controller review source closure;
  });
  command = "${pkgs.python3}/bin/python3 -I ${./deployment-peer.py} ${descriptor}";
in pkgs.testers.runNixOSTest {
  name = "phoenix-deployment-peer";
  globalTimeout = 120;
  nodes.machine = { ... }: {
    virtualisation = { cores = 2; memorySize = 2048; diskSize = 2048; };
    users.groups.peer-probes = { };
    users.users = builtins.listToAttrs (map (entry: {
      name = entry.name;
      value = { isNormalUser = true; uid = entry.uid; extraGroups = [ "peer-probes" ]; };
    }) [ { name = "client"; uid = 1000; } { name = "operator"; uid = 1001; }
         { name = "updater"; uid = 1002; } { name = "builder"; uid = 1003; }
         { name = "reviewer"; uid = 1004; } { name = "outsider"; uid = 1005; } ]);
    environment.systemPackages = [ pkgs.util-linux ];
    environment.etc."phoenix-agent/activated-source".source = source;
    systemd.sockets.peer-fixture = {
      wantedBy = [ "sockets.target" ];
      socketConfig = { ListenStream = "/run/peer-fixture/control.sock"; SocketMode = "0660"; SocketUser = "client"; SocketGroup = "peer-probes"; DirectoryMode = "0755"; };
    };
    systemd.services.peer-fixture = {
      requires = [ "peer-fixture.socket" ];
      after = [ "peer-fixture.socket" ];
      serviceConfig = { ExecStart = command + " serve"; User = "root"; UMask = "0077"; };
    };
  };
  testScript = ''
    import json
    start_all()
    machine.wait_for_unit("peer-fixture.socket")
    def request(user, case):
        command = "setpriv --reuid=" + user + " --regid=users --init-groups ${command} client " + case
        return json.loads(machine.succeed(command, timeout=10))
    try:
        for user in ("client", "operator"):
            assert request(user, "metadata")["decision"] == "security-review"
        assert request("outsider", "metadata").get("ok") is False
        assert request("operator", "allow").get("ok") is False
        assert request("updater", "allow").get("ok") is False
        assert json.loads(machine.succeed("cat /var/lib/peer-fixture/counts.json")) == {"review": 0, "activation": 0}
        for number, (case, code) in enumerate((("error", "review-invocation-failed"), ("deny", "model-denied")), 1):
            result = request("client", case)
            assert result.get("ok") is False and result.get("code") == code
            counts = json.loads(machine.succeed("cat /var/lib/peer-fixture/counts.json"))
            assert counts == {"review": number, "activation": 0}
        assert request("client", "allow")["ok"] is True
        counts = json.loads(machine.succeed("cat /var/lib/peer-fixture/counts.json"))
        assert counts == {"review": 3, "activation": 1}
        journal = machine.succeed("journalctl -u peer-fixture.service --no-pager")
        assert any('"uid": 1005' in line and '"code": "invalid-or-denied"' in line for line in journal.splitlines())
    finally:
        machine.succeed("journalctl -u peer-fixture.service --no-pager > /tmp/peer-fixture-journal.log")
        machine.copy_from_machine("/tmp/peer-fixture-journal.log", "evidence")
        status, _ = machine.execute("test -f /var/lib/peer-fixture/counts.json && cp /var/lib/peer-fixture/counts.json /tmp/peer-counts.json")
        if status == 0: machine.copy_from_machine("/tmp/peer-counts.json", "evidence")
  '';
}
