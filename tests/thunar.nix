# Standalone isolated fixtures; caller supplies the same pinned sources/packages.
{ pkgs, caelestiaCliSource }:
pkgs.runCommand "phoenix-thunar-integration-fixtures"
  {
    nativeBuildInputs = with pkgs; [
      gcc
      pkg-config
      gtk3
      python3
      xvfb-run
    ];
  }
  ''
    export HOME="$TMPDIR/home"
    export XDG_CONFIG_HOME="$HOME/.config"
    export XDG_CACHE_HOME="$HOME/.cache"
    export XDG_RUNTIME_DIR="$TMPDIR/runtime"
    export GSETTINGS_BACKEND=memory
    export PYTHONDONTWRITEBYTECODE=1
    unset DBUS_SESSION_BUS_ADDRESS WAYLAND_DISPLAY
    mkdir -p "$HOME" "$XDG_CONFIG_HOME" "$XDG_CACHE_HOME" "$XDG_RUNTIME_DIR"
    chmod 700 "$XDG_RUNTIME_DIR"
    cp -r ${caelestiaCliSource} cli
    chmod -R u+w cli
    patch -p1 -d cli < ${../patches/caelestia-gtk-thunar.patch}
    python ${./thunar-theme.py} cli "$TMPDIR/rendered"
    cp -r ${pkgs.thunar-unwrapped.src} thunar-source
    chmod -R u+w thunar-source
    patch -p1 -d thunar-source < ${../patches/thunar-live-user-css.patch}
    gcc -Wall -Wextra -Werror -Wno-deprecated-declarations \
      ${./thunar-css-refresh.c} -I thunar-source/thunar \
      $(pkg-config --cflags --libs gtk+-3.0 gio-2.0) -lm -o check-css
    xvfb-run -a --server-args="-screen 0 1024x768x24 -nolisten tcp" \
      ./check-css "$TMPDIR/rendered"
    mkdir -p fixture/home fixture/tests
    cp ${../home/thunar-image-convert.py} fixture/home/thunar-image-convert.py
    cp ${./thunar-image-convert.py} fixture/tests/thunar-image-convert.py
    cp ${./thunar-image-real.py} fixture/tests/thunar-image-real.py
    python fixture/tests/thunar-image-convert.py
    python fixture/tests/thunar-image-real.py ${pkgs.imagemagick}/bin/magick
    mkdir -p "$out"
    echo "Exact patched GTK/Caelestia lifecycle and ImageMagick fixtures passed" > "$out/result"
  ''
