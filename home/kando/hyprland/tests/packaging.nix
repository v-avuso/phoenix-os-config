# Run: nix build --impure --file home/kando/hyprland/tests/packaging.nix --no-link
let
  flake = builtins.getFlake ("git+file://" + toString ../../../..);
  pkgs = flake.inputs.nixpkgs.legacyPackages.x86_64-linux;
  user = import ../../../../config/user.nix { inherit (pkgs) lib; };
  metal = flake.nixosConfigurations.metal.config;
  vm = flake.nixosConfigurations.vm.config;
  fixture = bypass: import ../../tests/fixture.nix {
    nixpkgsPath = flake.inputs.nixpkgs.outPath;
    gameBypass = bypass;
  };
  lua = (fixture true).lua;
  rollbackLua = (fixture false).lua;
  keyLua = (import ../../tests/fixture.nix {
    nixpkgsPath = flake.inputs.nixpkgs.outPath;
    gameButtons = "keys";
  }).lua;
  mouse = metal.systemd.services."phoenix-mouse-debounce@".serviceConfig;
in
assert pkgs.lib.hasInfix ''configureKandoShortcuts(phoenixIsGameWindow, "mouse")'' lua;
assert pkgs.lib.hasInfix ''configureKandoShortcuts(phoenixIsGameWindow, "keys")'' keyLua;
assert !(pkgs.lib.hasInfix ''hl.bind("F23"'' lua);
assert !(pkgs.lib.hasInfix ''hl.bind("F24"'' lua);
assert pkgs.lib.hasInfix ''hl.bind("F23", hl.dsp.global("menu.kando.Kando:global-menu")'' rollbackLua;
assert pkgs.lib.hasInfix ''hl.bind("F24", hl.dsp.global("menu.kando.Kando:contextual-menu")'' rollbackLua;
assert !(pkgs.lib.hasInfix "configureKandoShortcuts" rollbackLua);
assert !(vm.systemd.services ? "phoenix-mouse-debounce@");
assert !(vm.home-manager.users.${user.name}.systemd.user.services ? kando);
assert mouse.User == "phoenix-mouse-debounce";
assert mouse.Group == "phoenix-mouse-debounce";
assert mouse.SupplementaryGroups == [ "input" "uinput" ];
assert mouse.DevicePolicy == "closed";
assert pkgs.lib.hasSuffix " --map-side-buttons" mouse.ExecStart;
assert mouse.DeviceAllow == [
  "/dev/input/by-id/usb-Razer_Razer_Viper_V2_Pro_000000000000-event-mouse r"
  "/dev/uinput rw"
];
pkgs.runCommand "phoenix-kando-hyprland-check" { nativeBuildInputs = [ pkgs.lua ]; } ''
  lua ${./shortcuts.lua} ${../shortcuts.lua} ${../../../hyprland/gaming/windows/classification.lua}
  touch "$out"
''
