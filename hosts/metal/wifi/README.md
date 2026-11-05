# Metal Wi-Fi

## Intentions

- Reduce recurring WCN7850 connection stalls without changing the held graphics
  stack; retain a known working boot generation and reversible configuration.

## Experimental receive-buffer backport

`default.nix` uses NixOS's native `boot.kernelPatches` to apply the
[October 16 submission](https://lists.openwall.net/linux-kernel/2026/10/16/1632)
verbatim to the held Linux 7.3. Both metal storage targets import this module.
The patch replenishes reaped receive descriptors even when no complete packet
was collected, and frees incomplete queued buffers before returning.

This is an unproven mitigation for this workstation, not a confirmed root cause
or an accepted upstream fix. The submission reports code inspection and a test
on WCN7860 that did not trigger the affected path. A kernel-version assertion
requires reassessment before an upgrade; remove the backport once the selected
source includes an equivalent fix, or if the trial does not help. The generic
updater package-patch overlay is not used because the selected kernel package
set requires kernel-specific wiring. No update policy or graphics hold changes.

Build the selected host before deployment. A kernel patch rebuilds the kernel
and external modules, including NVIDIA; it does not take effect merely through
a live configuration switch. Trial it at a coordinated reboot with the previous
boot generation available. Check graphics startup, Wi-Fi connection, suspend /
resume, and normal use for at least seven days. Two earlier failures in one day
are not a stable baseline; a quiet week supports usefulness without proving
causation. Keep power saving disabled and avoid other Wi-Fi changes during the
comparison. Revert this module import and rebuild to remove the experiment;
use the previous boot generation for immediate recovery.
