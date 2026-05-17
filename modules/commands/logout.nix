{ pkgs, ... }:

let
  phoenixLogout = pkgs.writeShellApplication {
    name = "phoenix-logout";

    runtimeInputs = [
      pkgs.hyprland
      pkgs.kdePackages.qttools # qdbus
    ];

    text = ''
      set -euo pipefail

      session="''${XDG_CURRENT_DESKTOP:-}:''${XDG_SESSION_DESKTOP:-}"

      # Hyprland
      if [ -n "''${HYPRLAND_INSTANCE_SIGNATURE:-}" ] \
        || [[ "$session" == *Hyprland* ]] \
        || [[ "$session" == *hyprland* ]]; then
        exec hyprctl dispatch exit
      fi

      # KDE Plasma
      if [[ "$session" == *KDE* ]] \
        || [[ "$session" == *plasma* ]] \
        || [[ "$session" == *plasmax11* ]]; then
        exec qdbus org.kde.Shutdown /Shutdown logout
      fi

      echo "No supported logout command found for this session." >&2
      echo "XDG_CURRENT_DESKTOP=''${XDG_CURRENT_DESKTOP:-}" >&2
      echo "XDG_SESSION_DESKTOP=''${XDG_SESSION_DESKTOP:-}" >&2
      echo "HYPRLAND_INSTANCE_SIGNATURE=''${HYPRLAND_INSTANCE_SIGNATURE:-}" >&2
      exit 1
    '';
  };

  logoutCommand = pkgs.writeShellScriptBin "logout" ''
    exec ${phoenixLogout}/bin/phoenix-logout "$@"
  '';
in
{
  environment.systemPackages = [
    phoenixLogout
    logoutCommand
  ];

  # Helps Bash prefer our command over Bash's builtin `logout`.
  environment.shellAliases = {
    logout = "phoenix-logout";
  };
}
