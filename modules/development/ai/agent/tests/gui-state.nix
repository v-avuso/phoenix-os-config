# After coordinator stages owned new files: nix eval --impure --file this-file.nix
# Combined declaration/packaging only, no GUI, auth or activation.
let
  flake = builtins.getFlake ("git+file://" + toString ../../../../..);
  lib = flake.inputs.nixpkgs.lib;
  off = flake.nixosConfigurations.metal.config;
  on = (flake.nixosConfigurations.metal.extendModules {
    modules = [ { phoenix.agent.gui.sharedState.enable = true; } ];
  }).config;
  gui = cfg: builtins.fromJSON (builtins.unsafeDiscardStringContext cfg.system.build.phoenixAgentGuiConfig.text);
  state = builtins.fromJSON (builtins.unsafeDiscardStringContext on.system.build.phoenixAgentGuiStateConfig.text);
  native = cfg: cfg.programs.codexDesktopLinux.package.buildCommand;
in
assert !off.phoenix.agent.gui.sharedState.enable;
assert on.phoenix.agent.gui.sharedState.enable;
assert (gui off).profileSeed != [ ];
assert (gui on).profileSeed == [ ];
assert lib.hasInfix "gui-state.py" (native on);
assert !(lib.hasInfix "gui-state.py" (native off));
assert lib.hasInfix "history-runtime.py" (native on);
assert lib.hasInfix "history-runtime.py" (native off);
assert !on.phoenix.agent.identity.enable;
assert !on.phoenix.agent.reservations.enable;
assert !on.phoenix.agent.shutdownOrdering.enable;
assert !on.services.phoenixDeployment.disruptionGuard.enable;
assert !on.services.phoenixDeployment.securityReview.enable;
assert !on.phoenix.authorization.explanation.enable;
assert lib.hasInfix "codex-desktop" (native on);
assert state.lock == "/home/v/.local/state/phoenix-openshell/gui.lock";
assert lib.hasInfix "phoenix-gui-history-runtime.py" state.historyModule;
assert lib.hasInfix "phoenix-gui-transport.py" state.transportModule;
{ passed = true; nativeDesktop = on.programs.codexDesktopLinux.package; sandboxDesktop = on.system.build.phoenixAgentGuiDesktop; sandboxWrapper = on.system.build.phoenixAgentGuiWrapper; }
