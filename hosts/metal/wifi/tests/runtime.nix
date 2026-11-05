# Disposable root/tracefs roundtrip; no host tracing or activation.
let
  flake = builtins.getFlake ("git+file://" + toString ../../../..);
  host = flake.nixosConfigurations.metal;
  pkgs = host.pkgs;
  collector = pkgs.writeText "wifi-diagnostics.py" (builtins.readFile ../diagnostics.py);
  trial = pkgs.writeText "wifi-runtime.py" (builtins.readFile ./runtime.py);
in
pkgs.testers.runNixOSTest {
  name = "phoenix-wifi-trace";
  nodes.machine = { ... }: {
    boot.kernelModules = [
      "mac80211_hwsim"
      "ath12k"
    ];
    users.groups.phoenix-wifi-diagnostics = { };
    systemd.services.wifi-trace-fixture.serviceConfig =
      host.config.systemd.services.phoenix-wifi-diagnostics.serviceConfig
      // {
        Type = "oneshot";
        ExecStart = "${pkgs.python3}/bin/python3 ${trial} ${collector} ${pkgs.kmod}/bin/modprobe";
        ExecStopPost = "";
      };
    virtualisation.memorySize = 1024;
  };
  testScript = ''
    machine.start()
    machine.wait_for_unit("multi-user.target")
    machine.succeed("systemctl start wifi-trace-fixture.service")
    machine.succeed("test $(stat -c %a /var/lib/phoenix-wifi-diagnostics) = 750")
  '';
}
