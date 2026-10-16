{ pkgs, user, ... }:

{
  # Omd2Typst launches Typst as a child process. Keeping Typst in the system
  # profile makes it visible to Obsidian regardless of its desktop launcher.
  environment.systemPackages = [ pkgs.typst ];

  # Metropole Report's declared defaults; TeX Gyre Heros is used by Briefs.
  fonts.packages = with pkgs; [
    source-serif-pro
    source-sans-pro
    source-code-pro
    gyre-fonts
  ];

  # The plugin only registers templates inside a vault. This Phoenix-owned
  # copy is the canonical source to copy into each vault that uses the plugin.
  home-manager.users.${user.name}.xdg.dataFile."phoenix/typst/templates".source = ./templates;
}
