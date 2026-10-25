# Run: nix build --impure --file home/kando/tests/packaging.nix --no-link
# Exact upstream schemas and selection code; no Electron/hardware is started.
let
  flake = builtins.getFlake ("git+file://" + toString ../../..);
  pkgs = flake.inputs.nixpkgs.legacyPackages.x86_64-linux;
  user = import ../../../config/user.nix { inherit (pkgs) lib; };
  metal = flake.nixosConfigurations.metal.config;
  home = metal.home-manager.users.${user.name};
  wrapped = pkgs.lib.findFirst (
    p: p.name == "kando-phoenix-${pkgs.kando.version}"
  ) null home.home.packages;
  fixture = pkgs.writeText "kando-fixture.json" (
    builtins.toJSON (import ./fixture.nix { nixpkgsPath = flake.inputs.nixpkgs.outPath; })
  );
  # Integrity is copied from the pinned Kando lockfile, not an unpinned npm install.
  zod = pkgs.fetchurl {
    url = "https://registry.npmjs.org/zod/-/zod-4.3.6.tgz";
    hash = "sha512-rftlrkhHZOcjDwkGlnUtZZkvaPHCsDATp4pGpuOOMDaTdDDXF91wuVDJoWoPsKX/3YPQ5fHuF3STjcYyKr+Qhg==";
  };
  hyprlandCheck = import ../hyprland/tests/packaging.nix;
in
assert
  pkgs.lib.toList home.systemd.user.services.kando.Service.ExecStart
  == [ "${wrapped}/bin/kando --close-menu" ];
pkgs.runCommand "phoenix-kando-check"
  {
    nativeBuildInputs = [
      pkgs.nodejs
      pkgs.python3
      pkgs.patch
    ];
  }
  ''
      test -e ${hyprlandCheck}
      mkdir zod
      tar xf ${zod} -C zod
      cp -r ${pkgs.kando.src} source
      chmod -R u+w source
      patch -d source -p1 < ${../shortcut-hold.patch}
      node ${./selection.mjs} ${fixture} \
        ${pkgs.kando.src}/src/common/settings-schemata/general-settings-v1.ts \
        ${pkgs.kando.src}/src/common/settings-schemata/menu-settings-v1.ts \
        ${pkgs.kando.src}/src/main/menu-window.ts "$PWD/zod/package/index.js" "$PWD/source" ${pkgs.typescript}/lib/node_modules/typescript/lib/typescript.js
      python3 - ${wrapped}/share/applications/kando.desktop ${wrapped}/bin/kando <<'PY'
    import pathlib, sys
    entry = pathlib.Path(sys.argv[1]).read_text()
    assert f'Exec={sys.argv[2]} %U' in entry
    assert 'Exec=kando ' not in entry
    print('Kando: actual managed desktop/service path passed')
    PY
      touch "$out"
  ''
