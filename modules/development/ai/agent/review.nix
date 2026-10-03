{
  pkgs,
  user,
  codexCliPackage,
  inputs,
  ...
}:
let
  reviewConfig = pkgs.writeText "phoenix-review.json" (
    builtins.toJSON {
      repo = user.repoDirectory;
      reviewHome = "${user.homeDirectory}/.local/state/phoenix-agent-review";
      codex = "${codexCliPackage}/bin/codex";
      git = "${pkgs.git}/bin/git";
      nix = "${pkgs.nix}/bin/nix";
      bwrap = "${pkgs.bubblewrap}/bin/bwrap";
      caBundle = "${pkgs.cacert}/etc/ssl/certs/ca-bundle.crt";
      # Nix store binaries are not setuid; NixOS owns the privileged wrapper.
      pkexec = "/run/wrappers/bin/pkexec";
      policy = toString ./review-policy.md;
      model = "gpt-6.1-sol";
      effort = "medium";
      baseline = "/etc/phoenix-agent/activated-source";
    }
  );
  deployReview = pkgs.writeShellScriptBin "phoenix-deploy-review" ''
    exec ${pkgs.python3}/bin/python3 -I ${./deploy-review.py} ${reviewConfig} "$@"
  '';
  reviewLogin = pkgs.writeShellScriptBin "phoenix-review-login" ''
    export CODEX_HOME="${user.homeDirectory}/.local/state/phoenix-agent-review"
    ${pkgs.coreutils}/bin/install -d -m 700 "$CODEX_HOME"
    cd /
    if [ "$#" -eq 0 ] && [ -f "$CODEX_HOME/auth.json" ]; then
      exec ${codexCliPackage}/bin/codex login status
    fi
    exec ${codexCliPackage}/bin/codex login "$@"
  '';
in
{
  environment.systemPackages = [
    deployReview
    reviewLogin
  ];
  environment.etc."phoenix-agent/review-policy.md".source = ./review-policy.md;
  environment.etc."phoenix-agent/activated-source".source = inputs.self.outPath;
  # No passwordless Polkit rule or root broker activation operation. Review and
  # build are useful now; temporary activation still uses normal authentication.
}
