# Composition defaults append narrowly; an explicit operator list still replaces them.
{ flake }:
let
  base = flake.nixosConfigurations.metal;
  lib = flake.inputs.nixpkgs.lib;
  user = import ../../../../../config/user.nix { inherit lib; };
  defaults = base.options.phoenix.agent.workspaces.default;
  selected = base.config.phoenix.agent.workspaces;
  custom = (base.extendModules { modules = [ { phoenix.agent.workspaces = [ "/fixture/custom" ]; } ]; }).config.phoenix.agent.workspaces;
in
assert selected == defaults ++ [ "${user.homeDirectory}/.codex/worktrees" ];
assert custom == [ "/fixture/custom" ];
{ passed = true; inherit selected custom; }
