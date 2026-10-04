{ pkgs, ... }:
let
  device = "/dev/input/by-id/usb-Razer_Razer_Viper_V2_Pro_000000000000-event-mouse";
  python = pkgs.python3.withPackages (p: [ p.libevdev ]);
  # Bind lifecycle to the physical event node supplied by the exact udev match.
  # The fixed by-id argument independently prevents arbitrary node capture.
in
{
  # Reuse NixOS's uinput node/group setup. Like the maintained keyd service,
  # use a fixed system account with device groups only inside this closed unit;
  # the filter needs device IO, not root-owned files or an interactive login.
  hardware.uinput.enable = true;
  users.groups.phoenix-mouse-debounce = { };
  users.users.phoenix-mouse-debounce = {
    isSystemUser = true;
    group = "phoenix-mouse-debounce";
  };
  services.udev.extraRules = ''
    ACTION=="add", SUBSYSTEM=="input", KERNEL=="event*", ENV{ID_INPUT_MOUSE}=="1", SYMLINK=="input/by-id/usb-Razer_Razer_Viper_V2_Pro_000000000000-event-mouse", ENV{ID_SERIAL}=="Razer_Razer_Viper_V2_Pro_000000000000", TAG+="systemd", ENV{SYSTEMD_WANTS}+="phoenix-mouse-debounce@%k.service"
  '';
  systemd.services."phoenix-mouse-debounce@" = {
    description = "Hardware-only Razer mouse side-button debounce";
    bindsTo = [ "dev-input-%i.device" ];
    after = [
      "dev-input-%i.device"
      "systemd-modules-load.service"
    ];
    serviceConfig = {
      Type = "simple";
      User = "phoenix-mouse-debounce";
      Group = "phoenix-mouse-debounce";
      SupplementaryGroups = [
        "input"
        "uinput"
      ];
      ExecStart = "${python}/bin/python3 -I ${./mouse-side-button-debounce.py} ${device}";
      Restart = "on-failure";
      RestartSec = 1;
      TimeoutStopSec = 5;
      DevicePolicy = "closed";
      DeviceAllow = [
        "${device} r"
        "/dev/uinput rw"
      ];
      NoNewPrivileges = true;
      CapabilityBoundingSet = "";
      ProtectSystem = "strict";
      ProtectHome = true;
      PrivateTmp = true;
      ProtectKernelTunables = true;
      ProtectKernelModules = true;
      ProtectControlGroups = true;
      RestrictAddressFamilies = [ "AF_UNIX" ];
      RestrictRealtime = true;
      LockPersonality = true;
      UMask = "0077";
    };
  };
}
