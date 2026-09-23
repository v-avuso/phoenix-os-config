{ lib, pkgs, ... }:

{
  # User-side OpenSnitch UI.
  # Keep opensnitchd + rules in NixOS system config.

  services.opensnitch-ui = {
    enable = true;
    package = pkgs.opensnitch-ui;
  };

  systemd.user.services.opensnitch-ui.Service = {
    Restart = "on-failure";
    RestartSec = "2s";
  };

  # OpenSnitch UI popup defaults:
  #   default_action=1    -> allow
  #   default_duration=0  -> once
  #   default_target=0    -> process
  #   default_timeout=99  -> max prompt timeout
  #
  # Disable prompts during the passive learning period. This intentionally
  # overwrites the UI settings file on Home Manager activation.
  home.activation.opensnitchUiPrefs =
    lib.hm.dag.entryAfter [ "writeBoundary" ] ''
      mkdir -p "$HOME/.config/opensnitch"

      cat > "$HOME/.config/opensnitch/settings.conf" <<'EOF'
[global]
default_action=1
default_duration=0
default_target=0
default_timeout=99
disable_popups=1
EOF
    '';
}
