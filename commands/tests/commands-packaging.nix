# Run with: nix build --impure --file commands/tests/commands-packaging.nix --no-link
let
  flake = builtins.getFlake ("git+file://" + toString ../..);
  config = flake.nixosConfigurations.metal.config;
  pkgs = flake.inputs.nixpkgs.legacyPackages.x86_64-linux;
  user = import ../../config/user.nix { inherit (pkgs) lib; };
  sandboxCommands = import ../. {
    inherit pkgs user;
    deploymentHelper = config.system.build.phoenixDeploymentSandboxClient;
    includeDesktopCommands = false;
  };
  commands = builtins.head (
    builtins.filter (
      package: (package.name or "") == "phoenix-user-commands"
    ) config.home-manager.users.${user.name}.home.packages
  );
  nativeBroker = builtins.head (builtins.filter (package: (package.name or "") == "ai-broker")
    config.home-manager.users.${user.name}.home.packages);
  sandboxBroker = import ../../modules/development/ai/agent/authorization/adapter.nix {
    inherit pkgs;
    authorizationLibrary = config.system.build.phoenixAuthorizationLibrary;
    authorizationPolicy = config.system.build.phoenixAuthorizationPolicy;
    adminClient = config.system.build.phoenixAdminClient;
    deploymentCommands = pkgs.lib.genAttrs [ "phoenix-test" "phoenix-switch" "phoenix-boot" ]
      (name: "${sandboxCommands}/bin/${name}");
  };
in
assert (builtins.fromJSON config.system.build.phoenixAuthorizationPolicy.text).target == "metal";
pkgs.runCommand "phoenix-command-packaging" { } ''
  # This checkout deliberately contains an unusable dispatcher. The installed
  # executable must use its packaged implementation while reading flake.nix
  # from this mutable checkout.
  checkout="$TMPDIR/checkout with spaces"
  mkdir -p "$checkout/commands"
  printf '{}\n' > "$checkout/flake.nix"
  printf '#!/bin/sh\nexit 99\n' > "$checkout/commands/phoenix-rebuild"
  chmod +x "$checkout/commands/phoenix-rebuild"

  export PHOENIX_REPO_ROOT="$checkout"
  export PHOENIX_TARGET=metal
  ${commands}/bin/phoenix-rebuild --print build > result
  grep -Fq 'nixos-rebuild build --flake ' result
  grep -Fq '#metal' result
  if grep -Fq -- '--sudo' result; then
    echo 'build unexpectedly requests privilege' >&2
    exit 1
  fi
  ${commands}/bin/phoenix-rebuild --print test > activation
  grep -Fq 'phoenix-deploy-review' activation
  grep -Fq -- '--worktree' activation
  grep -Fq -- '--reason' activation
  if grep -Eq 'nixos-rebuild|--sudo' activation; then
    echo 'activation bypasses frozen deployment helper' >&2; exit 1
  fi
  for package in ${nativeBroker} ${sandboxBroker}; do
    test -x "$package/bin/ai-broker"
    if "$package/bin/ai-broker" -- phoenix-test > broker-output 2>&1; then exit 1; fi
    if "$package/bin/ai-broker" --reason fixture -- sh -c true > broker-output 2>&1; then exit 1; fi
    if "$package/bin/ai-broker" --reason fixture -- phoenix-test --reason override > broker-output 2>&1; then exit 1; fi
  done
  ${sandboxCommands}/bin/phoenix-test --print > sandbox-preview
  grep -Fq 'phoenix-deploy-review' sandbox-preview
  # Packaging only: no deployment-socket preflight, authentication or activation.
  # Existing agent-deployment fixtures exercise the sandbox host-auth branch
  # with explicit disposable preflight stubs; a Nix builder has no live broker.
  ${pkgs.python3}/bin/python3 -I - <<'PY_CHECK'
  import shlex
  from pathlib import Path
  for filename, helper in [
      ('activation', '${config.system.build.phoenixDeploymentClient}/bin/phoenix-deploy-review'),
      ('sandbox-preview', '${config.system.build.phoenixDeploymentSandboxClient}/bin/phoenix-deploy-review')]:
      command = shlex.split(Path(filename).read_text())
      assert command[0] == helper
      assert command[command.index('--target') + 1] == 'metal'
      assert command[command.index('--action') + 1] == 'test'
      assert command[command.index('--reason') + 1] == 'Direct phoenix-test invocation'
  PY_CHECK
  touch "$out"
''
