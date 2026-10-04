{
  config,
  lib,
  pkgs,
  ...
}:
{
  # Generic file-manager integration; no Xfce session or Caelestia ownership here.
  config = lib.mkIf config.programs.hyprland.enable {
    nixpkgs.overlays = [
      (_final: prev: {
        thunar-unwrapped = prev.thunar-unwrapped.overrideAttrs (old: {
          patches = (old.patches or [ ]) ++ [ ../../patches/thunar-live-user-css.patch ];
        });
      })
    ];
    programs.thunar = {
      enable = true;
      plugins = with pkgs; [
        thunar-archive-plugin
        thunar-volman
        thunar-media-tags-plugin
      ];
    };
    # GVfs supplies UDisks, trash, MTP, SMB and FUSE without a GNOME session.
    services.gvfs = {
      enable = true;
      package = pkgs.gvfs;
    };
    services.tumbler.enable = true;
    # archive-plugin ships an Engrampa .tap adapter, but none for Xarchiver.
    # Its ZIP encoder/decoder helpers must also be on the desktop PATH.
    environment.systemPackages = with pkgs; [
      engrampa
      zip
      unzip
    ];
  };
}
