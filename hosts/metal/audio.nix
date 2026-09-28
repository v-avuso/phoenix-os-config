{ pkgs, ... }:

let
  alc897CombinedProfileSet = pkgs.runCommand "alc897-combined-profile-set.conf" { } ''
    cat ${pkgs.pipewire}/share/alsa-card-profile/mixer/profile-sets/default.conf > "$out"
    cat >> "$out" <<'PROFILE'

[Profile output:analog-stereo+output:iec958-stereo]
description = Analog Stereo Output + Digital Stereo (IEC958) Output
output-mappings = analog-stereo iec958-stereo
priority = 1000
PROFILE
  '';
in
{
  services.pipewire.wireplumber.extraConfig."51-ryzen-outputs" = {
    "monitor.alsa.rules" = [
      {
        matches = [
          { "device.bus-path" = "pci-0000:10:00.6"; }
        ];
        actions."update-props" = {
          "api.alsa.use-acp" = true;
          "device.profile-set" = "${alc897CombinedProfileSet}";
          "device.profile" = "output:analog-stereo+output:iec958-stereo";
        };
      }
      {
        matches = [
          { "node.name" = "alsa_output.pci-0000_10_00.6.analog-stereo"; }
        ];
        actions."update-props" = {
          "node.description" = "Headphones";
        };
      }
      {
        matches = [
          { "node.name" = "alsa_output.pci-0000_10_00.6.iec958-stereo"; }
        ];
        actions."update-props" = {
          "node.description" = "Speakers";
        };
      }
      {
        matches = [
          { "device.name" = "alsa_card.pci-0000_01_00.1"; }
        ];
        actions."update-props" = {
          "device.disabled" = true;
        };
      }
    ];
  };
}
