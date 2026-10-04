# Run: nix build --impure --file tests/kando-packaging.nix --no-link
# Exact upstream schemas and selection code; no Electron/hardware is started.
let
  flake = builtins.getFlake ("git+file://" + toString ../.);
  pkgs = flake.inputs.nixpkgs.legacyPackages.x86_64-linux;
  user = import ../config/user.nix { inherit (pkgs) lib; };
  metal = flake.nixosConfigurations.metal.config;
  vm = flake.nixosConfigurations.vm.config;
  home = metal.home-manager.users.${user.name};
  wrapped = pkgs.lib.findFirst (
    p: p.name == "kando-phoenix-${pkgs.kando.version}"
  ) null home.home.packages;
  fixture = pkgs.writeText "kando-fixture.json" (
    builtins.toJSON (import ./kando.nix { nixpkgsPath = flake.inputs.nixpkgs.outPath; })
  );
  # Integrity is copied from the pinned Kando lockfile, not an unpinned npm install.
  zod = pkgs.fetchurl {
    url = "https://registry.npmjs.org/zod/-/zod-4.3.6.tgz";
    hash = "sha512-rftlrkhHZOcjDwkGlnUtZZkvaPHCsDATp4pGpuOOMDaTdDDXF91wuVDJoWoPsKX/3YPQ5fHuF3STjcYyKr+Qhg==";
  };
  mouse = metal.systemd.services."phoenix-mouse-debounce@".serviceConfig;
in
assert !(vm.systemd.services ? "phoenix-mouse-debounce@");
assert !(vm.home-manager.users.${user.name}.systemd.user.services ? kando);
assert mouse.User == "phoenix-mouse-debounce";
assert mouse.Group == "phoenix-mouse-debounce";
assert
  mouse.SupplementaryGroups == [
    "input"
    "uinput"
  ];
assert mouse.DevicePolicy == "closed";
assert
  mouse.DeviceAllow == [
    "/dev/input/by-id/usb-Razer_Razer_Viper_V2_Pro_000000000000-event-mouse r"
    "/dev/uinput rw"
  ];
assert
  pkgs.lib.toList home.systemd.user.services.kando.Service.ExecStart == [ "${wrapped}/bin/kando" ];
pkgs.runCommand "phoenix-kando-check"
  {
    nativeBuildInputs = [
      pkgs.nodejs
      pkgs.python3
      pkgs.patch
    ];
  }
  ''
      mkdir zod
      tar xf ${zod} -C zod
      cp -r ${pkgs.kando.src} source
      chmod -R u+w source
      patch -d source -p1 < ${../patches/kando-shortcut-hold.patch}
      node ${./kando.mjs} ${fixture} \
        ${pkgs.kando.src}/src/common/settings-schemata/general-settings-v1.ts \
        ${pkgs.kando.src}/src/common/settings-schemata/menu-settings-v1.ts \
        ${pkgs.kando.src}/src/main/menu-window.ts "$PWD/zod/package/index.js" "$PWD/source" ${pkgs.typescript}/lib/node_modules/typescript/lib/typescript.js
      python3 - ${wrapped}/share/applications/kando.desktop ${wrapped}/bin/kando <<'PY'
    import pathlib, sys
    entry = pathlib.Path(sys.argv[1]).read_text()
    assert f'Exec={sys.argv[2]} %U' in entry
    assert 'Exec=kando ' not in entry
    print('Kando: actual managed desktop/service path and closed non-root mouse unit passed')
    PY
      touch "$out"
  ''
