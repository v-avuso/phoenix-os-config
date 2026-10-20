# Run: nix build --impure --file modules/input/keyd/tests/symbols.nix --no-link
let
  flake = builtins.getFlake ("git+file://" + toString ../../../..);
  system = flake.nixosConfigurations.metal;
  pkgs = system.pkgs;
  config = system.config;
  user = import ../../../../config/user.nix { inherit (pkgs) lib; };
  home = config.home-manager.users.${user.name};
  vm = flake.nixosConfigurations.vm.config;
  vmHome = vm.home-manager.users.${user.name};
  xkb = { inherit (config.services.xserver.xkb) layout variant options; };
  data = pkgs.writeText "keyboard-test.json" (builtins.toJSON {
    inherit xkb;
    inherit (config.services.keyd.keyboards.default) settings;
  });
in
assert pkgs.lib.hasInfix "kb_variant = ${builtins.toJSON xkb.variant}" home.xdg.configFile."caelestia/hypr-user.lua".text;
assert pkgs.lib.hasInfix "kb_options = ${builtins.toJSON xkb.options}" home.xdg.configFile."caelestia/hypr-user.lua".text;
assert vmHome.programs.plasma.configFile."kxkbrc"."Layout".VariantList.value == xkb.variant;
assert vmHome.programs.plasma.configFile."kxkbrc"."Layout".Options.value == xkb.options;
pkgs.runCommand "caps-symbol-events" {
  nativeBuildInputs = [ pkgs.stdenv.cc pkgs.python3 ];
  XKB_CONFIG_ROOT = "${pkgs.xkeyboard_config}/share/X11/xkb";
} ''
  source=${config.services.keyd.package.src}
  cc -D_DEFAULT_SOURCE -DDATA_DIR='""' -iquote "$source/src" \
    ${./events.c} \
    "$source/src/keyboard.c" "$source/src/string.c" "$source/src/macro.c" \
    "$source/src/config.c" "$source/src/log.c" "$source/src/ini.c" \
    "$source/src/keys.c" "$source/src/unicode.c" -o events
  python3 ${./symbols.py} ${data} ${pkgs.libxkbcommon}/lib/libxkbcommon.so ./events
  touch "$out"
''
