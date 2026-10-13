{ lib, ... }:
{
  # Authentication, source freezing and rollback remain in deployment.nix.
  # This single switch controls the optional AI security review; keep it off
  # until the real workflow has passed isolated acceptance.
  imports = [
    (lib.mkRenamedOptionModule
      [ "services" "phoenixDeployment" "modelReview" "enable" ]
      [ "services" "phoenixDeployment" "securityReview" "enable" ]
    )
  ];
  options.services.phoenixDeployment.securityReview = {
    enable = lib.mkEnableOption "experimental diff-based deployment security review";
    adapter = lib.mkOption {
      type = lib.types.enum [ "codex" ];
      default = "codex";
      description = "Implemented isolated review adapter; other backends are unsupported.";
    };
    model = lib.mkOption {
      type = lib.types.strMatching "[A-Za-z0-9][A-Za-z0-9._-]{0,99}";
      default = "gpt-6-luna";
      description = "Model requested by the pinned reviewer CLI; availability needs an isolated retained-auth trial.";
    };
    effort = lib.mkOption {
      type = lib.types.enum [ "low" "medium" "high" "xhigh" ];
      default = "high";
      description = "Requested reasoning effort; actual model/CLI compatibility remains separately verified.";
    };
  };
}
