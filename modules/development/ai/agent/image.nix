{
  pkgs,
  codexCliPackage,
  phoenixAdminPackage,
  phoenixAgentCodexConfig,
  phoenixDeployReviewPackage,
}:
let
  tools = pkgs.buildEnv {
    name = "phoenix-agent-tools";
    paths = [
      codexCliPackage
      phoenixAdminPackage
      phoenixDeployReviewPackage
      pkgs.bashInteractive
      pkgs.coreutils
      pkgs.findutils
      pkgs.gnugrep
      pkgs.gnused
      pkgs.gawk
      pkgs.git
      pkgs.curl
      pkgs.cacert
      pkgs.ripgrep
      pkgs.python3
      pkgs.nix
      pkgs.nixfmt
      pkgs.util-linux
      pkgs.procps
      pkgs.pciutils
      pkgs.usbutils
      pkgs.strace
      pkgs.openssh
      pkgs.less
    ];
    pathsToLink = [ "/bin" ];
  };
  etc = pkgs.runCommand "phoenix-agent-etc" { } ''
    mkdir -p "$out/etc/nix" "$out/etc/codex" "$out/usr/bin"
    printf 'root:x:0:0:root:/root:/bin/sh\nsandbox:x:1000:1000:Sandbox:/sandbox:/bin/bash\n' > "$out/etc/passwd"
    printf 'root:x:0:\nsandbox:x:1000:\n' > "$out/etc/group"
    printf 'hosts: files dns\n' > "$out/etc/nsswitch.conf"
    cat > "$out/etc/nix/nix.conf" <<'EOF'
    experimental-features = nix-command flakes
    sandbox = false
    # OpenShell already owns seccomp; nested filter installation is denied.
    filter-syscalls = false
    build-users-group =
    accept-flake-config = false
    EOF
    cp ${phoenixAgentCodexConfig} "$out/etc/codex/config.toml"
    ln -s ${pkgs.coreutils}/bin/env "$out/usr/bin/env"
  '';
  init = pkgs.writeShellScriptBin "phoenix-sandbox-init" ''
    exec ${pkgs.python3}/bin/python3 -I ${./sandbox-init.py} "$@"
  '';
  guiHttp = pkgs.writeShellScriptBin "phoenix-gui-http" ''
    exec ${pkgs.python3}/bin/python${pkgs.python3.pythonVersion} -I ${./gui-http-worker.py}
  '';
in
pkgs.dockerTools.buildLayeredImage {
  name = "localhost/phoenix-codex";
  tag = "0.1.2";
  contents = [
    tools
    etc
    init
    guiHttp
    pkgs.dockerTools.binSh
    pkgs.dockerTools.caCertificates
  ];
  includeNixDB = true;
  extraCommands = ''
    mkdir -p sandbox tmp dev sys run/phoenix-admin run/phoenix-deploy home/v
    chmod 1777 tmp
  '';
  # This /nix store belongs to the isolated image, never the host store. Nix
  # single-user evaluation/builds stay inside OpenShell's process/network fence.
  fakeRootCommands = ''
    chown 1000:1000 sandbox
    # Sticky, root-owned store: the single-user builder can add paths, but
    # cannot rename/replace the root-owned tool closures used by egress rules.
    chmod 1777 nix/store
    chown -R 1000:1000 nix/var
  '';
  config = {
    User = "1000:1000";
    WorkingDir = "/sandbox";
    Env = [
      "HOME=/sandbox"
      "PATH=/bin:/usr/bin"
      "SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt"
      "LANG=C.UTF-8"
      "TERM=xterm-256color"
    ];
    Cmd = [ "/bin/bash" ];
  };
}
