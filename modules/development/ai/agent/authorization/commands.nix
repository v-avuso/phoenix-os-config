# Exact opt-in definitions; published only through ordinary reviewed Nix deployment.
{ config, lib, pkgs, ... }:
let
  cfg = config.phoenix.authorization.commands;
  entry = lib.types.submodule {
    options = {
      executable = lib.mkOption {
        type = lib.types.strMatching "/nix/store/[a-z0-9]{32}-[^/]+/.+";
        description = "Immutable installed ELF executable, e.g. a package interpolation plus /bin/program. Scripts/interpreters and generic trampolines are unsupported.";
      };
      arguments = lib.mkOption { type = lib.types.listOf lib.types.str; default = [ ]; description = "Exact fixed argv; caller cannot append arguments."; };
      rationale = lib.mkOption { type = lib.types.str; description = "Reviewed nonempty purpose and bounded authority justification, required also for automatic entries."; };
      mode = lib.mkOption { type = lib.types.enum [ "automatic" "review" "human" ]; default = "human"; };
      timeout = lib.mkOption { type = lib.types.ints.between 1 60; default = 10; description = "Execution deadline in seconds; combined stdout/stderr is limited to 64 KiB."; };
    };
  };
in {
  options.phoenix.authorization.commands = {
    enable = lib.mkEnableOption "experimental exact registered command execution through the existing root controller";
    entries = lib.mkOption { type = lib.types.attrsOf entry; default = { }; description = "Installed identifier-to-exact-command policy; no caller-supplied programs or automatic rule publication."; };
  };
  config.assertions = [ {
    assertion = !cfg.enable || !(builtins.any (e: e.mode == "review") (builtins.attrValues cfg.entries))
      || config.services.phoenixDeployment.securityReview.enable;
    message = "Review-mode commands currently require the explicitly enabled protected deployment security-review provider; availability does not enable it.";
  } {
    assertion = builtins.all (name: builtins.match "[a-z][a-z0-9-]{0,63}" name != null
      && builtins.match ".*[^[:space:]].*" cfg.entries.${name}.rationale != null
      && builtins.length cfg.entries.${name}.arguments <= 16
      && builtins.all (a: builtins.stringLength a <= 4096) cfg.entries.${name}.arguments)
      (builtins.attrNames cfg.entries);
    message = "Command identifiers, nonempty rationales and fixed argv must satisfy the bounded registry contract.";
  } ];
}
