# Build/run both immutable entry points against one disposable typed client.
let
  flake = builtins.getFlake ("git+file://" + toString ../../../../../..);
  pkgs = flake.inputs.nixpkgs.legacyPackages.x86_64-linux;
  policy = pkgs.writeText "fixture-policy.json" (builtins.toJSON {
    version = 1; securityReviewEnabled = false; clientUid = 1000;
    operatorUid = 1000; updaterUid = 1000; target = "metal";
    diagnostics = builtins.listToAttrs (map (name: { name = "admin.${name}"; value = "automatic"; })
      [ "kernel-journal" "dmesg" "trace-summary" "trace-format" "service-status" "wakeup-get" "wakeup-set" ]);
    wakeupDevices = [ ]; statusServices = [ ];
  });
  client = pkgs.writeShellScriptBin "phoenix-admin" ''echo "$@"'';
  adapter = import ../adapter.nix {
    inherit pkgs; authorizationLibrary = pkgs.writeText "fixture-authorization.py" (builtins.readFile ../request.py);
    authorizationPolicy = policy; adminClient = client;
  };
in pkgs.runCommand "phoenix-authorization-alias-test" { } ''
  ${adapter}/bin/ai-broker --reason fixture -- phoenix-admin dmesg > old
  ${adapter}/bin/phoenix-authorize --reason fixture -- phoenix-admin dmesg > new
  cmp old new
  grep -F -- '--task ai-broker --reason fixture dmesg' new
  touch "$out"
''
