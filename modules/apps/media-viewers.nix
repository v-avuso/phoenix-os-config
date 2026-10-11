{ lib, pkgs, user, ... }:
let
  # Use the packaged desktop IDs and MIME declarations.
  videoTypes = [
    "video/mpeg"
    "video/x-mpeg2"
    "video/x-mpeg3"
    "video/mp4v-es"
    "video/x-m4v"
    "video/mp4"
    "video/divx"
    "video/vnd.divx"
    "video/msvideo"
    "video/x-msvideo"
    "video/ogg"
    "video/quicktime"
    "video/vnd.rn-realvideo"
    "video/x-ms-afs"
    "video/x-ms-asf"
    "video/x-ms-wmv"
    "video/x-ms-wmx"
    "video/x-ms-wvxvideo"
    "video/x-avi"
    "video/avi"
    "video/x-flic"
    "video/fli"
    "video/x-flc"
    "video/flv"
    "video/x-flv"
    "video/x-theora"
    "video/x-theora+ogg"
    "video/x-matroska"
    "video/mkv"
    "video/webm"
    "video/x-ogm"
    "video/x-ogm+ogg"
    "video/mp2t"
    "video/vnd.mpegurl"
    "video/3gp"
    "video/3gpp"
    "video/3gpp2"
    "video/dv"
    "video/vnd.avi"
    "application/mxf"
    "application/vnd.rn-realmedia"
    "application/vnd.rn-realmedia-vbr"
    "application/vnd.ms-asf"
    "application/x-matroska"
    "application/x-ogm-video"
  ];
  audioTypes = [
    "audio/opus"
    "audio/mpeg"
    "audio/mp3"
    "audio/x-mp3"
    "audio/flac"
    "audio/aac"
    "audio/x-aac"
    "audio/vnd.dolby.heaac.1"
    "audio/vnd.dolby.heaac.2"
    "audio/ogg"
    "audio/vorbis"
    "audio/x-vorbis"
    "audio/x-vorbis+ogg"
    "audio/wav"
    "audio/x-wav"
    "audio/vnd.wave"
    "audio/x-pn-wav"
    "audio/mp4"
    "audio/m4a"
    "audio/x-m4a"
    "audio/aiff"
    "audio/x-aiff"
    "audio/x-ms-wma"
    "audio/x-matroska"
    "audio/webm"
    "application/ogg"
    "application/x-ogg"
    "application/x-extension-m4a"
    "application/x-ogm-audio"
  ];
  imageTypes = [
    "image/avif"
    "image/bmp"
    "image/gif"
    "image/heif"
    "image/jpeg"
    "image/jpg"
    "image/jxl"
    "image/pbm"
    "image/pjpeg"
    "image/png"
    "image/svg+xml"
    "image/tiff"
    "image/webp"
    "image/x-bmp"
    "image/x-exr"
    "image/x-png"
    "image/x-portable-anymap"
    "image/x-portable-bitmap"
    "image/x-portable-graymap"
    "image/x-portable-pixmap"
    "image/x-targa"
    "image/x-tga"
  ];
in
{
  home-manager.users.${user.name} = {
    programs.mpv = {
      enable = true;
      # Keep native Wayland auto-selection and upstream playback bindings.
      # mpv.desktop supplies pseudo-gui, which forces a window for audio too.
      config = {
        osc = true;
        "audio-display" = "embedded-first";
        "loop-playlist" = "inf";
      };
      scriptOpts.osc.visibility = "auto";
    };
    programs.swayimg = {
      enable = true;
      settings = {
        info.show = "no";
        # Opening one image in Thunar also enables adjacent-image navigation.
        list.all = "yes";
        "keys.viewer" = {
          Left = "prev_file";
          Right = "next_file";
          Up = "fullscreen";
          Down = "step_down 10";
          ScrollUp = "zoom +10 mouse";
          ScrollDown = "zoom -10 mouse";
          "Ctrl+ScrollUp" = "step_up 5";
          "Ctrl+ScrollDown" = "step_down 5";
          "Alt+ScrollUp" = "step_left 5";
          "Alt+ScrollDown" = "step_right 5";
          "Shift+ScrollUp" = "prev_file";
          "Shift+ScrollDown" = "next_file";
          F11 = "fullscreen";
          f = "fullscreen";
          MouseLeft = "drag";
          BackSpace = "zoom optimal; position center";
        };
      };
    };
    # Remains available through Open With for conversion/editing.
    home.packages = [ pkgs.kdePackages.gwenview ];
    xdg.mimeApps.defaultApplications =
      lib.genAttrs (videoTypes ++ audioTypes) (_: [ "mpv.desktop" ])
      // lib.genAttrs imageTypes (_: [ "swayimg.desktop" ]);
    # Psysonic 1.55.0 (bd6c320) accepts Subsonic IDs, not arbitrary local paths.
    # Psysonic remains the library client; mpv owns local-file playback.
  };
}
