{ config, lib, pkgs, user, ... }:

# Deliberately not imported by modules/services/default.nix until the observer,
# package adapters, safe merge-back, and controller boot flow are integrated.
let
  inherit (lib) mkEnableOption mkIf mkOption types;
  cfg = config.services.phoenix-updates;
  candidate = pkgs.writeText "phoenix-update-candidate.py" (builtins.readFile ./candidate.py);
  serviceConfig = pkgs.writeText "phoenix-update-config.json" (builtins.toJSON {
    repo = cfg.repository;
    state = "/var/lib/phoenix-updates";
    git = "${pkgs.git}/bin/git";
    nix = "${pkgs.nix}/bin/nix";
    nixHome = "/var/lib/phoenix-updates/nix-home";
    approvedCommit = cfg.approvedCommit;
    approvedSource = cfg.approvedSource;
    requireStore = true;
    controllerSocket = cfg.controllerSocket;
    target = cfg.target;
    requestFile = "/var/lib/phoenix-updates/request.json";
  });
in
{
  options.services.phoenix-updates = {
    enable = mkEnableOption "isolated Phoenix update candidate preparation";
    repository = mkOption { type = types.str; default = "${user.homeDirectory}/src/phoenix-os-config"; };
    approvedCommit = mkOption { type = types.nullOr types.str; default = null; };
    approvedSource = mkOption { type = types.nullOr types.str; default = null; };
    controllerSocket = mkOption { type = types.nullOr types.str; default = null; };
    target = mkOption { type = types.enum [ "metal" "vm" ]; default = "metal"; };
  };

  config = mkIf cfg.enable {
    assertions = [
      { assertion = cfg.approvedCommit != null && cfg.approvedSource != null
          && cfg.controllerSocket != null;
        message = "Phoenix updates require an approved source identity and the existing controller socket."; }
    ];

    systemd.services.phoenix-update-candidate = {
      description = "Prepare a bounded Phoenix update candidate";
      serviceConfig = {
        Type = "oneshot";
        User = user.name;
        Group = "users";
        StateDirectory = "phoenix-updates";
        StateDirectoryMode = "0700";
        ExecStart = "${pkgs.python3}/bin/python3 -B ${candidate} ${serviceConfig}";
        NoNewPrivileges = true;
        PrivateTmp = true;
        ProtectSystem = "strict";
        ProtectHome = "read-only";
        ReadWritePaths = [ cfg.repository "/var/lib/phoenix-updates" ];
        MemoryMax = "1G";
        CPUQuota = "200%";
        RuntimeMaxSec = "2h";
      };
    };

    systemd.timers.phoenix-update-candidate = {
      description = "Daily Phoenix update candidate check";
      wantedBy = [ "timers.target" ];
      timerConfig = {
        OnCalendar = "daily";
        Persistent = true;
        RandomizedDelaySec = "30m";
        Unit = "phoenix-update-candidate.service";
      };
    };
  };
}
