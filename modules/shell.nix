{ user, ... }:

{
  programs.bash.interactiveShellInit = ''
    export PHOENIX_REPO_ROOT="''${PHOENIX_REPO_ROOT:-${user.repoDirectory}}"
    if [ -r "$PHOENIX_REPO_ROOT/shell/phoenix-aliases.sh" ]; then
      source "$PHOENIX_REPO_ROOT/shell/phoenix-aliases.sh"
    else
      source ${../shell/phoenix-aliases.sh}
    fi
  '';
}
