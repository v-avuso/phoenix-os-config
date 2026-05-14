# Source this file from a shell profile to enable PhoeNix OS helpers.

if [ -n "${BASH_SOURCE[0]-}" ]; then
  _phoenix_alias_file="${BASH_SOURCE[0]}"
elif [ -n "${ZSH_VERSION-}" ]; then
  _phoenix_alias_file="$(eval 'printf "%s" "${(%):-%x}"')"
else
  _phoenix_alias_file="$0"
fi

_phoenix_shell_dir="$(CDPATH= cd -- "$(dirname -- "$_phoenix_alias_file")" && pwd)"
# Nix may source this file from /nix/store. In that case modules/shell.nix sets
# PHOENIX_REPO_ROOT first so helpers keep using the mutable checkout.
if [ -z "${PHOENIX_REPO_ROOT:-}" ]; then
  PHOENIX_REPO_ROOT="$(CDPATH= cd -- "$_phoenix_shell_dir/.." && pwd)"
fi
export PHOENIX_REPO_ROOT

_phoenix_require_repo() {
  # Fail at command use, not shell startup, so a broken checkout path does not
  # make every new terminal noisy or unusable.
  if [ -f "$PHOENIX_REPO_ROOT/flake.nix" ] \
    && [ -r "$PHOENIX_REPO_ROOT/bin/phoenix-target" ] \
    && [ -r "$PHOENIX_REPO_ROOT/bin/phoenix-rebuild" ]; then
    return 0
  fi

  cat >&2 <<EOF
phoenix: cannot find PhoeNix OS repo helpers at:
  PHOENIX_REPO_ROOT=$PHOENIX_REPO_ROOT

Expected:
  \$PHOENIX_REPO_ROOT/flake.nix
  \$PHOENIX_REPO_ROOT/bin/phoenix-target
  \$PHOENIX_REPO_ROOT/bin/phoenix-rebuild

Set PHOENIX_REPO_ROOT to your checkout, or clone the repo to:
  ~/repos/code/phoenix-os-config
EOF
  return 127
}

phoenix-target() {
  _phoenix_require_repo || return
  bash "$PHOENIX_REPO_ROOT/bin/phoenix-target" "$@"
}

phoenix-target-info() {
  _phoenix_require_repo || return
  bash "$PHOENIX_REPO_ROOT/bin/phoenix-target" --info
}

phoenix-rebuild() {
  _phoenix_require_repo || return
  bash "$PHOENIX_REPO_ROOT/bin/phoenix-rebuild" "$@"
}

phoenix-switch() {
  phoenix-rebuild switch "$@"
}

phoenix-test() {
  phoenix-rebuild test "$@"
}

phoenix-boot() {
  phoenix-rebuild boot "$@"
}

phoenix-build() {
  phoenix-rebuild build "$@"
}

phoenix-dry-build() {
  phoenix-rebuild dry-build "$@"
}

unset _phoenix_alias_file
unset _phoenix_shell_dir
