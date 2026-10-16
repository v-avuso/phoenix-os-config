# On-demand disposable guest proof; model/auth are explicit doubles, no host changes.
{ pkgs }:
let
  library = pkgs.writeText "command-policy.py" (builtins.readFile ../command-policy.py);
  auth = pkgs.writeText "authorization.py" (builtins.readFile ../request.py);
  controller = pkgs.replaceVars ../../deployment.py {
    authorizationLibrary = toString auth;
    deploymentTransportPolicy = toString (pkgs.writeText "transport.json" (builtins.readFile ../../transport.json));
  };
  probe = pkgs.runCommandCC "command-probe" { } ''
    mkdir -p "$out/bin"
    cat > probe.c <<'C'
    #include <unistd.h>
    #include <stdio.h>
    #include <string.h>
    int main(int argc,char **argv) {
      if(argc>1 && !strcmp(argv[1],"fork")) {
        if(!fork()){setsid();sleep(3);FILE*f=fopen("/tmp/escaped-command","w");if(f){fputs("escape",f);fclose(f);}return 0;}
        sleep(20);return 0;
      }
      fputs("PRIVATE_CANARY",stdout);
      int n=argc>1&&!strcmp(argv[1],"flood")?65537:4096;
      for(int i=0;i<n;i++) putchar(0);
      return 0;
    }
    C
    $CC probe.c -o "$out/bin/probe"
  '';
  entry = mode: { executable = "${pkgs.coreutils}/bin/id"; arguments = [ "-u" ]; rationale = "Read fixed root UID in disposable guest"; inherit mode; timeout = 2; };
  commands = { enable = true; entries = {
    identity = entry "automatic";
    reviewed = entry "review";
    denied = entry "review";
    error = entry "review";
    wrong = entry "review";
    timeout-review = entry "review";
    human = entry "human";
    slow = { executable = "${probe}/bin/probe"; arguments = [ "fork" ]; rationale = "Disposable descendant cleanup probe"; mode = "automatic"; timeout = 1; };
    flood = { executable = "${probe}/bin/probe"; arguments = [ "flood" ]; rationale = "Disposable output overflow probe"; mode = "automatic"; timeout = 2; };
    controls = { executable = "${probe}/bin/probe"; arguments = [ ]; rationale = "Disposable control-byte response probe"; mode = "automatic"; timeout = 2; };
  }; };
  authority = pkgs.writeText "command-authority.json" (builtins.toJSON { registry = commands; implementation = builtins.hashString "sha256" (builtins.readFile ../command-policy.py); });
  replacement = pkgs.writeText "revoked-command-authority.json" ''{"registry":{"enable":false,"entries":{}}}'';
  authPolicy = pkgs.writeText "authorization-policy.json" (builtins.toJSON {
    version = 1; securityReviewEnabled = true; clientUid = 1000; operatorUid = 1001; updaterUid = 1002; target = "vm";
    diagnostics = builtins.listToAttrs (map (n: { name = "admin.${n}"; value = "automatic"; }) [ "kernel-journal" "dmesg" "trace-summary" "trace-format" "service-status" "wakeup-get" "wakeup-set" ]);
    wakeupDevices = [ ]; statusServices = [ ];
  });
  settings = pkgs.writeText "command-root-config.json" (builtins.toJSON {
    inherit commands;
    commandLibrary = toString library;
    commandAuthority = toString authority;
    commandCurrentAuthority = "/etc/phoenix-command-authority";
    commandState = "/var/lib/command-state";
    commandExec = toString (pkgs.writeText "command-exec.py" (builtins.readFile ../command-exec.py));
    authorizationPolicy = toString authPolicy;
    clientUid = 1000; operatorUid = 1001; modelReviewEnabled = true;
    model = "gpt-6-luna"; effort = "high";
    python = "${pkgs.python3}/bin/python3";
    setpriv = "${pkgs.util-linux}/bin/setpriv";
    systemdRun = "${pkgs.systemd}/bin/systemd-run";
    systemctl = "${pkgs.systemd}/bin/systemctl";
    controller = toString controller;
    work = "/var/lib/command-work";
    reviewerUser = "command-review"; reviewHome = "/var/lib/command-review";
    reviewScript = toString (pkgs.writeText "command-review-fixture.py" (builtins.readFile ./command-review-fixture.py));
    commandReviewPolicy = toString (pkgs.writeText "command-review-policy.md" (builtins.readFile ../command-review-policy.md));
  });
in pkgs.testers.runNixOSTest {
  name = "phoenix-command-root";
  globalTimeout = 180;
  nodes.machine = { ... }: {
    virtualisation.memorySize = 2048;
    virtualisation.cores = 2;
    users.users.command-client = { isNormalUser = true; uid = 1000; };
    users.users.command-operator = { isNormalUser = true; uid = 1001; };
    users.users.command-review = { isSystemUser = true; uid = 2000; group = "users"; };
    environment.etc."phoenix-command-authority".source = authority;
    environment.etc."command-root-test.py".source = ./command-root.py;
    systemd.tmpfiles.rules = [ "d /var/lib/command-state 0700 root root -" "d /var/lib/command-work 0711 root root -" "d /var/lib/command-review 0700 command-review users -" ];
    systemd.sockets.command-root = { wantedBy = [ "sockets.target" ]; socketConfig = { ListenStream = "/run/command-root.sock"; SocketMode = "0666"; }; };
    systemd.services.command-root = { requires = [ "command-root.socket" ]; serviceConfig = { ExecStart = "${pkgs.python3}/bin/python3 -I ${controller} ${settings} serve"; StandardOutput = "journal"; }; };
    environment.systemPackages = [ pkgs.python3 ];
  };
  testScript = ''
    machine.start()
    machine.wait_for_unit("multi-user.target")
    machine.succeed("python3 /etc/command-root-test.py ${settings} ${replacement}")
    machine.succeed("journalctl -u command-root.service --no-pager > /tmp/command-root-journal")
    machine.fail("grep -F PRIVATE_CANARY /tmp/command-root-journal")
    machine.succeed("journalctl -t phoenix-authorization --output=cat --no-pager > /tmp/command-audit")
    machine.succeed("grep -F 'command.identity' /tmp/command-audit && grep -F 'Bounded disposable proof' /tmp/command-audit && grep -F 'review-cache' /tmp/command-audit && grep -F 'critical-override' /tmp/command-audit")
    machine.fail("grep -F PRIVATE_CANARY /tmp/command-audit")
    machine.copy_from_vm("/tmp/command-root-proof.json", "evidence")
  '';
}
