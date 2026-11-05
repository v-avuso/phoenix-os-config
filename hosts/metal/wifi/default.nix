{ config, ... }:

{
  # Experimental backport; do not silently carry it onto a different driver.
  assertions = [
    {
      assertion = config.boot.kernelPackages.kernel.version == "7.3";
      message = "Reassess the WCN7850 RX-buffer backport before changing kernel 7.3.";
    }
  ];

  boot.kernelPatches = [
    {
      name = "ath12k-wifi7-replenish-rx-buffers";
      patch = ./replenish-rx-buffers.patch;
    }
  ];
}
