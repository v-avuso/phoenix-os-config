{ pkgs }:
let
  # Reuse upstream's overlay without adding/updating any repository flake inputs.
  source = builtins.fetchTarball {
    url = "https://github.com/exceptionptr/tsm-app-linux/archive/60ad454b7187c3d2f1e4df36352b2af0fade02a6.tar.gz";
    sha256 = "08fi4sqsq8fpzrqq4p5b03kaay61116y477r6gg93a01m3cr4qh3";
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
