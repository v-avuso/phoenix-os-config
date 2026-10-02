{ ... }:

{
  services.xserver.enable = true;

  services.displayManager.sddm.enable = true;

  # Caelestia consumes UPower and PowerProfiles directly; these are shared
  # desktop services rather than implicit dependencies of the VM's Plasma.
  services.upower.enable = true;
  services.power-profiles-daemon.enable = true;

  services.xserver.xkb = {
    layout = "us";
    variant = "";
  };

  services.printing.enable = true;

  services.pulseaudio.enable = false;
  security.rtkit.enable = true;

  services.pipewire = {
    enable = true;
    alsa.enable = true;
    alsa.support32Bit = true;
    pulse.enable = true;
  };
}
