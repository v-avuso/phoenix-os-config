{
  config,
  pkgs,
  user,
  inputs,
  lib,
  ...
}:
let
  cfg = config.services.phoenixDeployment;
  sourceSelector = pkgs.writeScript "phoenix-source" (
    builtins.replaceStrings [ "#!/usr/bin/env python3" ]
      [ "#!${pkgs.python3}/bin/python3" ] (builtins.readFile ../../../../commands/phoenix-source)
  );
  operatorCommand = [
    "/run/wrappers/bin/pkexec"
    "--disable-internal-agent"
    "${pkgs.python3}/bin/python3"
    "-I"
    (toString ./deployment.py)
    (toString deploymentConfig)
    "operator"
  ];
  # The caller supplies only a protected pending-record nonce. The controller
  # validates UID, policy, source/closure, target/action and current baseline;
  # no caller-provided command, store path or source is accepted here.
  securityOverride = pkgs.writeShellScript "phoenix-security-review-override" ''
    if [ "$#" -ne 1 ]; then exit 2; fi
    exec ${pkgs.python3}/bin/python3 -I ${./deployment.py} ${deploymentConfig} override "$1"
  '';
  overrideCommand = lib.optionals cfg.securityReview.enable [
    "/run/wrappers/bin/pkexec"
    "--disable-internal-agent"
    (toString securityOverride)
  ];
  # The privileged reviewer is a separate control-plane dependency. Everyday
  # CLI freshness must not silently replace the code enforcing review isolation.
  reviewerCodexPackage = pkgs.callPackage ./reviewer-codex.nix { };
  reviewConfig = pkgs.writeText "phoenix-review.json" (
    builtins.toJSON {
      repo = user.repoDirectory;
      sourceSelector = toString sourceSelector;
      modelReviewEnabled = cfg.securityReview.enable;
      operatorCommand = lib.optionals (!cfg.securityReview.enable) operatorCommand;
      inherit overrideCommand;
      notifySend = "${pkgs.libnotify}/bin/notify-send";
      reviewHome = "${user.homeDirectory}/.local/state/phoenix-agent-review";
      codex = if cfg.securityReview.enable then "${reviewerCodexPackage}/bin/codex" else null;
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
      sourceSelector = toString sourceSelector;
      modelReviewEnabled = cfg.securityReview.enable;
      operatorCommand = lib.optionals (!cfg.securityReview.enable) operatorCommand;
      inherit overrideCommand;
      notifySend = "${pkgs.libnotify}/bin/notify-send";
      git = "${pkgs.git}/bin/git";
      deploymentSocket = "/run/phoenix-deploy/control.sock";
      clientOnly = true;
      sandboxClient = true;
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
      exec ${reviewerCodexPackage}/bin/codex login status
    fi
    exec ${reviewerCodexPackage}/bin/codex login "$@"
  '';
  reviewLogin = pkgs.writeShellScriptBin "phoenix-review-login" ''
    export CODEX_HOME="${user.homeDirectory}/.local/state/phoenix-agent-review"
    ${pkgs.coreutils}/bin/install -d -m 700 "$CODEX_HOME"
    exec ${pkgs.util-linux}/bin/flock "$CODEX_HOME/migration.lock" ${reviewLoginCommand} "$@"
  '';
  deploymentConfig = pkgs.writeText "phoenix-deployment.json" (
    builtins.toJSON {
      modelReviewEnabled = cfg.securityReview.enable;
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
      securityReviewScript = toString ./security-review.py;
      securityReviewState = "/var/lib/phoenix-deploy/security-review";
      routineUpdateScript = toString ./routine-update.py;
      system = pkgs.stdenv.hostPlatform.system;
      python = "${pkgs.python3}/bin/python3";
      setpriv = "${pkgs.util-linux}/bin/setpriv";
      nix = "${pkgs.nix}/bin/nix";
      nixStore = "${pkgs.nix}/bin/nix-store";
      nixEnv = "${pkgs.nix}/bin/nix-env";
      systemdRun = "${pkgs.systemd}/bin/systemd-run";
      codex = if cfg.securityReview.enable then "${reviewerCodexPackage}/bin/codex" else null;
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
  imports = [ ./security-review.nix ];
  config = {
    system.build.phoenixDeploymentClient = deployReview;
    system.build.phoenixDeploymentSandboxClient = deployClient;
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
    ]
    ++ lib.optionals cfg.securityReview.enable [
      reviewLogin
      bootstrap
    ];
    # Fresh authentication, never auth_admin_keep: a rejected review is critical.
    # This policy is absent while the experimental security-review switch is off.
    environment.etc = lib.mkMerge [
      { "phoenix-agent/activated-source".source = inputs.self.outPath; }
      (lib.optionalAttrs cfg.securityReview.enable {
        "phoenix-agent/review-policy.md".source = ./review-policy.md;
        "polkit-1/actions/org.phoenix.security-review.policy".text = ''
          <?xml version="1.0" encoding="UTF-8"?>
          <!DOCTYPE policyconfig PUBLIC "-//freedesktop//DTD PolicyKit Policy Configuration 1.0//EN" "http://www.freedesktop.org/standards/PolicyKit/1/policyconfig.dtd">
          <policyconfig>
            <action id="org.phoenix.security-review.override">
              <description>Override a failed deployment security review</description>
              <message>CRITICAL: A deployment security review failed. Read its rejection and verify the frozen change before authenticating. This authorizes only the protected pending request: $(command_line)</message>
              <icon_name>dialog-warning</icon_name>
              <defaults><allow_any>no</allow_any><allow_inactive>no</allow_inactive><allow_active>auth_admin</allow_active></defaults>
              <annotate key="org.freedesktop.policykit.exec.path">${securityOverride}</annotate>
            </action>
          </policyconfig>
        '';
      })
    ];
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
    systemd.tmpfiles.rules =
      lib.optionals cfg.securityReview.enable [
        "d /var/lib/phoenix-deploy/security-review 0700 root root -"
      ]
      ++ [
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
      description = "Authenticated NixOS deployment controller";
      requires = [ "phoenix-deploy.socket" ];
      after = [
        "phoenix-deploy.socket"
        "nix-daemon.socket"
      ];
      # Reload asks for a clean exit after the active request/response; systemd
      # starts the installed ExecStart. Never kill the authorizing request midway.
      # Legacy controllers lack the handler: the guarded reload leaves them alive
      # for a one-time authenticated restart during migration.
      reloadIfChanged = true;
      restartIfChanged = false;
      stopIfChanged = false;
      serviceConfig = {
        ExecStart = "${pkgs.python3}/bin/python3 -I ${./deployment.py} ${deploymentConfig} serve";
        User = "root";
        UMask = "0077";
        ExecReload = pkgs.writeShellScript "phoenix-deploy-reload" ''
          while read -r key value rest; do
            if [ "$key" = SigCgt: ]; then
              if (( (16#$value & (1 << 9)) != 0 )); then
                exec ${pkgs.coreutils}/bin/kill -USR1 "$MAINPID"
              fi
              echo 'Legacy deployment controller: one initial authenticated restart required.'
              exit 0
            fi
          done < "/proc/$MAINPID/status"
          exit 1
        '';
        Restart = "always";
        KillMode = "process";
      };
    };
  };
}
