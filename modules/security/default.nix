{ config, lib, pkgs, user, ... }:

{
  # Security-focused desktop baseline for NixOS.
  # Goal: raise exploit cost + improve containment/visibility while keeping the
  # desktop and NVIDIA stack practical.

  # ---------------------------------------------------------------------------
  # Kernel / exploit mitigation
  # ---------------------------------------------------------------------------

  # Practical default for very new NVIDIA hardware.
  # If proprietary NVIDIA support lags latest, switch to the newest supported stable kernel.
  boot.kernelPackages = pkgs.linuxPackages_latest;

  # Rarely needed legacy/network protocol modules. Low-risk reduction of kernel attack surface.
  boot.blacklistedKernelModules = [
    "dccp"
    "rds"
    "sctp"
    "tipc"
  ];

  boot.kernel.sysctl = {
    "kernel.kptr_restrict" = 2;
    "kernel.dmesg_restrict" = 1;
    "kernel.yama.ptrace_scope" = 1;
    "net.core.bpf_jit_harden" = 2;

    "fs.protected_symlinks" = 1;
    "fs.protected_hardlinks" = 1;
    "fs.protected_fifos" = 2;
    "fs.protected_regular" = 2;
    "fs.suid_dumpable" = 0;

    # Headroom for ClamAV on-access scanning and developer file watchers.
    "fs.fanotify.max_queued_events" = 32768;
    "fs.inotify.max_user_watches" = 524288;

    "net.ipv4.conf.all.rp_filter" = 1;
    "net.ipv4.conf.default.rp_filter" = 1;
    "net.ipv4.conf.all.accept_redirects" = 0;
    "net.ipv4.conf.default.accept_redirects" = 0;
    "net.ipv6.conf.all.accept_redirects" = 0;
    "net.ipv6.conf.default.accept_redirects" = 0;
    "net.ipv4.conf.all.send_redirects" = 0;
    "net.ipv4.conf.default.send_redirects" = 0;
    "net.ipv4.conf.all.accept_source_route" = 0;
    "net.ipv4.conf.default.accept_source_route" = 0;
    "net.ipv6.conf.all.accept_source_route" = 0;
    "net.ipv6.conf.default.accept_source_route" = 0;
    "net.ipv4.tcp_syncookies" = 1;
  };

  # ---------------------------------------------------------------------------
  # Firewall / outbound visibility
  # ---------------------------------------------------------------------------

  networking.firewall = {
    enable = true;
    allowPing = false;
  };

  services.opensnitch = {
    enable = true;
  
    rules = import ./opensnitch-rules.nix {
      inherit config lib pkgs;
    };

    settings = {
      # Learning mode: allow outbound traffic and record it for later review.
      # The allow rules remain available as a future default-deny baseline.
      DefaultAction = "allow";
      InterceptUnknown = true;
      LogUTC = true;
      LogMicro = true;
      Server.Loggers = [
        {
          Name = "syslog";
          Server = "";
          Format = "json";
          Tag = "opensnitchd";
        }
      ];

      # Avoid opensnitch_ebpf kernel-module builds. eBPF is faster/more reliable
      # when it builds, but it is coupled to kernel internals and currently fails
      # against Linux 7.0.5 in this config.
      ProcMonitorMethod = "proc";
    };
  };

  # ---------------------------------------------------------------------------
  # Mandatory Access Control
  # ---------------------------------------------------------------------------

  security.apparmor = {
    enable = true;
    packages = with pkgs; [
      apparmor-profiles
    ];
  };

  # ---------------------------------------------------------------------------
  # Auditing / logs
  # ---------------------------------------------------------------------------

  # Disabled for now: auditctl fails on this kernel/channel even for control
  # commands such as `auditctl -b 64`, so audit rule loading currently breaks
  # activation. Set both enable flags to true once nixpkgs/kernel/audit improves.
  security.audit.enable = false;
  security.auditd.enable = false;

  security.audit.rules = [
    "-w /etc/passwd -p wa -k identity"
    "-w /etc/group -p wa -k identity"
    "-w /etc/shadow -p wa -k identity"
    "-w /etc/sudoers -p wa -k privilege"
    "-w /etc/sudoers.d -p wa -k privilege"

    "-w ${user.nixosConfigPath} -p wa -k nixos-config"
    "-w /boot -p wa -k boot"

    "-a always,exit -F arch=b64 -S init_module -S finit_module -S delete_module -k kernel-modules"
    "-a always,exit -F arch=b64 -S adjtimex -S settimeofday -S clock_settime -k time-change"
  ];

  services.journald.extraConfig = ''
    SystemMaxUse=1G
    RuntimeMaxUse=512M
    MaxRetentionSec=30day
  '';

  # ---------------------------------------------------------------------------
  # Antivirus / file ingress scanning
  # ---------------------------------------------------------------------------

  services.clamav = {
    daemon.enable = true;
    clamonacc.enable = true;
    updater.enable = true;

    daemon.settings = {
      OnAccessIncludePath = user.downloadsDirectory;
      OnAccessPrevention = true;
      OnAccessExtraScanning = true;
      OnAccessMaxFileSize = "100M";
    };
  };

  # First-run robustness: clamd cannot start before freshclam has created
  # /var/lib/clamav/*.cvd/*.cld signature databases. Keep the switch from
  # failing if the database is not present yet, and make clamonacc wait for clamd.
  systemd.services.clamav-daemon.unitConfig.ConditionPathExistsGlob = "/var/lib/clamav/*.c[vl]d";
  systemd.services.clamav-clamonacc = {
    wants = [ "clamav-daemon.service" "clamav-freshclam.service" ];
    after = [ "clamav-daemon.service" "clamav-freshclam.service" ];
    unitConfig.ConditionPathExistsGlob = "/var/lib/clamav/*.c[vl]d";
  };

  # ---------------------------------------------------------------------------
  # Sandboxed app layer
  # ---------------------------------------------------------------------------

  services.flatpak.enable = true;

  # Portal implementation belongs in the desktop module, because KDE/Hyprland/GNOME
  # need different portal packages.

  environment.systemPackages = with pkgs; [
    bubblewrap
  ];

  # ---------------------------------------------------------------------------
  # Firmware / privilege hygiene
  # ---------------------------------------------------------------------------

  services.fwupd.enable = true;

  security.sudo.enable = false;
  security.sudo-rs = {
    enable = true;
    wheelNeedsPassword = true;
    execWheelOnly = true;
    extraConfig = ''
      Defaults env_keep += "SSH_AUTH_SOCK TERM DISPLAY WAYLAND_DISPLAY XAUTHORITY"
    '';
  };

  security.polkit.enable = true;
}
