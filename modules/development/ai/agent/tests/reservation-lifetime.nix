# On-demand isolated systemd/guard lifetime test; no host activation or model.
{ pkgs }:
let
  source = pkgs.runCommand "source" { } ''
    mkdir -p $out
    echo 'Synthetic guest provenance for lifetime acceptance.' > $out/README.md
  '';
  authorization = pkgs.writeText "reservation-authorization.py" (builtins.readFile ../authorization/request.py);
  transport = pkgs.writeText "reservation-transport.json" (builtins.readFile ../transport.json);
  engine = pkgs.writeText "reservation-engine.py" (builtins.readFile ../reservations.py);
  adapter = pkgs.writeText "reservation-management.py" (builtins.readFile ../reservation-client.py);
  controller = pkgs.replaceVars ../deployment.py {
    deploymentTransportPolicy = toString transport;
    authorizationLibrary = toString authorization;
  };
  recorder = pkgs.writeScript "reservation-recorder" ''
    #!${pkgs.python3}/bin/python3
    import os
    from pathlib import Path
    import time
    root = Path('/var/lib/reservation-lifetime')
    child = os.fork()
    if child == 0:
        (root / 'ready').write_text(str(os.getpid()))
        while not (root / 'release').exists(): time.sleep(.02)
        (root / 'descendant-done').touch()
        os._exit(0)
    _, status = os.waitpid(child, 0)
    if status: raise SystemExit(1)
    (root / 'finished').touch()
  '';
  closure = pkgs.runCommand "nixos-system-reservation-fixture" { } ''
    mkdir -p $out/bin $out/etc/phoenix-agent
    ln -s ${recorder} $out/bin/switch-to-configuration
    ln -s ${source} $out/etc/phoenix-agent/activated-source
  '';
  helper = pkgs.writeText "reservation-lifetime-helper.py" ''
    import contextlib, importlib.util, json, os, subprocess, sys
    from pathlib import Path
    def load(name, path):
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        return module
    deploy = load('deployment', '${controller}')
    management = load('management', '${adapter}')
    root = Path('/var/lib/reservation-lifetime')
    config = dict(target='metal', baseline='/etc/phoenix-agent/activated-source',
        activationSpool=str(root / 'spool'), activationLock=str(root / 'activation.lock'),
        activationEnvironment={}, reservations=dict(engine='${engine}',
        adapter='${adapter}', state=str(root / 'state'),
        mapping=load('engine', '${engine}').DEFAULT_MAPPING, bounds={}))
    if sys.argv[1] == 'setup':
        deploy.store_path('${source}', 'source')
        deploy.store_path('${closure}', 'closure')
        deploy.activation_executable('${closure}')
        root.mkdir(mode=0o700); (root / 'spool').mkdir(mode=0o700)
        profile = Path('/nix/var/nix/profiles/system')
        if not profile.exists():
            profile.parent.mkdir(parents=True, exist_ok=True)
            profile.symlink_to(Path('/run/current-system').resolve(strict=True))
        manager = management.Management(config['reservations'])
        ticket = manager.engine.acquire(1000, 'lifetime-fixture', 'deployment.test', manager.engine.baseline())
        capability = {key: ticket[key] for key in ('generation', 'capability')}
        (root / 'ticket.json').write_text(json.dumps(capability)); (root / 'ticket.json').chmod(0o600)
        (root / 'config.json').write_text(json.dumps(config)); (root / 'config.json').chmod(0o600)
        for nonce in ('a' * 64, 'b' * 64):
            binding = dict(nonce=nonce, target='metal', action='test', closure='${closure}', source='${source}',
                base='${source}', profile=str(profile.resolve(strict=True)), profileSource='${source}',
                reservation=capability, reservationUid=1000)
            envelope = root / 'spool' / (nonce + '.json')
            envelope.write_text(json.dumps(binding)); envelope.chmod(0o600)
    else:
        manager = management.Management(config['reservations'])
        capability = json.loads((root / 'ticket.json').read_text())
        with deploy.activation_guard(config) as guard, manager.engine.operation(1000, command='deployment.test', **capability) as operation:
            if sys.argv[1] == 'timeout':
                code = "import os,time,pathlib; child=os.fork(); time.sleep(.8 if child == 0 else 5); pathlib.Path('/var/lib/reservation-lifetime/escaped').touch()"
                try:
                    operation.run_child(['${pkgs.python3}/bin/python3', '-c', code], timeout=.15, guard_fds=(guard,))
                except subprocess.TimeoutExpired:
                    (root / 'timeout-returned').touch()
                else: raise AssertionError('timeout missing')
            elif sys.argv[1] == 'probe': (root / 'gate-free').touch()
            else: raise AssertionError('unsupported fixed fixture mode')
  '';
  runtimeInputs = pkgs.runCommand "reservation-runtime-import-check" { nativeBuildInputs = [ pkgs.python3 ]; } ''
    python3 -I - <<'PYTHON'
    import importlib.util
    for name, path in [('controller', '${controller}'), ('engine', '${engine}'), ('management', '${adapter}')]:
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    PYTHON
    touch $out
  '';
in
assert pkgs.lib.hasSuffix "-source" (toString source);
assert pkgs.lib.hasSuffix "-nixos-system-reservation-fixture" (toString closure);
pkgs.testers.runNixOSTest {
  name = "phoenix-reservation-lifetime";
  globalTimeout = 120;
  nodes.machine = { ... }: {
    virtualisation = { cores = 2; memorySize = 2048; diskSize = 2048; };
    system.extraDependencies = [ runtimeInputs ];
    environment.etc."phoenix-agent/activated-source".source = source;
    environment.systemPackages = [ pkgs.python3 ];
  };
  testScript = ''
    python = "${pkgs.python3}/bin/python3"
    helper = "${helper}"
    controller = "${controller}"
  '' + builtins.readFile ./reservation-lifetime-driver.py;
}
