{ pkgs }:
let
  # Reuse upstream's overlay without adding/updating any repository flake inputs.
  source = builtins.fetchTarball {
    url = "https://github.com/exceptionptr/tsm-app-linux/archive/d4f787414908d0ff53000538a6fa618755bfeb00.tar.gz";
    sha256 = "15wqszaqhqqxwlgvph0rz7s300kklpb2a7fwp2svjxd463s9shgb";
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
