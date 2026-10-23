# Run with: nix build --impure --file commands/tests/commands-packaging.nix --no-link
let
  flake = builtins.getFlake ("git+file://" + toString ../..);
  config = flake.nixosConfigurations.metal.config;
  newConfig = flake.nixosConfigurations.metal-4tb.config;
  pkgs = flake.inputs.nixpkgs.legacyPackages.x86_64-linux;
  user = import ../../config/user.nix { inherit (pkgs) lib; };
  sandboxCommands = import ../. {
    inherit pkgs user;
    includeDesktopCommands = false;
    targetProbe = pkgs.writeShellScript "fixture-root-probe" ''
      printf '%s\n' e9d1b391-3f86-4254-9970-aa47df230474
    '';
  };
  # Only root identity is synthetic; compile the real packaged command flow.
  commandsFor = c: import ../. {
    inherit pkgs user;
    # This fixture exercises storage selection/deployment, not desktop packages.
    includeDesktopCommands = false;
    defaultTarget = c.phoenix.target;
    nixosRebuild = c.system.build.nixos-rebuild;
    targetProbe = pkgs.writeShellScript "fixture-root-probe" ''
      printf '%s\n' ${pkgs.lib.escapeShellArg (if c.phoenix.target == "metal-4tb" then
        "b1756a78-0da5-47a3-a73c-38112d1ac945" else "e9d1b391-3f86-4254-9970-aa47df230474")}
    '';
  };
  commands = commandsFor config;
  newCommands = commandsFor newConfig;
  nativeBroker = builtins.head (builtins.filter (package: (package.name or "") == "ai-broker")
    config.home-manager.users.${user.name}.home.packages);
  sandboxBroker = import ../../modules/development/ai/agent/authorization/adapter.nix {
    inherit pkgs;
    authorizationLibrary = config.system.build.phoenixAuthorizationLibrary;
    authorizationPolicy = config.system.build.phoenixAuthorizationPolicy;
    adminClient = config.system.build.phoenixAdminClient;
    deploymentCommands = pkgs.lib.genAttrs [ "phoenix-test" "phoenix-switch" "phoenix-boot" ]
      (name: "${config.system.build.phoenixDeploymentSandboxClient}/bin/phoenix-deploy-review");
  };
in
assert (builtins.fromJSON config.system.build.phoenixAuthorizationPolicy.text).target == "metal";
assert (builtins.fromJSON newConfig.system.build.phoenixAuthorizationPolicy.text).target == "metal-4tb";
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
  unset PHOENIX_TARGET
  ${newCommands}/bin/phoenix-target --info > selected
  grep -Fxq 'target=metal-4tb source=root-filesystem:b1756a78-0da5-47a3-a73c-38112d1ac945' selected
  ${newCommands}/bin/phoenix-rebuild --print switch > new-activation
  grep -Fq '#metal-4tb' new-activation
  grep -Fq 'nixos-rebuild --sudo switch' new-activation
  export PHOENIX_TARGET=metal
  ${commands}/bin/phoenix-rebuild --print build > result
  grep -Fq 'nixos-rebuild build --flake ' result
  grep -Fq '#metal' result
  if grep -Fq -- '--sudo' result; then
    echo 'build unexpectedly requests privilege' >&2
    exit 1
  fi
  ${commands}/bin/phoenix-rebuild --print test > activation
  grep -Fq 'nixos-rebuild --sudo test --flake ' activation
  if grep -Fq 'phoenix-deploy-review' activation; then
    echo 'human activation unexpectedly uses broker helper' >&2; exit 1
  fi
  for package in ${nativeBroker} ${sandboxBroker}; do
    test -x "$package/bin/ai-broker"
    if "$package/bin/ai-broker" -- phoenix-test > broker-output 2>&1; then exit 1; fi
    if "$package/bin/ai-broker" --reason fixture -- sh -c true > broker-output 2>&1; then exit 1; fi
    if "$package/bin/ai-broker" --reason fixture -- phoenix-test --reason override > broker-output 2>&1; then exit 1; fi
  done
  ${sandboxCommands}/bin/phoenix-test --print > sandbox-preview
  grep -Fq 'nixos-rebuild --sudo test --flake ' sandbox-preview
  # Packaging only: no deployment-socket preflight, authentication or activation.
  # Existing agent-deployment fixtures exercise the sandbox host-auth branch
  # with explicit disposable preflight stubs; a Nix builder has no live broker.
  ${pkgs.python3}/bin/python3 -I - <<'PY_CHECK'
  from pathlib import Path
  import importlib.util, json, re
  spec = importlib.util.spec_from_file_location('adapter', '${../../modules/development/ai/agent/authorization/ai-broker.py}')
  adapter = importlib.util.module_from_spec(spec); spec.loader.exec_module(adapter)
  for package, helper in [
      ('${nativeBroker}', '${config.system.build.phoenixDeploymentClient}/bin/phoenix-deploy-review'),
      ('${sandboxBroker}', '${config.system.build.phoenixDeploymentSandboxClient}/bin/phoenix-deploy-review')]:
      wrapper = Path(package + '/bin/ai-broker').read_text()
      broker_config = json.loads(Path(re.search(r'/nix/store/[A-Za-z0-9-]+-phoenix-ai-broker[.]json', wrapper)[0]).read_text())
      for action in ('test', 'switch', 'boot'):
          command = adapter.prepare(broker_config, ['--task','fixture','--reason','Requested deployment','--',
                                                    'phoenix-' + action,'--worktree',str(Path.cwd())])
          assert command == [helper,'--target','metal','--action',action,'--task','fixture',
                             '--reason','Requested deployment','--worktree',str(Path.cwd())]
  PY_CHECK
  touch "$out"
''
