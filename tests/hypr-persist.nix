# Run: nix build --impure --file tests/hypr-persist.nix --no-link
# Builds the package (including upstream/mock IPC tests) and checks declarations;
# does not run its daemon, install state, or alter user services.
# Stage task files before evaluating: use the Git source, excluding ignored data.
let
  flake = builtins.getFlake ("git+file://" + toString ../.);
  pkgs = flake.inputs.nixpkgs.legacyPackages.x86_64-linux;
  user = import ../config/user.nix { inherit (pkgs) lib; };
  metal = flake.nixosConfigurations.metal.config.home-manager.users.${user.name};
  vm = flake.nixosConfigurations.vm.config.home-manager.users.${user.name};
  unit = metal.systemd.user.services.hypr-persist;
  package = builtins.head (
    builtins.filter (p: (p.pname or "") == "hypr-persist") metal.home.packages
  );
  configPath = builtins.elemAt (pkgs.lib.splitString " --config " (builtins.head unit.Service.ExecStart)) 1;
  baseline = metal.xdg.dataFile."caelestia/shell.json.nix-baseline".source;
in
assert !(vm.systemd.user.services ? hypr-persist);
assert unit.Unit.PartOf == [ "hyprland-session.target" ];
assert unit.Unit.BindsTo == [ "hyprland-session.target" ];
assert unit.Unit.After == [ "hyprland-session.target" ];
assert unit.Unit.ConditionEnvironment == "HYPRLAND_INSTANCE_SIGNATURE";
assert unit.Install.WantedBy == [ "hyprland-session.target" ];
assert unit.Service.UMask == "0077";
assert unit.Service.Restart == "no";
assert unit.Service.TimeoutStopSec == 30;
assert !(unit.Service ? ExecStop);
assert pkgs.lib.hasInfix "/bin/install -d -m 0700 " unit.Service.ExecStartPre;
assert package.doCheck;
pkgs.runCommand "phoenix-hypr-persist-check" { nativeBuildInputs = [ pkgs.python3 ]; } ''
    ${package}/bin/hypr-persist --help > /dev/null
    python3 - ${configPath} ${baseline} <<'PY'
  import json, pathlib, re, sys, tomllib
  settings = tomllib.loads(pathlib.Path(sys.argv[1]).read_text())
  assert settings['general'] == {
      'save_interval': 120,
      'session_dir': '${metal.xdg.stateHome}/phoenix-hypr-persist',
      'restore_on_start': True,
      'per_window_launch': True,
      'restore_geometry': True,
      'restore_layout': False,
  }
  assert settings['overrides'] == {
      'codex-desktop': '/run/current-system/sw/bin/codex-desktop',
      'codex-desktop-sandboxed': '/run/current-system/sw/bin/codex-desktop-sandboxed',
  }
  exclusions = [re.compile(x) for x in settings['rules']['exclude']]
  for app in ('codex-desktop', 'codex-desktop-sandboxed', 'firefox', 'org.mozilla.firefox'):
      assert not any(x.search(app) for x in exclusions), app
  for helper in ('hyprpicker', 'quickshell', 'xdg-desktop-portal-gtk', 'org.kde.polkit-kde-authentication-agent-1'):
      assert any(x.search(helper) for x in exclusions), helper
  baseline = json.loads(pathlib.Path(sys.argv[2]).read_text())
  logout = baseline['session']['commands']['logout']
  assert logout[1] == 'dispatch'
  script_path = re.fullmatch(r"hl\.dsp\.exec_cmd\('([^']+)'\)", logout[2])[1]
  script = pathlib.Path(script_path).read_text()
  assert script.index('systemctl --user stop hypr-persist.service') < script.index('exec ')
  assert 'hyprshutdown --vt 1' in script
  assert '|| exit $?' in script
  assert script.count('hypr-persist') == 1
  print('hypr-persist declarations, exclusions, containment and logout ordering passed')
  PY
    touch "$out"
''
