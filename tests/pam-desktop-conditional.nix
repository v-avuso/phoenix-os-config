# Run with: nix eval --impure --file tests/pam-desktop-conditional.nix
let
  flake = builtins.getFlake ("git+file://" + toString ../.);
  metal = flake.nixosConfigurations.metal.config;
  vm = flake.nixosConfigurations.vm.config;
  hasService = config: name: builtins.hasAttr name config.security.pam.services;
  linesMatching = pattern: text:
    builtins.filter
      (line: builtins.match pattern line != null)
      (builtins.filter builtins.isString (builtins.split "\n" text));
  u2fLines = config: service:
    linesMatching "auth sufficient .*pam_u2f[.]so.*"
      config.security.pam.services.${service}.text;
  polkitU2fLines = u2fLines metal "polkit-1";
  polkitText = metal.security.pam.services."polkit-1".text;
  polkitAuthLines = linesMatching "auth .*" polkitText;
  noticeLines = linesMatching "auth optional .*pam_echo[.]so file=.*"
    polkitText;
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
assert !metal.security.pam.services."polkit-1".u2f.enable;
assert builtins.length polkitU2fLines == 2;
assert builtins.match ".*pam_u2f[.]so cue .*pinverification=0.*userverification=1.*u2f-biometric.*" (builtins.elemAt polkitU2fLines 0) != null;
assert builtins.match ".*pam_u2f[.]so pinverification=1.*userverification=0.*u2f-pin-fallback.*" (builtins.elemAt polkitU2fLines 1) != null;
assert builtins.length noticeLines == 2;
assert builtins.length polkitAuthLines == 6;
assert builtins.match ".*u2f-biometric.*" (builtins.elemAt polkitAuthLines 0) != null;
assert builtins.match ".*pam_echo[.]so.*u2f-pin-notice.*" (builtins.elemAt polkitAuthLines 1) != null;
assert builtins.match ".*u2f-pin-fallback.*" (builtins.elemAt polkitAuthLines 2) != null;
assert builtins.match ".*pam_echo[.]so.*u2f-fallback-notice.*" (builtins.elemAt polkitAuthLines 3) != null;
assert builtins.match ".*pam_unix[.]so.*unix.*" (builtins.elemAt polkitAuthLines 4) != null;
assert builtins.match ".*pam_deny[.]so.*deny.*" (builtins.elemAt polkitAuthLines 5) != null;
assert builtins.length (u2fLines metal "sudo") == 1;
assert builtins.length (u2fLines metal "login") == 1;
assert metal.security.pam.services.sshd.u2f.enable == false;
true
