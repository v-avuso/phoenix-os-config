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
  # allowed successful hibernation. On 2026-09-29, a failed suspend involved
  # the same controller that owned the receiver, but the logs do not prove the
  # receiver caused that failure. Apply the same temporary workaround for
  # suspend and hibernation-family transitions. The exact kernel/device root
  # cause remains unresolved; remove and retest it if DJI firmware or Linux
  # USB/xHCI/HCD wake handling changes so these transitions succeed with
  # controller wake enabled.
  environment.etc."systemd/system-sleep/50-phoenix-dji-hibernate-wakeup".source =
    "${hook}/bin/phoenix-dji-hibernate-wakeup";
}
