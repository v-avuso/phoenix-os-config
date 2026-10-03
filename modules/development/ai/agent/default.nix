{
  config,
  lib,
  pkgs,
  user,
  codexCliPackage,
  phoenixAdminPackage,
  phoenixAgentCodexConfig,
  phoenixDeployReviewPackage,
  ...
}:
let
  cfg = config.phoenix.agent;
  packages = import ./packages.nix { inherit pkgs; };
  image = import ./image.nix {
    inherit
      pkgs
      codexCliPackage
      phoenixAdminPackage
      phoenixAgentCodexConfig
      phoenixDeployReviewPackage
      ;
  };
  formats = pkgs.formats.toml { };
  yaml = pkgs.formats.yaml { };
  state = "${user.homeDirectory}/.local/state/phoenix-openshell";
  gatewayConfig = formats.generate "phoenix-openshell-gateway.toml" {
    openshell = {
      version = 2;
      gateway = {
        name = "openshell";
        bind_address = "127.0.0.1:17670";
        health_bind_address = "127.0.0.1:17671";
        compute_driver = "podman";
        log_level = "info";
      };
      drivers.podman = {
        socket_path = "/run/user/1000/phoenix-openshell-podman.sock";
        default_image = "localhost/phoenix-codex:0.1.2";
        image_pull_policy = "never";
        sandbox_runtime_image = "ghcr.io/nvidia/openshell/sandbox@sha256:bf4797b6c511f2d8ba02955dbba4bf76c1f0dd6d83531420c5408d5f1fb9d72f";
        supervisor_image = "ghcr.io/nvidia/openshell/supervisor@sha256:d7b5264bb6bc56f4796e6fa3617b8e4a8d785be0b7293542efd8cc250b0fb67a";
        userns = "keep-id:uid=1000,gid=1000";
        allow_driver_config = true;
        enable_bind_mounts = true;
        resource_admission.enabled = false;
        sandbox_pids_limit = 512;
      };
    };
  };
  policy = yaml.generate "phoenix-openshell-policy.yaml" {
    version = 1;
    filesystem_policy = {
      include_workdir = false;
      read_only = [
        "/etc"
        "/bin"
        "/usr"
        "/proc"
        "/sys"
        "/dev"
        "/run/phoenix-admin"
        "/run/phoenix-deploy"
      ];
      read_write = [
        "/sandbox"
        "/tmp"
        "/nix"
        "/dev/null"
        "/dev/pts"
      ]
      ++ cfg.workspaces;
    };
    landlock.compatibility = "hard_requirement";
    process = {
      run_as_user = "1000";
      run_as_group = "1000";
    };
    network_policies = {
      codex = {
        name = "codex";
        endpoints =
          map
            (host: {
              inherit host;
              port = 443;
              protocol = "rest";
              enforcement = "enforce";
              access = "read-write";
            })
            [
              "api.openai.com"
              "auth.openai.com"
              "chatgpt.com"
              "ab.chatgpt.com"
            ];
        binaries = [ { path = "${codexCliPackage}/bin/codex"; } ];
      };
      gui_http = {
        name = "gui_http";
        endpoints = [
          {
            host = "chatgpt.com";
            port = 443;
            protocol = "rest";
            enforcement = "enforce";
            rules =
              lib.concatMap
                (
                  method:
                  map (path: { allow = { inherit method path; }; }) [
                    "/backend-api/**"
                    "/api/codex/**"
                  ]
                )
                [
                  "GET"
                  "HEAD"
                  "POST"
                  "PUT"
                  "PATCH"
                  "DELETE"
                ];
          }
        ];
        # Python is an interpreter, not fixed-script identity. Its whole egress
        # authority is limited to these desktop API namespaces; gateway handle
        # resolution follows L7 admission and remains endpoint-scoped.
        binaries = [ { path = "${pkgs.python3}/bin/python${pkgs.python3.pythonVersion}"; } ];
      };
      development = {
        name = "development";
        endpoints = map (host: {
          inherit host;
          port = 443;
          protocol = "rest";
          enforcement = "enforce";
          rules = [
            {
              allow.method = "GET";
              allow.path = "/**";
            }
            {
              allow.method = "HEAD";
              allow.path = "/**";
            }
          ];
        }) cfg.developmentHosts;
        # Public read access is useful to arbitrary development tools. No
        # wildcard hosts, raw tunnels, SSH, PUT/POST, or local-service access.
        binaries = [ { path = "/**"; } ];
      };
      git = {
        name = "git";
        endpoints = [
          {
            host = "github.com";
            port = 443;
            protocol = "rest";
            enforcement = "enforce";
            rules = [
              {
                allow.method = "GET";
                allow.path = "/**";
              }
              {
                allow.method = "POST";
                allow.path = "/*/*/git-upload-pack";
              }
            ];
          }
        ];
        binaries = [ { path = "${pkgs.git}/**"; } ];
      };
    };
  };
  driverConfig = pkgs.writeText "phoenix-openshell-mounts.json" (
    builtins.toJSON {
      podman.mounts =
        (map (path: {
          type = "bind";
          source = path;
          target = path;
          read_only = false;
        }) cfg.workspaces)
        ++ [
          {
            type = "bind";
            source = "/sys";
            target = "/sys";
            read_only = true;
          }
          {
            type = "bind";
            source = "/run/phoenix-admin";
            target = "/run/phoenix-admin";
            read_only = true;
          }
          {
            type = "bind";
            source = "/run/phoenix-deploy";
            target = "/run/phoenix-deploy";
            read_only = true;
          }
          # Present the protected source as the reviewed immutable snapshot too.
          {
            type = "bind";
            source = "${./.}";
            target = "${user.repoDirectory}/modules/development/ai/agent";
            read_only = true;
          }
        ];
    }
  );
  launcherConfig = pkgs.writeText "phoenix-openshell-launcher.json" (
    builtins.toJSON {
      openshell = "${packages.cli}/bin/openshell";
      native = "${codexCliPackage}/bin/codex";
      podman = "${pkgs.podman}/bin/podman";
      systemctl = "${pkgs.systemd}/bin/systemctl";
      ssh = "${pkgs.openssh}/bin/ssh";
      image = toString image;
      policy = toString policy;
      mounts = toString driverConfig;
      profile = toString (
        pkgs.writeText "phoenix-codex-provider.yaml" (
          builtins.replaceStrings [ "@CODEX_BINARY@" ] [ "${codexCliPackage}/bin/codex" ] (
            builtins.readFile ./codex-provider.yaml
          )
        )
      );
      workspaces = cfg.workspaces;
      appServerPreferences = [
        "${pkgs.python3}/bin/python3" "-I" (toString ./gui-profile.py)
        "--worker" "${user.homeDirectory}/.codex/config.toml"
      ];
      default_workdir = user.repoDirectory;
      inherit state;
    }
  );
  launchers = pkgs.writeShellScriptBin "codex" ''
    exec ${pkgs.python3}/bin/python3 -I ${./launch.py} ${launcherConfig} "$@"
  '';
  native = pkgs.writeShellScriptBin "codex-native" ''
    exec ${codexCliPackage}/bin/codex "$@"
  '';
  login = pkgs.writeShellScriptBin "codex-sandbox-login" ''
    exec ${pkgs.python3}/bin/python3 -I ${./launch.py} ${launcherConfig} --phoenix-login
  '';
  sandboxExec = pkgs.writeShellScriptBin "codex-sandbox-exec" ''
    exec ${pkgs.python3}/bin/python3 -I ${./launch.py} ${launcherConfig} --phoenix-exec "$@"
  '';
in
{
  imports = [ ./broker.nix ];
  options.phoenix.agent = {
    workspaces = lib.mkOption {
      type = lib.types.listOf lib.types.str;
      default = [
        "${user.homeDirectory}/repos/code"
        "${user.homeDirectory}/Projects"
      ];
      description = "Explicit existing host directories mounted writable into Codex; never the home itself.";
    };
    developmentHosts = lib.mkOption {
      type = lib.types.listOf lib.types.str;
      default = [
        "github.com"
        "api.github.com"
        "raw.githubusercontent.com"
        "objects.githubusercontent.com"
        "codeload.github.com"
        "gitlab.com"
        "cache.nixos.org"
        "channels.nixos.org"
        "releases.nixos.org"
        "registry.npmjs.org"
        "pypi.org"
        "files.pythonhosted.org"
        "crates.io"
        "static.crates.io"
        "index.crates.io"
        "docs.nvidia.com"
        "developers.openai.com"
        "learn.chatgpt.com"
        "nixos.org"
        "nixos.wiki"
        "wiki.nixos.org"
        "search.nixos.org"
        "www.kernel.org"
        "docs.kernel.org"
        "www.freedesktop.org"
      ];
      description = "Exact HTTPS destinations granted public GET/HEAD access; policy changes need Native Codex.";
    };
  };
  config = {
    _module.args.phoenixAgentImage = image;
    _module.args.phoenixAgentPackages = packages;
    _module.args.phoenixAgentLauncherConfig = launcherConfig;
    environment.systemPackages = [
      packages.cli
      packages.gateway
      launchers
      native
      login
      sandboxExec
    ];
    environment.etc."phoenix-openshell/gateway.toml".source = gatewayConfig;
    virtualisation.podman.enable = true;
    home-manager.users.${user.name} = {
      systemd.user.services.phoenix-openshell-podman = {
        Unit.Description = "Dedicated rootless Podman API for OpenShell";
        Service = {
          ExecStart = "${pkgs.podman}/bin/podman system service --time=0 unix:%t/phoenix-openshell-podman.sock";
          Restart = "on-failure";
          UMask = "0077";
        };
      };
      systemd.user.services.phoenix-openshell-gateway = {
        Unit = {
          Description = "Phoenix OpenShell gateway (rootless, private credentials)";
          Requires = [ "phoenix-openshell-podman.service" ];
          After = [ "phoenix-openshell-podman.service" ];
        };
        Service = {
          Environment = [
            "OPENSHELL_LOCAL_TLS_DIR=${state}/tls"
            "OPENSHELL_GATEWAY_CONFIG=${gatewayConfig}"
            "XDG_STATE_HOME=${state}"
          ];
          ExecStartPre = [
            "${packages.gateway}/bin/openshell-gateway config preflight"
            "${packages.gateway}/bin/openshell-gateway generate-certs --output-dir ${state}/tls --server-san 127.0.0.1 --server-san localhost --server-san host.openshell.internal"
          ];
          ExecStart = "${packages.gateway}/bin/openshell-gateway";
          # Supported readiness endpoint, bounded startup failure. No fixed
          # sleep: systemctl start completes only after the database is ready.
          ExecStartPost = "${pkgs.curl}/bin/curl --fail --silent --show-error --output /dev/null --max-time 3 --retry 5 --retry-connrefused --retry-max-time 20 http://127.0.0.1:17671/readyz";
          TimeoutStartSec = "30s";
          Restart = "on-failure";
          RestartSec = "5s";
          UMask = "0077";
        };
        Install.WantedBy = [ "default.target" ];
      };
      xdg.desktopEntries.codex-sandboxed = {
        name = "Codex (Sandboxed)";
        comment = "OpenShell-protected Codex CLI with bounded host diagnostics";
        exec = "${launchers}/bin/codex";
        icon = "codex-desktop";
        terminal = true;
        type = "Application";
        categories = [ "Development" ];
      };
      xdg.desktopEntries.codex-native = {
        name = "Codex CLI (Native / Unrestricted)";
        comment = "Direct host CLI for policy repair and deliberate administrative work";
        exec = "${native}/bin/codex-native";
        icon = "dialog-warning";
        terminal = true;
        type = "Application";
        categories = [ "Development" ];
      };
    };
  };
}
