{ config, inputs, lib, pkgs, user, ... }:

let
  inherit (lib) mkEnableOption mkIf;
  cfg = config.services.phoenixUpdates;
  policy = builtins.fromJSON (builtins.readFile ../../../config/updates.json);
  system = pkgs.stdenv.hostPlatform.system;
  runtimePath = lib.makeBinPath [ pkgs.nix pkgs.git pkgs.nix-update pkgs.coreutils pkgs.bash ];
  ordinaryHolds = lib.filterAttrs (name: _: !(builtins.elem name [ "firefox" "codex-cli" "codex-desktop" ])) policy.holds;
  heldPkgs = hold: import (builtins.getFlake "github:NixOS/nixpkgs/${hold.pin}") {
    inherit system;
    config = pkgs.config;
  };
  firefoxHold = policy.holds.firefox or null;
  heldFirefox = if firefoxHold == null then null else
    (import (builtins.getFlake "github:NixOS/nixpkgs/${firefoxHold.pin}") {
      inherit system;
      config = pkgs.config;
    }).firefox;
  firefoxPackage = if firefoxHold != null then heldFirefox else
    if policy.packageSources.firefox == "nixpkgs" then pkgs.firefox
    else inputs.nixpkgs-unstable.legacyPackages.${system}.firefox;

  runnerConfig = pkgs.writeText "phoenix-updates-runner.json" (builtins.toJSON {
    repo = user.repoDirectory;
    state = "/var/lib/phoenix-updates";
    policyFile = "config/updates.json";
    candidateScript = toString ./candidate.py;
    git = "${pkgs.git}/bin/git";
    nix = "${pkgs.nix}/bin/nix";
    python = "${pkgs.python3}/bin/python3";
    nixUpdate = "${pkgs.nix-update}/bin/nix-update";
    path = runtimePath;
    caBundle = "${pkgs.cacert}/etc/ssl/certs/ca-bundle.crt";
    nixHome = "/var/lib/phoenix-updates/nix-home";
    controllerSocket = "/run/phoenix-deploy/control.sock";
    target = if config.networking.hostName == "phoenix-vm" then "vm" else "metal";
    baseline = "/etc/phoenix-agent/activated-source";
    systemProfile = "/nix/var/nix/profiles/system";
  });

  runner = pkgs.writeText "phoenix-update-runner.py" (builtins.readFile ./runner.py);
  notifyFailure = pkgs.writeShellScript "phoenix-updates-notify-failure" ''
    exec ${pkgs.libnotify}/bin/notify-send --app-name=Phoenix \
      --urgency=normal "Phoenix update check failed" \
      "An update needs attention. See the phoenix-updates journal."
  '';
  userUid = config.users.users.${user.name}.uid;
in
{
  options.services.phoenixUpdates = {
    enable = mkEnableOption "reviewed Phoenix update preparation";
  };

  config = {
    assertions = [
      {
        assertion = builtins.elem policy.packageSources.firefox [ "nixpkgs" "nixpkgs-unstable" ];
        message = "updates.json must select Firefox from nixpkgs or nixpkgs-unstable";
      }
      {
        assertion = userUid != null && builtins.match "[0-9]+" (toString userUid) != null;
        message = "Phoenix update notification requires a fixed numeric desktop user UID";
      }
    ];

    # Ordinary holds pin only the named package, allowing the rest of the stable
    # system to advance. Kando preserves its existing exact-version contract.
    nixpkgs.overlays = [ (_final: _previous:
      lib.mapAttrs (name: hold: (heldPkgs hold).${name}) ordinaryHolds
    ) ];

    home-manager.users.${user.name}.programs.firefox.package = firefoxPackage;

    systemd.tmpfiles.rules = lib.optional cfg.enable
      "d /var/lib/phoenix-updates 0700 ${user.name} users -";
    environment.systemPackages = lib.optional cfg.enable
      (pkgs.writeShellScriptBin "phoenix-update" ''
        exec ${pkgs.python3}/bin/python3 -I ${runner} ${runnerConfig}
      '');

    systemd.services.phoenix-updates = mkIf cfg.enable {
      description = "Check upstream versions and prepare reviewed Phoenix update candidates";
      path = [ pkgs.nix pkgs.git pkgs.nix-update pkgs.coreutils pkgs.bash ];
      environment = {
        SSL_CERT_FILE = "${pkgs.cacert}/etc/ssl/certs/ca-bundle.crt";
        DBUS_SESSION_BUS_ADDRESS = "unix:path=/run/user/${toString userUid}/bus";
      };
      serviceConfig = {
        Type = "oneshot";
        User = user.name;
        Group = "users";
        StateDirectory = "phoenix-updates";
        StateDirectoryMode = "0700";
        ExecStart = "${pkgs.python3}/bin/python3 -I ${runner} ${runnerConfig}";
        NoNewPrivileges = true;
        PrivateTmp = true;
        ProtectSystem = "strict";
        ProtectHome = "read-only";
        ReadWritePaths = [ user.repoDirectory "/var/lib/phoenix-updates" ];
        MemoryMax = "4G";
        CPUQuota = "200%";
        TimeoutStartSec = "2h";
      };
      unitConfig.OnFailure = "phoenix-updates-notify.service";
    };

    systemd.services.phoenix-updates-notify = mkIf cfg.enable {
      description = "Notify the desktop user about a failed Phoenix update check";
      serviceConfig = {
        Type = "oneshot";
        User = user.name;
        Group = "users";
        Environment = "DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/${toString userUid}/bus";
        ExecStart = notifyFailure;
        NoNewPrivileges = true;
        ProtectSystem = "strict";
        ProtectHome = true;
      };
    };

    systemd.timers.phoenix-updates = mkIf cfg.enable {
      description = "Check selected Phoenix application sources every six hours";
      wantedBy = [ "timers.target" ];
      timerConfig = {
        OnCalendar = "*-*-* 00/6:00:00";
        Persistent = true;
        RandomizedDelaySec = "15m";
        Unit = "phoenix-updates.service";
      };
    };
  };
}
