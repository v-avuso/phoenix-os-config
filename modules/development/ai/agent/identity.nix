{
  config,
  lib,
  pkgs,
  user,
  phoenixAgentLauncherConfig,
  phoenixAgentGatewayConfig,
  phoenixAgentPackages,
  ...
}:
let
  cfg = config.phoenix.agent.identity;
  operator = config.users.users.${user.name};
  state = "/var/lib/phoenix-agent";
  runtime = "/run/phoenix-agent";
  userRuntime = "/run/user/${toString cfg.uid}";
  excludedUserUnits = [ "gcr-ssh-agent" "pipewire" "pipewire-pulse" "speech-dispatcher" "podman" ];
  excludeAgent = _: {
    overrideStrategy = "asDropin";
    unitConfig.ConditionUser = lib.mkAfter [ "!phoenix-agent" ];
  };
  environment = {
    HOME = "${state}/home";
    XDG_CONFIG_HOME = "${state}/config";
    XDG_STATE_HOME = state;
    XDG_DATA_HOME = "${state}/data";
    XDG_RUNTIME_DIR = userRuntime;
    OPENSHELL_LOCAL_TLS_DIR = "${state}/tls";
    PATH =
      (lib.makeBinPath [
        pkgs.coreutils
        pkgs.openssh
        pkgs.podman
        # Podman healthcheck timers invoke systemd-run --user by name.
        pkgs.systemd
      ])
      + ":/run/wrappers/bin";
    TERM = "xterm-256color";
  };
  homeBinds =
    [ userRuntime ] ++ config.phoenix.agent.workspaces
    ++ map (name: "-${user.homeDirectory}/.codex/${name}") [
      "sessions"
      "archived_sessions"
      "thread-writer-locks"
    ]
    ++ [
      "-${user.homeDirectory}/.local/state/phoenix-openshell/history"
      "-${user.homeDirectory}/.local/state/phoenix-openshell/history.lock"
    ];
  transportConfig = pkgs.writeText "phoenix-agent-identity-launch.json" (
    builtins.toJSON {
      operatorUid = operator.uid;
      socket = "${runtime}/launch.sock";
      workspaces = config.phoenix.agent.workspaces;
      command = [
        "${pkgs.python3}/bin/python3"
        "-I"
        (toString ./launch.py)
        (toString phoenixAgentLauncherConfig)
      ];
      inherit environment;
    }
  );
  launch = pkgs.writeShellScriptBin "phoenix-agent-launch" ''
    exec ${pkgs.python3}/bin/python3 -I ${./identity-transport.py} --client ${transportConfig} "$@"
  '';
  setupConfig = pkgs.writeText "phoenix-agent-identity-setup.json" (
    builtins.toJSON {
      inherit state;
      uid = cfg.uid;
      gid = cfg.gid;
      subordinateStart = cfg.subordinateStart;
      subordinateCount = cfg.subordinateCount;
      operatorUid = operator.uid;
      operatorHome = user.homeDirectory;
      oldState = "${user.homeDirectory}/.local/state/phoenix-openshell";
      nativeHome = "${user.homeDirectory}/.codex";
      historyRoot = "${user.homeDirectory}/.local/state/phoenix-openshell/history";
      historyRuntime = toString ./history-runtime.py;
      cp = "${pkgs.coreutils}/bin/cp";
      setfacl = "${pkgs.acl}/bin/setfacl";
      workspaces = config.phoenix.agent.workspaces;
      historyDirectories =
        map (name: "${user.homeDirectory}/.codex/${name}") [
          "sessions"
          "archived_sessions"
          "thread-writer-locks"
        ]
        ++ [ "${user.homeDirectory}/.local/state/phoenix-openshell/history" ];
      historyFiles = [ "${user.homeDirectory}/.local/state/phoenix-openshell/history.lock" ];
    }
  );
  setup = pkgs.writeShellScriptBin "phoenix-agent-identity-setup" ''
    exec ${pkgs.python3}/bin/python3 -I ${./identity-setup.py} ${setupConfig}
  '';
  overlaps =
    start: count: otherStart: otherCount:
    start < otherStart + otherCount && otherStart < start + count;
  otherUsers = lib.filterAttrs (name: _: name != "phoenix-agent") config.users.users;
in
{
  options.phoenix.agent.identity = {
    enable = lib.mkEnableOption "dedicated protected OpenShell identity (isolated acceptance required)";
    uid = lib.mkOption {
      type = lib.types.ints.positive;
      default = 980;
      description = "Stable dedicated agent host UID.";
    };
    gid = lib.mkOption {
      type = lib.types.ints.positive;
      default = 980;
      description = "Stable dedicated agent host GID.";
    };
    subordinateStart = lib.mkOption {
      type = lib.types.ints.positive;
      default = 300000;
      description = "Start of dedicated rootless Podman UID/GID range.";
    };
    subordinateCount = lib.mkOption {
      type = lib.types.ints.positive;
      default = 65536;
      description = "Size of dedicated subordinate UID/GID range.";
    };
  };
  config = lib.mkIf cfg.enable {
    assertions = [
      {
        assertion =
          cfg.uid != operator.uid
          && !(lib.any (entry: (entry.uid or null) == cfg.uid) (builtins.attrValues otherUsers));
        message = "Agent identity UID must be distinct from all existing accounts.";
      }
      {
        assertion =
          !(lib.any (entry: (entry.gid or null) == cfg.gid) (
            builtins.attrValues (lib.filterAttrs (name: _: name != "phoenix-agent") config.users.groups)
          ));
        message = "Agent identity GID must be distinct from all existing groups.";
      }
      {
        assertion =
          cfg.subordinateCount >= 65536
          && cfg.subordinateStart + cfg.subordinateCount <= 4294967295
          && cfg.subordinateStart > cfg.uid
          && cfg.subordinateStart > cfg.gid
          && cfg.subordinateStart > operator.uid
          && !(lib.any (
            range: overlaps cfg.subordinateStart cfg.subordinateCount range.startUid range.count
          ) (lib.concatMap (entry: entry.subUidRanges or [ ]) (builtins.attrValues otherUsers)))
          && !(lib.any (
            range: overlaps cfg.subordinateStart cfg.subordinateCount range.startGid range.count
          ) (lib.concatMap (entry: entry.subGidRanges or [ ]) (builtins.attrValues otherUsers)));
        message = "Dedicated agent subordinate ranges must not overlap existing rootless accounts.";
      }
      {
        assertion = lib.all (
          root:
          lib.hasPrefix "/" root
          && root != "/"
          && root != user.homeDirectory
          && !(lib.hasPrefix (root + "/") user.homeDirectory)
          && !(lib.hasSuffix "/" root)
          && !(lib.hasInfix "/../" root)
          && !(lib.hasInfix "/./" root)
        ) config.phoenix.agent.workspaces;
        message = "Protected agent workspaces must be narrow normalized absolute paths.";
      }
    ];
    environment.systemPackages = [
      launch
      setup
    ];
    users.groups.phoenix-agent.gid = cfg.gid;
    users.users.phoenix-agent = {
      isSystemUser = true;
      uid = cfg.uid;
      group = "phoenix-agent";
      home = "${state}/home";
      createHome = true;
      autoSubUidGidRange = false;
      subUidRanges = [
        {
          startUid = cfg.subordinateStart;
          count = cfg.subordinateCount;
        }
      ];
      subGidRanges = [
        {
          startGid = cfg.subordinateStart;
          count = cfg.subordinateCount;
        }
      ];
    };
    systemd.tmpfiles.rules = [
      "d ${state} 0700 phoenix-agent phoenix-agent -"
      "d ${state}/config 0700 phoenix-agent phoenix-agent -"
      "d ${state}/data 0700 phoenix-agent phoenix-agent -"
      "d ${runtime} 0711 root root -"
      "d ${runtime}/private 0700 phoenix-agent phoenix-agent -"
    ];
    # Podman healthchecks execute in this real user manager, so preserve the same
    # namespace and storage environment for its children, not only the API service.
    systemd.services."user@${toString cfg.uid}" = {
      overrideStrategy = "asDropin";
      environment = environment // { PATH = lib.mkForce environment.PATH; };
      serviceConfig = { ProtectHome = "tmpfs"; BindPaths = homeBinds; };
    };
    # Global desktop/API units are not useful to the protected service account.
    # Conditions append to upstream constraints and leave operator units usable.
    systemd.user.services = lib.genAttrs excludedUserUnits excludeAgent;
    systemd.user.sockets = lib.genAttrs excludedUserUnits excludeAgent;
    systemd.services.phoenix-agent-podman = {
      requires = [ "user@${toString cfg.uid}.service" ];
      after = [ "user@${toString cfg.uid}.service" ];
      serviceConfig = {
        ProtectHome = "tmpfs";
        BindPaths = homeBinds;
        User = "phoenix-agent";
        Group = "phoenix-agent";
        ExecStart = "${pkgs.podman}/bin/podman system service --time=0 unix:${runtime}/private/podman.sock";
        Delegate = true;
        UMask = "0077";
        Restart = "on-failure";
      };
      environment = environment // {
        PATH = lib.mkForce environment.PATH;
      };
    };
    systemd.services.phoenix-agent-gateway = {
      requires = [ "phoenix-agent-podman.service" ];
      after = [ "phoenix-agent-podman.service" ];
      environment = environment // {
        PATH = lib.mkForce environment.PATH;
        OPENSHELL_GATEWAY_CONFIG = toString phoenixAgentGatewayConfig;
      };
      serviceConfig = {
        ProtectHome = "tmpfs";
        BindPaths = homeBinds;
        User = "phoenix-agent";
        Group = "phoenix-agent";
        ExecStartPre = [
          "${pkgs.coreutils}/bin/test -f ${state}/identity-ready"
          "${phoenixAgentPackages.gateway}/bin/openshell-gateway config preflight"
          "${phoenixAgentPackages.gateway}/bin/openshell-gateway generate-certs --output-dir ${state}/tls --server-san 127.0.0.1 --server-san localhost --server-san host.openshell.internal"
        ];
        ExecStart = "${phoenixAgentPackages.gateway}/bin/openshell-gateway";
        ExecStartPost = "${pkgs.curl}/bin/curl --fail --silent --show-error --output /dev/null --max-time 3 --retry 5 --retry-connrefused --retry-max-time 20 http://127.0.0.1:17671/readyz";
        Delegate = true;
        UMask = "0077";
        Restart = "on-failure";
        TimeoutStartSec = "30s";
      };
    };
    systemd.sockets.phoenix-agent-launch = {
      wantedBy = [ "sockets.target" ];
      socketConfig = {
        ListenStream = "${runtime}/launch.sock";
        SocketUser = user.name;
        SocketMode = "0600";
        Accept = true;
        MaxConnections = 8;
        RemoveOnStop = true;
      };
    };
    systemd.services."phoenix-agent-launch@" = {
      requires = [ "phoenix-agent-gateway.service" ];
      after = [ "phoenix-agent-gateway.service" ];
      serviceConfig = {
        ProtectHome = "tmpfs";
        BindPaths = homeBinds;
        User = "phoenix-agent";
        Group = "phoenix-agent";
        ExecStart = "${pkgs.python3}/bin/python3 -I ${./identity-transport.py} --serve ${transportConfig}";
        StandardInput = "socket";
        StandardOutput = "journal";
        StandardError = "journal";
        Delegate = true;
        UMask = "0002";
        KillMode = "control-group";
        TimeoutStopSec = "10s";
      };
      environment = environment // {
        PATH = lib.mkForce environment.PATH;
      };
    };
  };
}
