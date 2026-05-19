{ pkgs, ... }:

{
  environment.systemPackages = with pkgs; [
    # Baseline version-control CLI.
    git

    # Visual Git client for history, staging, diffs, branches.
    sourcegit
  ];
}
