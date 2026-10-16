{ lib, pkgs, user, ... }:

{
  imports = [
    ./codex.nix
    ./agent/codex-sandbox.nix
    ./agent/deployment.nix
    ./agent
    ./agent/gui.nix
  ];
  # Append at option-default priority: explicit operator workspace lists still replace it.
  phoenix.agent.workspaces = lib.mkOptionDefault (lib.mkAfter [ "${user.homeDirectory}/.codex/worktrees" ]);
  phoenix.agent.gui.sharedState.enable = true;
  services.phoenixDeployment.securityReview.enable = true;
}
