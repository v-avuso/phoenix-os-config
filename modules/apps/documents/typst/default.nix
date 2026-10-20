{ pkgs, user, ... }:

let
  upstreamArchive = pkgs.fetchurl {
    url = "https://packages.typst.org/preview/letter-pro-3.0.0.tar.gz";
    hash = "sha256-Qo78PVKgsbOjLvO+19rKwDJ/ZrQ0jF3uKlC7CjDd468=";
  };
  letterPro = pkgs.runCommand "typst-letter-pro-3.0.0" { } ''
    mkdir -p "$out"
    tar -xzf ${upstreamArchive} -C "$out"
  '';
  sourceRoot = "${user.repoDirectory}/modules/apps/documents/typst";
  deploy = pkgs.writeShellApplication {
    name = "phoenix-typst-vault";
    runtimeInputs = [ pkgs.python3 ];
    text = ''
      exec python3 ${./deploy-vault.py} --source "${sourceRoot}/template-adapters/omd2typst" "$@"
    '';
  };
in

{
  # Omd2Typst launches Typst as a child process. Keeping Typst in the system
  # profile makes it visible to Obsidian regardless of its desktop launcher.
  environment.systemPackages = [ pkgs.typst ];

  # Metropole Report defaults, Briefs' Heros and Phoenix letter's Liberation Sans.
  fonts.packages = with pkgs; [
    source-serif-pro
    source-sans-pro
    source-code-pro
    gyre-fonts
    liberation_ttf
  ];

  home-manager.users.${user.name} = { config, ... }: {
    home.packages = [ deploy ];
    xdg.dataFile = {
      "phoenix/typst/templates".source = ./templates;
      "typst/packages/preview/letter-pro/3.0.0".source = letterPro;
      # Live design edits are deliberate; upstream remains immutable and hashed.
      "typst/packages/local/phoenix-letter/0.1.0".source =
        config.lib.file.mkOutOfStoreSymlink "${sourceRoot}/templates/phoenix-letter";
    };
  };
}
