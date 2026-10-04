{
  config,
  inputs,
  lib,
  pkgs,
  ...
}:

let
  system = pkgs.stdenv.hostPlatform.system;
  timewall = inputs.timewall.packages.${system}.default;
  caelestiaCli = "${config.programs.caelestia.cli.package}/bin/caelestia";
  timewallCli = "${timewall}/bin/timewall";
  python = "${pkgs.python3}/bin/python3";

  # This third-party HEIC is intentionally an external runtime asset, not
  # redistributed with Phoenix. Place it at ~/Pictures/Wallpapers/futuristic-city.heic.
  # Keeping this as a string means flake evaluation/builds do not depend on it;
  # a missing or unreadable file uses the generated black fallback below.
  wallpaperPath = "${config.home.homeDirectory}/Pictures/Wallpapers/futuristic-city.heic";

  lightAt = "07:00";
  darkAt = "20:00";
  helper = pkgs.writeText "phoenix-timewall-helper.py" (builtins.readFile ./timewall-helper.py);

  blackFallback =
    pkgs.runCommand "phoenix-timewall-black.png"
      {
        nativeBuildInputs = [ pkgs.python3 ];
      }
      ''
        ${python} - "$out" <<'PY'
        import struct
        import sys
        import zlib

        def chunk(kind, payload):
            return (struct.pack(">I", len(payload)) + kind + payload
                    + struct.pack(">I", zlib.crc32(kind + payload) & 0xffffffff))

        width, height = 3840, 2160
        row = b"\x00" + b"\x00\x00\x00\xff" * width
        image = b"\x89PNG\r\n\x1a\n"
        image += chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))
        image += chunk(b"IDAT", zlib.compress(row * height, 9))
        image += chunk(b"IEND", b"")
        with open(sys.argv[1], "wb") as output:
            output.write(image)
        PY
      '';

  timewallConfig = (pkgs.formats.toml { }).generate "phoenix-timewall-config.toml" {
    daemon.update_interval_seconds = 600;
    geoclue.enable = false;
    setter = {
      command = [
        python
        helper
        "set-wallpaper"
        caelestiaCli
        "${blackFallback}"
        "%f"
      ];
      quiet = false;
      overlap = 0;
    };
  };

  timewallStart = pkgs.writeShellScript "phoenix-timewall-start" ''
    exec ${python} ${helper} start \
      ${lib.escapeShellArgs [
        timewallCli
        wallpaperPath
        caelestiaCli
        (toString blackFallback)
      ]}
  '';

  themeSync = pkgs.writeShellScript "phoenix-timewall-theme-sync" ''
    exec ${python} ${helper} sync-theme \
      ${lib.escapeShellArgs [
        caelestiaCli
        lightAt
        darkAt
      ]}
  '';

  sessionTarget = "hyprland-session.target";
  themeService = "phoenix-timewall-theme.service";

  sessionBoundUnit = {
    PartOf = [ sessionTarget ];
    BindsTo = [ sessionTarget ];
    After = [ sessionTarget ];
  };
in
{
  home.packages = [ timewall ];

  xdg.configFile."timewall/config.toml".source = timewallConfig;

  systemd.user.services.phoenix-timewall = {
    Unit = sessionBoundUnit // {
      Description = "Timewall dynamic wallpaper for Caelestia";
    };
    Service = {
      Type = "simple";
      ExecStart = "${timewallStart}";
      # Timewall stores the daemon PID here. systemd removes this private
      # per-run directory on stop, so restarts cannot inherit stale PID state.
      RuntimeDirectory = "phoenix-timewall";
      RuntimeDirectoryMode = "0700";
      Environment = [
        "TIMEWALL_CONFIG_DIR=${config.xdg.configHome}/timewall"
        "TIMEWALL_RUNTIME_DIR=%t/phoenix-timewall"
      ];
      Restart = "no";
      TimeoutStopSec = 15;
    };
    Install.WantedBy = [ sessionTarget ];
  };

  systemd.user.services.phoenix-timewall-theme = {
    Unit = sessionBoundUnit // {
      Description = "Synchronize Caelestia light/dark mode with local time";
    };
    Service = {
      Type = "oneshot";
      ExecStart = "${themeSync}";
      Restart = "no";
    };
    Install.WantedBy = [ sessionTarget ];
  };

  systemd.user.timers.phoenix-timewall-theme-light = {
    Unit = sessionBoundUnit // {
      Description = "Set Caelestia light mode at 07:00 local time";
    };
    Timer = {
      OnCalendar = "*-*-* ${lightAt}:00";
      AccuracySec = "1s";
      Persistent = false;
      Unit = themeService;
    };
    Install.WantedBy = [ sessionTarget ];
  };

  systemd.user.timers.phoenix-timewall-theme-dark = {
    Unit = sessionBoundUnit // {
      Description = "Set Caelestia dark mode at 20:00 local time";
    };
    Timer = {
      OnCalendar = "*-*-* ${darkAt}:00";
      AccuracySec = "1s";
      Persistent = false;
      Unit = themeService;
    };
    Install.WantedBy = [ sessionTarget ];
  };
}
