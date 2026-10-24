{ lib, ... }:
{
  imports = [
    ../common.nix
    ./hardware-configuration.nix
  ];

  # Use the existing 4 TB firmware entry; preserve the old SSD's boot priority.
  boot.loader.efi.canTouchEfiVariables = lib.mkForce false;
  phoenix.target = "metal-4tb";

  # Migration accepted: inherit normal Syncthing and update services. The old
  # SSD must remain offline or boot with the rollback masks in the runbook.
}
