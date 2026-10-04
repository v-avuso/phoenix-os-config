# Run with: nix build --impure --file tests/clamav-recovery.nix --no-link
let
  flake = builtins.getFlake ("git+file://" + toString ../.);
  config = flake.nixosConfigurations.metal.config;
  pkgs = flake.inputs.nixpkgs.legacyPackages.x86_64-linux;
  recovery = config.systemd.services.clamav-db-recovery;
  freshclam = config.systemd.services.clamav-freshclam;
  daemon = config.systemd.services.clamav-daemon;
  scanner = config.systemd.services.clamav-clamonacc;
in
assert config.services.clamav.updater.enable;
assert freshclam.wantedBy == [ "multi-user.target" ];
assert freshclam.unitConfig.OnSuccess == [ "clamav-db-recovery.service" ];
assert daemon.wants == [ ];
assert builtins.elem "clamav-freshclam.service" daemon.after;
assert scanner.wants == [ "clamav-daemon.service" ];
assert builtins.elem "clamav-freshclam.service" scanner.after;
assert builtins.elem "clamav-freshclam.service" recovery.after;
assert recovery.serviceConfig.Type == "oneshot";
assert !(recovery.serviceConfig ? User);
assert recovery.unitConfig.ConditionPathExistsGlob == "/var/lib/clamav/*.c[vl]d";
pkgs.runCommand "clamav-recovery-behavior" { } ''
  mkdir -p fakebin
  cat > fakebin/systemctl <<'SH'
  #!/bin/sh
  set -eu

  action="$1"
  shift
  if [ "$action" = is-active ]; then
    [ "''${1:-}" = --quiet ] && shift
    grep -Fqx "$1" "$ACTIVE_FILE"
    exit $?
  fi

  if [ "$action" = start ]; then
    printf 'start %s\n' "$1" >> "$CALL_LOG"
    printf '%s\n' "$1" >> "$ACTIVE_FILE"
    exit 0
  fi

  exit 2
  SH
  chmod +x fakebin/systemctl

  # Run the configured recovery script with a fake systemctl executable.
  sed 's|${pkgs.systemd}/bin/systemctl|'"$PWD"'/fakebin/systemctl|g' \
    ${recovery.serviceConfig.ExecStart} > recovery.sh
  export ACTIVE_FILE="$PWD/active-units"
  export CALL_LOG="$PWD/calls"
  : > "$ACTIVE_FILE"
  : > "$CALL_LOG"

  bash recovery.sh
  test "$(grep -c '^start ' "$CALL_LOG")" -eq 2
  grep -Fqx 'start clamav-daemon.service' "$CALL_LOG"
  grep -Fqx 'start clamav-clamonacc.service' "$CALL_LOG"

  # A partially active setup starts only the missing scanner.
  printf '%s\n' 'clamav-daemon.service' > "$ACTIVE_FILE"
  : > "$CALL_LOG"
  bash recovery.sh
  test "$(grep -c '^start ' "$CALL_LOG")" -eq 1
  grep -Fqx 'start clamav-clamonacc.service' "$CALL_LOG"

  # A later successful freshclam run sees both units active and submits no
  # starts.
  : > "$CALL_LOG"
  bash recovery.sh
  test ! -s "$CALL_LOG"

  touch "$out"
''
