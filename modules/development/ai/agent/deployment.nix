{
  config,
  pkgs,
  user,
  inputs,
  lib,
  phoenixReservationSettings ? null,
  ...
}:
let
  cfg = config.services.phoenixDeployment;
  installedTarget = config.phoenix.target;
  authorizationPolicy = toString config.system.build.phoenixAuthorizationPolicy;
  authorizationLibrary = toString config.system.build.phoenixAuthorizationLibrary;
  transportPolicy = pkgs.writeText "phoenix-deployment-transport.json" (builtins.readFile ./transport.json);
  sourceManifestLibrary = toString (pkgs.writeText "phoenix-source-manifest.py" (builtins.readFile ./source-manifest.py));
  controllerScript = pkgs.replaceVars ./deployment.py { deploymentTransportPolicy = toString transportPolicy; inherit authorizationLibrary sourceManifestLibrary; };
  reviewScript = pkgs.replaceVars ./deploy-review.py { deploymentTransportPolicy = toString transportPolicy; inherit authorizationLibrary sourceManifestLibrary; };
  sourceSelector = pkgs.writeScript "phoenix-source" (
    builtins.replaceStrings [ "#!/usr/bin/env python3" ]
      [ "#!${pkgs.python3}/bin/python3" ] (builtins.readFile ../../../../commands/phoenix-source)
  );
  nativeDeployHelper = pkgs.writeShellScript "phoenix-deployment-authorize" ''
    if [ "$#" -ne 0 ]; then exit 2; fi
    exec ${pkgs.python3}/bin/python3 -I ${controllerScript} ${deploymentConfig} operator
  '';
  operatorCommand = [ "/run/wrappers/bin/pkexec" "--disable-internal-agent" (toString nativeDeployHelper) ];
  commandLibrary = pkgs.writeText "phoenix-command-policy.py" (builtins.readFile ./authorization/command-policy.py);
  commandPolicy = pkgs.writeText "phoenix-command-review-policy.md" (builtins.readFile ./authorization/command-review-policy.md);
  commandPublication = pkgs.writeText "phoenix-command-authority.json" (builtins.toJSON {
    registry = config.phoenix.authorization.commands;
    executor = builtins.hashString "sha256" (builtins.readFile ./authorization/command-exec.py);
    operatorUid = config.users.users.${user.name}.uid;
    clientUid = if config.phoenix.agent.identity.enable then config.phoenix.agent.identity.uid else config.users.users.${user.name}.uid;
    implementation = builtins.hashString "sha256" (builtins.readFile ./authorization/command-policy.py);
    controller = builtins.hashString "sha256" (builtins.readFile ./deployment.py);
    review = builtins.hashString "sha256" (builtins.readFile ./deploy-review.py);
    sourceManifest = builtins.hashString "sha256" (builtins.readFile ./source-manifest.py);
    prompt = builtins.hashString "sha256" (builtins.readFile ./authorization/command-review-policy.md);
    provider = if cfg.securityReview.enable then toString reviewerCodexPackage else null;
    inherit (cfg.securityReview) adapter model effort;
    reviewerUser = "phoenix-deploy-review";
    inherit (config.phoenix.agent) identity;
  });
  commandHelper = pkgs.writeShellScript "phoenix-command-authorize" ''
    if [ "$#" -ne 0 ]; then exit 2; fi
    exec ${pkgs.python3}/bin/python3 -I ${controllerScript} ${deploymentConfig} command-operator
  '';
  commandCriticalHelper = pkgs.writeShellScript "phoenix-command-critical-override" ''
    if [ "$#" -ne 0 ]; then exit 2; fi
    exec ${pkgs.python3}/bin/python3 -I ${controllerScript} ${deploymentConfig} command-critical
  '';
  commandClient = sandbox: let
    clientSettings = pkgs.writeText "phoenix-command-client.json" (builtins.toJSON {
      socket = "/run/phoenix-deploy/control.sock";
      authority = toString commandPublication;
      operatorCommand = lib.optionals (!sandbox) [ "/run/wrappers/bin/pkexec" "--disable-internal-agent" (toString commandHelper) ];
      criticalCommand = lib.optionals (!sandbox) [ "/run/wrappers/bin/pkexec" "--disable-internal-agent" (toString commandCriticalHelper) ];
    });
  in pkgs.writeShellScriptBin "phoenix-command" ''
    exec ${pkgs.python3}/bin/python3 -I ${./authorization/command-client.py} ${clientSettings} "$@"
  '';
  # The caller supplies only a protected pending-record nonce. The controller
  # validates UID, policy, source/closure, target/action and current baseline;
  # no caller-provided command, store path or source is accepted here.
  securityOverride = pkgs.writeShellScript "phoenix-security-review-override" ''
    if [ "$#" -ne 1 ]; then exit 2; fi
    exec ${pkgs.python3}/bin/python3 -I ${controllerScript} ${deploymentConfig} override "$1"
  '';
  overrideCommand = lib.optionals cfg.securityReview.enable [
    "/run/wrappers/bin/pkexec"
    "--disable-internal-agent"
    (toString securityOverride)
  ];
  trustActiveHelper = pkgs.writeShellScript "phoenix-security-review-trust-active" ''
    if [ "$#" -ne 0 ]; then exit 2; fi
    exec ${pkgs.python3}/bin/python3 -I ${controllerScript} ${deploymentConfig} trust-active
  '';
  trustActive = pkgs.writeShellScriptBin "phoenix-review-trust-active" ''
    if [ "$#" -ne 0 ]; then exit 2; fi
    echo 'Trusting current active code for security review testing; no model, build or activation.' >&2
    exec /run/wrappers/bin/pkexec --disable-internal-agent ${trustActiveHelper}
  '';
  disruptionOverride = pkgs.writeShellScript "phoenix-disruption-override" ''
    if [ "$#" -ne 1 ]; then exit 2; fi
    exec ${pkgs.python3}/bin/python3 -I ${controllerScript} ${deploymentConfig} disruption-override "$1"
  '';
  disruptionOverrideCommand = lib.optionals cfg.disruptionGuard.enable [
    "/run/wrappers/bin/pkexec" "--disable-internal-agent" (toString disruptionOverride)
  ];
  # The privileged reviewer is a separate control-plane dependency. Everyday
  # CLI freshness must not silently replace the code enforcing review isolation.
  reviewerCodexPackage = pkgs.callPackage ./reviewer-codex.nix { };
  reviewConfig = pkgs.writeText "phoenix-review.json" (
    builtins.toJSON {
      repo = user.repoDirectory;
      sourceSelector = toString sourceSelector;
      reservationAdapter = if config.phoenix.agent.reservations.enable then phoenixReservationSettings.adapter else null;
      inherit authorizationPolicy;
      authorizationPresentation = toString config.system.build.phoenixAuthorizationPresentation;
      authorizationLibrary = authorizationLibrary;
      deploymentTransportPolicy = toString transportPolicy;
      inherit sourceManifestLibrary;
      securityIdentityVersion = 2;
      modelReviewEnabled = cfg.securityReview.enable;
      operatorCommand = lib.optionals (!cfg.securityReview.enable) operatorCommand;
      inherit overrideCommand disruptionOverrideCommand;
      disruptionInfo = "/run/phoenix-deploy";
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
      inherit (cfg.securityReview) adapter model effort;
      baseline = "/etc/phoenix-agent/activated-source";
      migrationMarker = "/var/lib/phoenix-deploy/reviewer-migrated";
      deploymentSocket = "/run/phoenix-deploy/control.sock";
    }
  );
  deployReview = pkgs.writeShellScriptBin "phoenix-deploy-review" ''
    exec ${pkgs.python3}/bin/python3 -I ${reviewScript} ${reviewConfig} "$@"
  '';
  clientConfig = pkgs.writeText "phoenix-deployment-client.json" (
    builtins.toJSON {
      repo = user.repoDirectory;
      sourceSelector = toString sourceSelector;
      reservationAdapter = if config.phoenix.agent.reservations.enable then phoenixReservationSettings.adapter else null;
      inherit authorizationPolicy;
      authorizationPresentation = toString config.system.build.phoenixAuthorizationPresentation;
      authorizationLibrary = authorizationLibrary;
      deploymentTransportPolicy = toString transportPolicy;
      inherit sourceManifestLibrary;
      securityIdentityVersion = 2;
      modelReviewEnabled = cfg.securityReview.enable;
      operatorCommand = lib.optionals (!cfg.securityReview.enable) operatorCommand;
      inherit overrideCommand disruptionOverrideCommand;
      disruptionInfo = "/run/phoenix-deploy";
      notifySend = "${pkgs.libnotify}/bin/notify-send";
      git = "${pkgs.git}/bin/git";
      deploymentSocket = "/run/phoenix-deploy/control.sock";
      clientOnly = true;
      sandboxClient = true;
    }
  );
  deployClient = pkgs.writeShellScriptBin "phoenix-deploy-review" ''
    exec ${pkgs.python3}/bin/python3 -I ${reviewScript} ${clientConfig} "$@"
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
    builtins.toJSON ({
      inherit authorizationPolicy;
      commandLibrary = toString commandLibrary;
      commandReviewPolicy = toString commandPolicy;
      commandAuthority = toString commandPublication;
      commandCurrentAuthority = "/etc/phoenix-authorization/command-authority.json";
      commands = config.phoenix.authorization.commands;
      commandState = "/var/lib/phoenix-deploy/commands";
      commandExec = toString (pkgs.writeText "phoenix-command-exec.py" (builtins.readFile ./authorization/command-exec.py));
      authorizationLibrary = authorizationLibrary;
      deploymentTransportPolicy = toString transportPolicy;
      inherit sourceManifestLibrary;
      securityIdentityVersion = 2;
      modelReviewEnabled = cfg.securityReview.enable;
      operatorName = user.name;
      disruptionScript = toString (pkgs.writeText "phoenix-disruption.py" (builtins.readFile ./disruption.py));
      disruptionState = "/var/lib/phoenix-deploy/disruption";
      disruptionInfo = "/run/phoenix-deploy";
      systemctl = "${pkgs.systemd}/bin/systemctl";
      disruptionGuard = {
        enable = cfg.disruptionGuard.enable;
        systemUnits = [ "display-manager.service" "systemd-logind.service" "systemd-user-sessions.service" "user@${toString config.users.users.${user.name}.uid}.service" ];
        userUnits = [ "hyprland-session.target" "graphical-session.target" "hypr-persist.service" "kando.service" "phoenix-timewall.service" "phoenix-timewall-theme.service" "phoenix-openshell-podman.service" "phoenix-openshell-gateway.service" "phoenix-agent-gui.socket" "phoenix-agent-gui-http.socket" "opensnitch-ui.service" ];
      };
      clientUid = if config.phoenix.agent.identity.enable then config.phoenix.agent.identity.uid else config.users.users.${user.name}.uid;
      operatorUid = config.users.users.${user.name}.uid;
      target = installedTarget;
      targetGuard = "${config.system.build.phoenixTarget}/bin/phoenix-target";
      reviewerUser = "phoenix-deploy-review";
      builderUser = "phoenix-deploy-build";
      reviewHome = "/var/lib/phoenix-deploy-review";
      migrationMarker = "/var/lib/phoenix-deploy/reviewer-migrated";
      loginHome = "${user.homeDirectory}/.local/state/phoenix-agent-review";
      work = "/var/lib/phoenix-deploy/requests";
      baseline = "/etc/phoenix-agent/activated-source";
      controller = toString controllerScript;
      reviewScript = toString reviewScript;
      securityReviewScript = toString (pkgs.writeText "phoenix-security-review.py" (builtins.readFile ./security-review.py));
      securityReviewState = "/var/lib/phoenix-deploy/security-review";
      routineUpdateScript = toString (pkgs.writeText "phoenix-routine-update.py" (builtins.readFile ./routine-update.py));
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
      inherit (cfg.securityReview) adapter model effort;
      activationLock = "/var/lib/phoenix-deploy/activation.lock";
      activationSpool = "/var/lib/phoenix-deploy/activation";
      activationEnvironment = {
        PATH = "/run/current-system/sw/bin:/run/current-system/sw/sbin";
        HOME = "/root";
      };
      activationEnvironmentTools = {
        LOCALE_ARCHIVE = "${pkgs.glibcLocales}/lib/locale/locale-archive";
      };
    } // lib.optionalAttrs config.phoenix.agent.reservations.enable { reservations = phoenixReservationSettings; })
  );
  bootstrap = pkgs.writeShellScriptBin "phoenix-deploy-bootstrap" ''
    exec /run/wrappers/bin/pkexec --disable-internal-agent ${pkgs.python3}/bin/python3 -I ${controllerScript} ${deploymentConfig} bootstrap
  '';

in
{
  imports = [ ./security-review.nix ./authorization ];
  options.services.phoenixDeployment.disruptionGuard.enable =
    lib.mkEnableOption "experimental protected desktop unit deployment guard";
  config = {
    system.build.phoenixCommandClient = commandClient false;
    system.build.phoenixCommandSandboxClient = commandClient true;

    system.build.phoenixDeploymentTransportPolicy = transportPolicy;
    system.build.phoenixSourceManifestLibrary = sourceManifestLibrary;
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
      trustActive
    ];
    # Fresh authentication, never auth_admin_keep: a rejected review is critical.
    # This policy is absent while the experimental security-review switch is off.
    environment.etc = lib.mkMerge [
      { "phoenix-authorization/command-authority.json".source = commandPublication; }

      {
        "phoenix-agent/activated-source".source = inputs.self.outPath;
        "phoenix-agent/active-provenance.json".text = builtins.toJSON {
          version = 1;
          target = installedTarget;
          source = toString inputs.self.outPath;
        };
      }
      (lib.optionalAttrs (!cfg.securityReview.enable) {
        "polkit-1/actions/org.phoenix.deployment.policy".text = ''
          <?xml version="1.0" encoding="UTF-8"?>
          <!DOCTYPE policyconfig PUBLIC "-//freedesktop//DTD PolicyKit Policy Configuration 1.0//EN" "http://www.freedesktop.org/standards/PolicyKit/1/policyconfig.dtd">
          <policyconfig><action id="org.phoenix.deployment.authorize">
            <description>Authorize an immutable Phoenix deployment</description>
            <message>Phoenix requests deployment of the frozen source shown in the terminal. This can change the system and interrupt services.</message>
            <icon_name>dialog-warning</icon_name>
            <defaults><allow_any>no</allow_any><allow_inactive>no</allow_inactive><allow_active>auth_admin</allow_active></defaults>
            <annotate key="org.freedesktop.policykit.exec.path">${nativeDeployHelper}</annotate>
          </action></policyconfig>
        '';
      })
      (lib.optionalAttrs cfg.disruptionGuard.enable {
        "polkit-1/actions/org.phoenix.disruption.policy".text = ''
          <?xml version="1.0" encoding="UTF-8"?>
          <!DOCTYPE policyconfig PUBLIC "-//freedesktop//DTD PolicyKit Policy Configuration 1.0//EN" "http://www.freedesktop.org/standards/PolicyKit/1/policyconfig.dtd">
          <policyconfig>
            <action id="org.phoenix.disruption.override">
              <description>Approve a protected desktop disruption exception</description>
              <message>WARNING: This deployment changes protected desktop units or cannot be inspected. Read the CLI findings before authenticating. This authorizes one exact pending activation and may interrupt your session.</message>
              <icon_name>dialog-warning</icon_name>
              <defaults><allow_any>no</allow_any><allow_inactive>no</allow_inactive><allow_active>auth_admin</allow_active></defaults>
              <annotate key="org.freedesktop.policykit.exec.path">${disruptionOverride}</annotate>
            </action>
          </policyconfig>
        '';
      })
      (lib.optionalAttrs config.phoenix.authorization.commands.enable {
        "polkit-1/actions/org.phoenix.command-critical.policy".text = ''
          <?xml version="1.0" encoding="UTF-8"?>
          <!DOCTYPE policyconfig PUBLIC "-//freedesktop//DTD PolicyKit Policy Configuration 1.0//EN" "http://www.freedesktop.org/standards/PolicyKit/1/policyconfig.dtd">
          <policyconfig><action id="org.phoenix.command.critical-override">
            <description>CRITICAL: override registered-command security review</description>
            <message>CRITICAL SECURITY OVERRIDE: authorize the exact installed command despite rejected or unavailable independent review. Read its command and context in the terminal.</message>
            <icon_name>dialog-warning</icon_name>
            <defaults><allow_any>no</allow_any><allow_inactive>no</allow_inactive><allow_active>auth_admin</allow_active></defaults>
            <annotate key="org.freedesktop.policykit.exec.path">${commandCriticalHelper}</annotate>
          </action></policyconfig>
        '';
        "polkit-1/actions/org.phoenix.command.policy".text = ''
          <?xml version="1.0" encoding="UTF-8"?>
          <!DOCTYPE policyconfig PUBLIC "-//freedesktop//DTD PolicyKit Policy Configuration 1.0//EN" "http://www.freedesktop.org/standards/PolicyKit/1/policyconfig.dtd">
          <policyconfig><action id="org.phoenix.command.authorize">
            <description>Authenticate an exact installed Phoenix command</description>
            <message>Authenticate the exact registered command shown in the terminal. Task and reason are context, not authority.</message>
            <defaults><allow_any>no</allow_any><allow_inactive>no</allow_inactive><allow_active>auth_admin</allow_active></defaults>
            <annotate key="org.freedesktop.policykit.exec.path">${commandHelper}</annotate>
          </action></policyconfig>
        '';
      })
      (lib.optionalAttrs cfg.securityReview.enable {
        "phoenix-agent/review-policy.md".source = ./review-policy.md;
        "polkit-1/actions/org.phoenix.security-review-baseline.policy".text = ''
          <?xml version="1.0" encoding="UTF-8"?>
          <!DOCTYPE policyconfig PUBLIC "-//freedesktop//DTD PolicyKit Policy Configuration 1.0//EN" "http://www.freedesktop.org/standards/PolicyKit/1/policyconfig.dtd">
          <policyconfig><action id="org.phoenix.security-review.trust-active">
            <description>Trust the current active Phoenix code for security review testing</description>
            <message>This adopts only the actual immutable running system as an explicitly trusted review checkpoint. Its existing code is not being reviewed. No deployment will run.</message>
            <icon_name>dialog-warning</icon_name>
            <defaults><allow_any>no</allow_any><allow_inactive>no</allow_inactive><allow_active>auth_admin</allow_active></defaults>
            <annotate key="org.freedesktop.policykit.exec.path">${trustActiveHelper}</annotate>
          </action></policyconfig>
        '';
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
      lib.optionals cfg.disruptionGuard.enable [ "d /var/lib/phoenix-deploy/disruption 0700 root root -" ]
      ++
      lib.optionals cfg.securityReview.enable [
        "d /var/lib/phoenix-deploy/security-review 0700 root root -"
      ]
      ++ [
        "d /var/lib/phoenix-deploy 0711 root root -"
        "d /var/lib/phoenix-deploy/activation 0700 root root -"
        "d /var/lib/phoenix-deploy/commands 0700 root root -"
        "d /var/lib/phoenix-deploy/requests 0711 root root -"
        "d /var/lib/phoenix-deploy-review 0700 phoenix-deploy-review phoenix-deploy-review -"
        "d /run/phoenix-deploy 0755 root root -"
      ];
    systemd.sockets.phoenix-deploy = {
      wantedBy = [ "sockets.target" ];
      socketConfig = {
        ListenStream = "/run/phoenix-deploy/control.sock";
        SocketMode = "0660";
        SocketGroup = "phoenix-authorization";
        SocketUser = if config.phoenix.agent.identity.enable then "phoenix-agent" else user.name;
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
        ExecStart = "${pkgs.python3}/bin/python3 -I ${controllerScript} ${deploymentConfig} serve";
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
