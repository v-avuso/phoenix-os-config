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
  options.services.phoenixDeployment.securityReview.enable =
    lib.mkEnableOption "experimental diff-based deployment security review";
}
