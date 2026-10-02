# Run with: nix eval --impure --file tests/pam-desktop-conditional.nix
let
  flake = builtins.getFlake (toString ../.);
  metal = flake.nixosConfigurations.metal.config;
  vm = flake.nixosConfigurations.vm.config;
  hasService = config: name: builtins.hasAttr name config.security.pam.services;
in
assert !metal.services.desktopManager.plasma6.enable;
assert !(hasService metal "kde-fingerprint");
assert !(hasService metal "kde");
assert vm.services.desktopManager.plasma6.enable;
assert (hasService vm "kde-fingerprint");
assert vm.security.pam.services."kde-fingerprint".u2f.enable;
assert vm.security.pam.services.kde.u2f.enable == false;
assert metal.security.pam.u2f.enable;
assert metal.security.pam.services.login.u2f.enable;
assert metal.security.pam.services.sudo.u2f.enable;
assert metal.security.pam.services."sudo-i".u2f.enable;
assert metal.security.pam.services.su.u2f.enable;
assert metal.security.pam.services."su-l".u2f.enable;
assert metal.security.pam.services."polkit-1".u2f.enable;
assert metal.security.pam.services.sshd.u2f.enable == false;
true
