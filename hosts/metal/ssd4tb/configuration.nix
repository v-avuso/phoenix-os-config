{ lib, ... }:
{
  imports = [
    ../common.nix
    ./hardware-configuration.nix
  ];

  # Use the existing 4 TB firmware entry; preserve the old SSD's boot priority.
  boot.loader.efi.canTouchEfiVariables = lib.mkForce false;
  phoenix.target = "metal-4tb";

  # Resume after first-boot acceptance and a committed, installed source baseline.
  services.phoenixUpdates.enable = lib.mkForce false;

  # Never synchronize the restored identity before explicit acceptance. The
  # init service requires syncthing.service, so guard both units.
  systemd.services.syncthing.unitConfig.ConditionPathExists = "/var/lib/phoenix-migration/syncthing-accepted";
  systemd.services.syncthing-init.unitConfig.ConditionPathExists = "/var/lib/phoenix-migration/syncthing-accepted";
}
