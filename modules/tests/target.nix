# Evaluate in a Git-visible source; never starts services or copies disk data.
let
  flake = builtins.getFlake ("git+file://" + toString ../..);
  lib = flake.inputs.nixpkgs.lib;
  old = flake.nixosConfigurations.metal.config;
  new = flake.nixosConfigurations.metal-4tb.config;
  vm = flake.nixosConfigurations.vm.config;
  enabled = (flake.nixosConfigurations.metal-4tb.extendModules {
    modules = [ { services.phoenixUpdates.enable = lib.mkOverride 40 true; } ];
  }).config;
  policy = c: builtins.fromJSON c.system.build.phoenixAuthorizationPolicy.text;
  # Inspect generated JSON without realizing its package output contexts.
  runner = c: builtins.fromJSON (builtins.unsafeDiscardStringContext c.system.build.phoenixUpdateRunnerConfig.text);
in
assert old.phoenix.target == "metal" && (policy old).target == "metal";
assert old.fileSystems."/".device == "/dev/disk/by-uuid/e9d1b391-3f86-4254-9970-aa47df230474";
assert vm.phoenix.target == "vm" && (policy vm).target == "vm";
assert new.phoenix.target == "metal-4tb" && (policy new).target == "metal-4tb";
assert (runner new).target == "metal-4tb" && (runner enabled).target == "metal-4tb";
assert !new.services.phoenixUpdates.enable && enabled.services.phoenixUpdates.enable;
assert new.systemd.services.syncthing.unitConfig.ConditionPathExists == "/var/lib/phoenix-migration/syncthing-accepted";
assert new.systemd.services.syncthing-init.unitConfig.ConditionPathExists == "/var/lib/phoenix-migration/syncthing-accepted";
assert new.networking.hostName == "phoenix" && new.users.mutableUsers;
assert new.security.pam.u2f.control == "sufficient";
assert !new.boot.loader.efi.canTouchEfiVariables;
assert new.fileSystems."/".device == "/dev/mapper/luks-d9756988-1532-4903-b6d9-6e89735248f7";
assert new.fileSystems."/home".device == new.fileSystems."/".device;
assert new.fileSystems."/nix".device == new.fileSystems."/".device;
assert builtins.elem "subvolid=5" new.fileSystems."/".options;
assert builtins.elem "subvol=home" new.fileSystems."/home".options;
assert builtins.elem "subvol=nix" new.fileSystems."/nix".options;
assert new.fileSystems."/boot".device == "/dev/disk/by-uuid/B4E3-63E5";
assert map (item: item.device) new.swapDevices == [ "/dev/mapper/luks-8c5388a9-cb79-4c29-8de1-65cf542437e1" ];
assert builtins.length (builtins.attrNames new.boot.initrd.luks.devices) == 2;
assert new.boot.initrd.luks.devices."luks-d9756988-1532-4903-b6d9-6e89735248f7".device == "/dev/disk/by-uuid/d9756988-1532-4903-b6d9-6e89735248f7";
assert new.boot.initrd.luks.devices."luks-8c5388a9-cb79-4c29-8de1-65cf542437e1".device == "/dev/disk/by-uuid/8c5388a9-cb79-4c29-8de1-65cf542437e1";
assert builtins.all (item: item.assertion) enabled.assertions;
{ passed = true; }
