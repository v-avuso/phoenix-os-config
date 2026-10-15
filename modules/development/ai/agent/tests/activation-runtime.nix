# On-demand actual guest activation/rollback. No host activation, reviewer or auth.
{ pkgs }:
let
  source = pkgs.runCommand "source" { } ''
    mkdir -p $out
    echo 'Synthetic guest-only activation provenance.' > $out/README.md
  '';
  authorization = pkgs.writeText "activation-authorization.py" (builtins.readFile ../authorization/request.py);
  transport = pkgs.writeText "activation-transport.json" (builtins.readFile ../transport.json);
  controller = pkgs.replaceVars ../deployment.py {
    authorizationLibrary = toString authorization;
    deploymentTransportPolicy = toString transport;
  };
  review = pkgs.replaceVars ../deploy-review.py {
    authorizationLibrary = toString authorization;
    deploymentTransportPolicy = toString transport;
  };
  runtimeInputs = pkgs.runCommand "activation-runtime-import-check" { nativeBuildInputs = [ pkgs.python3 ]; } ''
    python3 -I - <<'PYTHON'
    import importlib.util
    for name, path in [('controller', '${controller}'), ('review', '${review}')]:
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    PYTHON
    touch $out
  '';
in pkgs.testers.runNixOSTest {
  name = "phoenix-activation-runtime";
  globalTimeout = 180;
  nodes.machine = { lib, ... }: {
    virtualisation = { cores = 2; memorySize = 2048; diskSize = 2048; };
    system.switch.enable = true;
    system.extraDependencies = [ runtimeInputs ];
    environment.etc."phoenix-agent/activated-source".source = source;
    environment.etc."activation-runtime-marker".text = "base\n";
    specialisation.good.configuration = {
      environment.etc."activation-runtime-marker".text = lib.mkForce "good\n";
    };
    specialisation.failing.configuration = {
      environment.etc."activation-runtime-marker".text = lib.mkForce "failing\n";
      # A real activation error after /etc changed; ERR records nonzero and the
      # normal activation tail still runs. Production activate() must roll back.
      system.activationScripts.fixtureFailure = {
        deps = [ "etc" ];
        text = ''
          mkdir -p /var/lib/activation-runtime
          cat /etc/activation-runtime-marker > /var/lib/activation-runtime/failure-observed
          false
        '';
      };
    };
  };
  testScript = ''
    python = "${pkgs.python3}/bin/python3"
    controller = "${controller}"
    review = "${review}"
    source = "${source}"
    activation_environment = {
      "PATH": "/run/current-system/sw/bin:/run/current-system/sw/sbin",
      "HOME": "/root",
      "LOCALE_ARCHIVE": "${pkgs.glibcLocales}/lib/locale/locale-archive",
    }
  '' + builtins.readFile ./activation-runtime-driver.py;
}
