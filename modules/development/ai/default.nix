{ pkgs, ... }:

{
  imports = [
    ./codex.nix
    ./agent/codex-sandbox.nix
    ./agent/deployment.nix
    ./agent
    ./agent/gui.nix
  ];
  phoenix.agent.gui.sharedState.enable = true;
  services.phoenixDeployment.securityReview.enable = true;
}
