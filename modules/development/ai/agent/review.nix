{
  config,
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
      migrationMarker = "/var/lib/phoenix-deploy/reviewer-migrated";
      deploymentSocket = "/run/phoenix-deploy/control.sock";
    }
  );
  deployReview = pkgs.writeShellScriptBin "phoenix-deploy-review" ''
    exec ${pkgs.python3}/bin/python3 -I ${./deploy-review.py} ${reviewConfig} "$@"
  '';
  clientConfig = pkgs.writeText "phoenix-deployment-client.json" (
    builtins.toJSON {
      repo = user.repoDirectory;
      git = "${pkgs.git}/bin/git";
      deploymentSocket = "/run/phoenix-deploy/control.sock";
      clientOnly = true;
    }
  );
  deployClient = pkgs.writeShellScriptBin "phoenix-deploy-review" ''
    exec ${pkgs.python3}/bin/python3 -I ${./deploy-review.py} ${clientConfig} "$@"
  '';
  reviewLoginCommand = pkgs.writeShellScript "phoenix-review-login-retained" ''
    if [ -f /var/lib/phoenix-deploy/reviewer-migrated ]; then
      echo 'Reviewer login belongs to the protected deployment controller; no OAuth login needed.'
      exit 0
    fi
    cd /
    if [ "$#" -eq 0 ] && [ -f "$CODEX_HOME/auth.json" ]; then
      exec ${codexCliPackage}/bin/codex login status
    fi
    exec ${codexCliPackage}/bin/codex login "$@"
  '';
  reviewLogin = pkgs.writeShellScriptBin "phoenix-review-login" ''
    export CODEX_HOME="${user.homeDirectory}/.local/state/phoenix-agent-review"
    ${pkgs.coreutils}/bin/install -d -m 700 "$CODEX_HOME"
    exec ${pkgs.util-linux}/bin/flock "$CODEX_HOME/migration.lock" ${reviewLoginCommand} "$@"
  '';
  deploymentConfig = pkgs.writeText "phoenix-deployment.json" (
    builtins.toJSON {
      clientUid = config.users.users.${user.name}.uid;
      target = if config.networking.hostName == "phoenix-vm" then "vm" else "metal";
      reviewerUser = "phoenix-deploy-review";
      builderUser = "phoenix-deploy-build";
      reviewHome = "/var/lib/phoenix-deploy-review";
      migrationMarker = "/var/lib/phoenix-deploy/reviewer-migrated";
      loginHome = "${user.homeDirectory}/.local/state/phoenix-agent-review";
      work = "/var/lib/phoenix-deploy/requests";
      baseline = "/etc/phoenix-agent/activated-source";
      controller = toString ./deployment.py;
      reviewScript = toString ./deploy-review.py;
      upstreamReviewScript = toString ./upstream-review.py;
      python = "${pkgs.python3}/bin/python3";
      setpriv = "${pkgs.util-linux}/bin/setpriv";
      nix = "${pkgs.nix}/bin/nix";
      nixStore = "${pkgs.nix}/bin/nix-store";
      nixEnv = "${pkgs.nix}/bin/nix-env";
      systemdRun = "${pkgs.systemd}/bin/systemd-run";
      codex = "${codexCliPackage}/bin/codex";
      bwrap = "${pkgs.bubblewrap}/bin/bwrap";
      caBundle = "${pkgs.cacert}/etc/ssl/certs/ca-bundle.crt";
      policy = toString ./review-policy.md;
      model = "gpt-6.1-sol";
      effort = "medium";
      activationEnvironment = {
        PATH = "/run/current-system/sw/bin:/run/current-system/sw/sbin";
        HOME = "/root";
        LOCALE_ARCHIVE = "${pkgs.glibcLocales}/lib/locale/locale-archive";
      };
    }
  );
  bootstrap = pkgs.writeShellScriptBin "phoenix-deploy-bootstrap" ''
    exec /run/wrappers/bin/pkexec --disable-internal-agent ${pkgs.python3}/bin/python3 -I ${./deployment.py} ${deploymentConfig} bootstrap
  '';

in
{
  _module.args.phoenixDeployReviewPackage = deployClient;
  _module.args.phoenixDeployReviewClientConfig = clientConfig;
  # The upstream default allows all users, while only root is trusted. Keep
  # that access policy intact; a future restrictive policy must name this user.
  assertions = [
    {
      assertion =
        builtins.elem "*" config.nix.settings.allowed-users
        || builtins.elem "phoenix-deploy-build" config.nix.settings.allowed-users;
      message = "Reviewed deployment requires phoenix-deploy-build in nix.settings.allowed-users (not trusted-users).";
    }
  ];
  environment.systemPackages = [
    deployReview
    reviewLogin
    bootstrap
  ];
  environment.etc."phoenix-agent/review-policy.md".source = ./review-policy.md;
  environment.etc."phoenix-agent/activated-source".source = inputs.self.outPath;
  users.groups.phoenix-deploy-review = { };
  users.groups.phoenix-deploy-build = { };
  users.users.phoenix-deploy-review = {
    isSystemUser = true;
    group = "phoenix-deploy-review";
    home = "/var/lib/phoenix-deploy-review";
  };
  users.users.phoenix-deploy-build = {
    isSystemUser = true;
    group = "phoenix-deploy-build";
    home = "/var/empty";
  };
  systemd.tmpfiles.rules = [
    "d /var/lib/phoenix-deploy 0711 root root -"
    "d /var/lib/phoenix-deploy/requests 0711 root root -"
    "d /var/lib/phoenix-deploy-review 0700 phoenix-deploy-review phoenix-deploy-review -"
    "d /run/phoenix-deploy 0755 root root -"
  ];
  systemd.sockets.phoenix-deploy = {
    wantedBy = [ "sockets.target" ];
    socketConfig = {
      ListenStream = "/run/phoenix-deploy/control.sock";
      SocketMode = "0600";
      SocketUser = user.name;
      RemoveOnStop = true;
    };
  };
  systemd.services.phoenix-deploy = {
    description = "Protected independently reviewed NixOS deployment controller";
    requires = [ "phoenix-deploy.socket" ];
    after = [
      "phoenix-deploy.socket"
      "nix-daemon.socket"
    ];
    # Keep the authorizing controller alive through the activation it authorized.
    # New controller/policy takes effect on explicit restart or reboot.
    restartIfChanged = false;
    stopIfChanged = false;
    serviceConfig = {
      ExecStart = "${pkgs.python3}/bin/python3 -I ${./deployment.py} ${deploymentConfig} serve";
      User = "root";
      UMask = "0077";
      Restart = "on-failure";
      KillMode = "process";
    };
  };
}
