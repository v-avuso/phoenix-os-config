{ lib, nixosConfig, ... }:

{
  # Keep standard Compose sequences available to applications loading ~/.XCompose.
  home.file.".XCompose".text = ''
    include "%L"
  '';
  programs.plasma.configFile."kxkbrc"."Layout" = lib.mkIf nixosConfig.services.desktopManager.plasma6.enable {
    LayoutList = nixosConfig.services.xserver.xkb.layout;
    VariantList = nixosConfig.services.xserver.xkb.variant;
    Options = nixosConfig.services.xserver.xkb.options;
    ResetOldOptions = true;
  };
}
