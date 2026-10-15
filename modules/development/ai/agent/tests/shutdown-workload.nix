# Synthetic control/log/shutdown workload; not the full Phoenix/Codex image.
{ pkgs }:
let
  tools = pkgs.buildEnv {
    name = "shutdown-workload-tools";
    paths = [ pkgs.bash pkgs.curl pkgs.coreutils pkgs.cacert pkgs.dockerTools.binSh ];
    pathsToLink = [ "/bin" "/etc/ssl/certs" ];
  };
  accounts = pkgs.runCommand "shutdown-workload-accounts" { } ''
    mkdir -p "$out/etc"
    printf 'root:x:0:0:root:/root:/bin/sh\nsandbox:x:1000:1000:Sandbox:/sandbox:/bin/bash\n' > "$out/etc/passwd"
    printf 'root:x:0:\nsandbox:x:1000:\n' > "$out/etc/group"
    printf 'hosts: files dns\n' > "$out/etc/nsswitch.conf"
  '';
in
pkgs.dockerTools.buildLayeredImage {
  name = "localhost/phoenix-shutdown-workload";
  tag = "fixture";
  contents = [ tools accounts ];
  extraCommands = ''
    mkdir -p tmp sandbox
    chmod 1777 tmp
    chmod 0700 sandbox
  '';
  # Fakeroot changes archive ownership without a root build or build-time VM.
  fakeRootCommands = ''
    chown 1000:1000 sandbox
  '';
  config = {
    User = "1000:1000";
    WorkingDir = "/sandbox";
    Cmd = [ "/bin/bash" ];
    StopSignal = "SIGTERM";
    Env = [ "HOME=/sandbox" "PATH=/bin" "SSL_CERT_FILE=/etc/ssl/certs/ca-bundle.crt" ];
  };
}
