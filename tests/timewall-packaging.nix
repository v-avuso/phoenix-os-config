# Run: nix build --impure --file tests/timewall-packaging.nix --no-link
let
  flake = builtins.getFlake ("git+file://" + toString ../.);
  pkgs = flake.inputs.nixpkgs.legacyPackages.x86_64-linux;
  user = import ../config/user.nix { inherit (pkgs) lib; };
  home = flake.nixosConfigurations.metal.config.home-manager.users.${user.name};
  vmHome = flake.nixosConfigurations.vm.config.home-manager.users.${user.name};
  service = home.systemd.user.services.phoenix-timewall;
  theme = home.systemd.user.services.phoenix-timewall-theme;
  configFile = home.xdg.configFile."timewall/config.toml".source;
  cli = home.programs.caelestia.cli.package;
  timewall = flake.inputs.timewall.packages.x86_64-linux.default;
in
assert !(vmHome.systemd.user.services ? phoenix-timewall);
assert service.Service.RuntimeDirectory == "phoenix-timewall";
assert service.Service.RuntimeDirectoryMode == "0700";
assert builtins.elem "TIMEWALL_RUNTIME_DIR=%t/phoenix-timewall" service.Service.Environment;
assert service.Service.Restart == "no";
assert theme.Service.Type == "oneshot";
assert home.systemd.user.timers.phoenix-timewall-theme-light.Timer.OnCalendar == "*-*-* 07:00:00";
assert home.systemd.user.timers.phoenix-timewall-theme-dark.Timer.OnCalendar == "*-*-* 20:00:00";
pkgs.runCommand "phoenix-timewall-check"
  {
    nativeBuildInputs = [ pkgs.python3 ];
  }
  ''
      test -x ${cli}/bin/caelestia
      test -x ${timewall}/bin/timewall
      python3 - ${configFile} ${cli}/bin/caelestia <<'PY'
    import os, pathlib, sys, tomllib
    config = tomllib.loads(pathlib.Path(sys.argv[1]).read_text())
    assert config['daemon']['update_interval_seconds'] == 600
    assert config['geoclue']['enable'] is False
    argv = config['setter']['command']
    assert argv[2] == 'set-wallpaper' and argv[3] == sys.argv[2]
    assert argv[-1] == '%f' and config['setter']['overlap'] == 0
    assert os.access(argv[0], os.X_OK)
    assert pathlib.Path(argv[1]).is_file()
    black = pathlib.Path(argv[4]).read_bytes()
    assert black.startswith(b'\x89PNG\r\n\x1a\n')
    print('Timewall: actual CLI, generated setter config, fallback and session declarations passed')
    PY
      touch "$out"
  ''
