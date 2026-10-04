# Run: nix build --impure --file tests/thunar-packaging.nix --no-link
# Use tracked Git sources only; never import private ignored checkout notes.
let
  flake = builtins.getFlake ("git+file://" + toString ../.);
  metal = flake.nixosConfigurations.metal;
  vm = flake.nixosConfigurations.vm.config;
  pkgs = metal.pkgs;
  user = import ../config/user.nix { inherit (pkgs) lib; };
  home = metal.config.home-manager.users.${user.name};
  cliSource = flake.inputs.caelestia-shell.inputs.caelestia-cli.packages.x86_64-linux.default.src;
  expectedPlugins = with pkgs; [
    thunar-archive-plugin
    thunar-volman
    thunar-media-tags-plugin
  ];
in
assert metal.config.programs.thunar.enable;
assert metal.config.programs.xfconf.enable;
assert metal.config.services.gvfs.enable;
assert metal.config.services.gvfs.package == pkgs.gvfs;
assert metal.config.services.tumbler.enable;
assert pkgs.lib.all (p: builtins.elem p metal.config.programs.thunar.plugins) expectedPlugins;
assert builtins.elem pkgs.engrampa metal.config.environment.systemPackages;
assert builtins.elem pkgs.zip metal.config.environment.systemPackages;
assert builtins.elem pkgs.unzip metal.config.environment.systemPackages;
assert home.xfconf.settings.thunar.misc-middle-click-in-tab;
assert !home.xfconf.settings.thunar.last-menubar-visible;
assert home.xdg.mimeApps.defaultApplications."inode/directory" == [ "thunar.desktop" ];
assert home.xdg.mimeApps.defaultApplications."application/zip" == [ "engrampa.desktop" ];
assert home.dconf.settings."org/mate/engrampa/dialogs/batch-add".default-extension == ".zip";
assert pkgs.lib.hasInfix "<submenu>Convert to…</submenu>" home.xdg.configFile."Thunar/uca.xml".text;
assert pkgs.lib.hasInfix "<submenu>Archive</submenu>" home.xdg.configFile."Thunar/uca.xml".text;
assert pkgs.lib.hasInfix "<name>Create ZIP</name>" home.xdg.configFile."Thunar/uca.xml".text;
assert pkgs.lib.any (
  p: toString p == "${flake.outPath}/patches/thunar-live-user-css.patch"
) pkgs.thunar-unwrapped.patches;
assert !(vm.programs.thunar.enable);
import ./thunar.nix {
  inherit pkgs;
  caelestiaCliSource = cliSource;
}
