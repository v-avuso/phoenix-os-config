{ pkgs, ... }:

{
  environment.systemPackages = with pkgs; [
    # Baseline version-control CLI.
    git

    # HTTPS credential helper with GitHub OAuth and Secret Service support.
    (git-credential-manager.override { withGpgSupport = false; })

    # Visual Git client for history, staging, diffs, branches.
    sourcegit
  ];
}
