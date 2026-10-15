# On demand only: rootless Podman smoke, not OpenShell shutdown acceptance.
# Pass pkgs from the repository's locked nixpkgs; do not register in flake checks.
{ pkgs }:
let
  image = pkgs.dockerTools.buildImage {
    name = "localhost/phoenix-shutdown-smoke";
    tag = "fixture";
    copyToRoot = pkgs.busybox;
    config.Cmd = [ "/bin/sh" ];
  };
in
pkgs.testers.runNixOSTest {
  name = "phoenix-shutdown-smoke";
  nodes.machine = { pkgs, ... }: {
    virtualisation = {
      cores = 2;
      memorySize = 4096;
      diskSize = 4096;
      podman.enable = true;
    };
    users.users.fixture = {
      isNormalUser = true;
      uid = 1000;
      autoSubUidGidRange = true;
    };
    services.journald.extraConfig = "Storage=persistent";
    environment.systemPackages = [ pkgs.procps ];
  };
  testScript = ''
    import shlex

    def user(command):
        return "su fixture -l -c " + shlex.quote(command)

    start_all()
    machine.wait_for_unit("multi-user.target")
    machine.succeed("loginctl enable-linger fixture")
    machine.wait_for_unit("user@1000.service")
    machine.succeed(user("systemctl --user is-system-running --wait"))
    machine.log("systemd: " + machine.succeed("systemctl --version").splitlines()[0])
    machine.log("Podman: " + machine.succeed(user("podman --version")).strip())
    machine.succeed(user("podman load --input ${image}"))
    command = "trap 'exit 0' TERM; echo SMOKE_READY; while :; do sleep 1; done"
    machine.succeed(user("podman run --pull=never --name smoke -d localhost/phoenix-shutdown-smoke:fixture /bin/sh -c " + shlex.quote(command)))
    machine.succeed(user("test $(podman inspect --format '{{.State.Running}}' smoke) = true"))
    machine.wait_until_succeeds(user("podman logs smoke | grep -qx SMOKE_READY"), timeout=20)
    machine.succeed(user("podman stop --time 10 smoke"), timeout=20)
    machine.succeed(user("test $(podman inspect --format '{{.State.Status}}' smoke) = exited"))
    machine.succeed(user("test $(podman inspect --format '{{.State.ExitCode}}' smoke) = 0"))
    machine.succeed(user("podman rm smoke"))
    machine.succeed(user('test -z "$(podman ps -aq)"'))
    machine.wait_until_succeeds("! pgrep -u 1000 -x conmon", timeout=10)
    machine.succeed("systemctl is-active user@1000.service")
    machine.succeed("journalctl --sync")
    machine.succeed("journalctl -b --no-pager -u user@1000.service")
  '';
}
