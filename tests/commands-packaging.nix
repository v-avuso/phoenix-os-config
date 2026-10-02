# Run with: nix build --impure --file tests/commands-packaging.nix --no-link
let
  flake = builtins.getFlake (toString ../.);
  config = flake.nixosConfigurations.metal.config;
  pkgs = flake.inputs.nixpkgs.legacyPackages.x86_64-linux;
  user = import ../config/user.nix { inherit (pkgs) lib; };
  commands = builtins.head (
    builtins.filter (package: (package.name or "") == "phoenix-user-commands")
      config.home-manager.users.${user.name}.home.packages
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
  touch "$out"
''
