{ pkgs, ... }:

let
  hookPath = pkgs.lib.makeBinPath [ pkgs.coreutils pkgs.util-linux ];
  hook = pkgs.writeShellScriptBin "phoenix-dji-hibernate-wakeup" (
    builtins.replaceStrings
      [ "@DJI_HOOK_PATH@" ]
      [ hookPath ]
      (builtins.readFile ./dji-hibernate-wakeup.sh)
  );
in
{
  # DJI Wireless Mic Rx 2ca3:4015 can trigger an HCD wake-pending condition
  # during hibernation. The failure followed the receiver across at least two
  # AMD xHCI controllers. Linux USB_QUIRK_DISCONNECT_SUSPEND was tested and did
  # not solve it; temporarily disabling wake on its owning PCI xHCI controller
  # allowed successful hibernation. The exact kernel/device root cause remains
  # unresolved. This is an intentionally narrow workaround; remove and retest
  # it if DJI firmware or Linux USB/xHCI/HCD wake handling changes so hibernation
  # succeeds with controller wake enabled.
  environment.etc."systemd/system-sleep/50-phoenix-dji-hibernate-wakeup".source =
    "${hook}/bin/phoenix-dji-hibernate-wakeup";
}
