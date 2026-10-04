{ lib, pkgs, ... }:
let
  converter = pkgs.writeShellScript "phoenix-thunar-convert-images" ''
    exec ${pkgs.python3}/bin/python3 -I ${./thunar-image-convert.py} \
      --magick ${pkgs.imagemagick}/bin/magick "$@"
  '';
  # %F is quoted by Thunar's supported filename expansion; the converter reads
  # stdin so ImageMagick never interprets user filenames as coder/frame syntax.
  imageAction = format: title: ''
    <action>
      <icon>image-x-generic</icon>
      <name>Convert to ${title}</name>
      <unique-id>phoenix-convert-${format}</unique-id>
      <command>${converter} ${format} %F</command>
      <description>Create ${title} copies; keep originals and existing files</description>
      <patterns>*</patterns>
      <image-files/>
    </action>
  '';
  archiveTypes = [
    "application/zip"
    "application/x-tar"
    "application/gzip"
    "application/x-bzip2"
    "application/x-xz"
    "application/x-7z-compressed"
    "application/x-rar"
    "application/vnd.rar"
    "application/x-compressed-tar"
    "application/x-bzip-compressed-tar"
    "application/x-xz-compressed-tar"
  ];
in
{
  xfconf.settings.thunar = {
    misc-middle-click-in-tab = true;
    # Ctrl+M remains the upstream menu-bar toggle.
    last-menubar-visible = false;
  };
  xdg.mimeApps.defaultApplications = {
    "inode/directory" = [ "thunar.desktop" ];
  }
  // lib.genAttrs archiveTypes (_: [ "engrampa.desktop" ]);
  # Own only UCA, not history, bookmarks, tabs or other Thunar state.
  xdg.configFile."Thunar/uca.xml".text = ''
    <?xml version="1.0" encoding="UTF-8"?>
    <actions>
      <action>
        <icon>utilities-terminal</icon>
        <name>Open Terminal Here</name>
        <unique-id>phoenix-terminal-here</unique-id>
        <command>${pkgs.foot}/bin/foot -D %f</command>
        <description>Open the current directory in foot</description>
        <patterns>*</patterns>
        <startup-notify/>
        <directories/>
      </action>
      ${imageAction "jpeg" "JPEG"}
      ${imageAction "png" "PNG"}
      ${imageAction "webp" "WebP"}
      ${imageAction "jxl" "JPEG XL"}
    </actions>
  '';
}
