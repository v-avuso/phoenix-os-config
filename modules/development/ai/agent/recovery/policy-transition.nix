# On-demand exact descriptor; preparation grants no authority and never activates.
# Execute only after the security administrator approves the bound report/helper.
{ pkgs, descriptor }:
import ./source-bootstrap.nix {
  inherit pkgs descriptor;
  name = "phoenix-review-policy-transition";
}
