{ pkgs }:
let
  # Reuse upstream's overlay without adding/updating any repository flake inputs.
  source = builtins.fetchTarball {
    url = "https://github.com/exceptionptr/tsm-app-linux/archive/1908e34930f742a3a9ce754faf4e1839431fff3a.tar.gz";
    sha256 = "1rf42jp7m71g0ialwk7qkjlg8nxlnwrghnsbfrxyx8lz1hhidsmi";
  };
  upstream = (import "${source}/flake.nix").outputs {
    self = source;
    nixpkgs = null;
  };
in
((pkgs.extend upstream.overlays.default).tsm-app).overrideAttrs (old: {
  patches = (old.patches or [ ]) ++ [ ./tsm-startup.patch ];
  postInstall = old.postInstall + ''
    substituteInPlace $out/share/applications/tsm-app.desktop \
      --replace-fail 'Exec=/usr/bin/tsm-app' 'Exec=wow-tsm'
  '';
})
