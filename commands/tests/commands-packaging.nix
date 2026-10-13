# Run with: nix build --impure --file commands/tests/commands-packaging.nix --no-link
let
  flake = builtins.getFlake ("git+file://" + toString ../..);
  config = flake.nixosConfigurations.metal.config;
  pkgs = flake.inputs.nixpkgs.legacyPackages.x86_64-linux;
  user = import ../../config/user.nix { inherit (pkgs) lib; };
  sandboxCommands = import .. {
    inherit pkgs user;
    deploymentHelper = config.system.build.phoenixDeploymentSandboxClient;
    includeDesktopCommands = false;
  };
  commands = builtins.head (
    builtins.filter (
      package: (package.name or "") == "phoenix-user-commands"
    ) config.home-manager.users.${user.name}.home.packages
  );
in
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
  ${commands}/bin/phoenix-rebuild --print test --reason 'packaged routing fixture' > activation
  grep -Fq 'phoenix-deploy-review' activation
  grep -Fq -- '--worktree' activation
  grep -Fq -- '--reason' activation
  if grep -Eq 'nixos-rebuild|--sudo' activation; then
    echo 'activation bypasses frozen deployment helper' >&2; exit 1
  fi
  ${sandboxCommands}/bin/phoenix-test --print --reason 'sandbox routing fixture' > sandbox-preview
  grep -Fq 'phoenix-deploy-review' sandbox-preview
  if ${sandboxCommands}/bin/phoenix-test --reason 'sandbox routing fixture' > sandbox-output 2>&1; then
    echo 'sandbox disabled-AI deployment unexpectedly succeeded' >&2; exit 1
  fi
  grep -Fq 'host Polkit authentication' sandbox-output
  touch "$out"
''
