{ ... }:

{
  services.pipewire.wireplumber.extraConfig."51-ryzen-outputs" = {
    "device.profile.priority.rules" = [
      {
        matches = [
          { "device.name" = "alsa_card.pci-0000_10_00.6"; }
        ];
        actions."update-props" = {
          priorities = [ "pro-audio" ];
        };
      }
    ];

    "monitor.alsa.rules" = [
      {
        matches = [
          { "device.name" = "alsa_card.pci-0000_10_00.6"; }
        ];
        actions."update-props" = {
          "device.profile" = "pro-audio";
        };
      }
      {
        matches = [
          { "node.name" = "alsa_output.pci-0000_10_00.6.pro-output-0"; }
        ];
        actions."update-props" = {
          "node.description" = "Headphones";
        };
      }
      {
        matches = [
          { "node.name" = "alsa_output.pci-0000_10_00.6.pro-output-1"; }
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
