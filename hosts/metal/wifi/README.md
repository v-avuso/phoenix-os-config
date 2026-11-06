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

Kernel changes require a build and coordinated reboot. Keep the previous boot
generation for immediate recovery. Keep power saving disabled and avoid other
Wi-Fi changes during diagnostic comparisons. The diagnostic capture below is
the next step after recurrence; another quiet interval alone cannot establish
that the backport fixes the defect.

## Diagnostic capture

The held kernel enables `ATH12K_DEBUG`, `ATH12K_DEBUGFS`, `ATH12K_TRACING`, and
`ATH12K_COREDUMP`. Enabling these facilities is not a fix. The receive-buffer
patch is retained to keep this observability trial otherwise comparable; a
recurrence on November 5 showed that it does not prevent all stalls.

`phoenix-wifi-diagnostics.service` starts at boot and captures until the first
unexpected disconnect after establishing a connection, plus 60 seconds, or
24 hours. Locally generated reason-3 leaves (including normal suspend) do not
consume the incident window; peer-originated leaves and kernel connection-loss
events still trigger it. It never reloads the driver, reconnects,
requests firmware statistics, simulates a crash, or changes power saving. A
module reload is tolerated. It restores the previous driver debug mask and
NetworkManager logging settings when stopped, including via `ExecStopPost`.
Failures restoring NetworkManager logging are reported, with driver cleanup
still attempted. A service restart begins another bounded capture.

- The debug mask `0x42` selects WMI/QMI messages. PCI interrupt logging is
  excluded because it floods the rolling capture. MAC debugging is excluded:
  Linux 7.3 contains MAC-debug key dump sites. Raw ath12k packet/buffer trace
  events and management-frame/control-port events are not selected.
- The isolated `phoenix-wifi` tracefs instance records driver call/return,
  station-state, scan, flush, connection-loss and association-timeout metadata.
  Its per-CPU allocation totals at most 32 MiB. The global tracer is untouched.
- Passive `device_dp_stats`, station counters, connection state, routes and
  router/external connectivity probes are sampled approximately every ten seconds. Errors are retained.
- Selected kernel and NetworkManager/supplicant journal messages rotate through
  four 8 MiB files. Two incident trace exports keep the most recent 16 MiB each; truncation is recorded. Total
  retained capture files are at most approximately 64 MiB (below a 96 MiB budget).
  Processing stops after 256 MiB of journal input. Existing system-journal
  retention still applies separately; debug messages may increase its turnover.
- CPU is capped at 20% of one CPU for the collector; its process memory limit is
  192 MiB, separate from trace-buffer memory. Kernel debug work is not governed
  by the collector's CPU quota. Tracing/debug logging can affect timing.
- Queue overflow or an oversized journal record stops capture rather than silently dropping incoming records.
  Missing required trace events or driver counters fail visibly.
- Firmware crash-dump support is available, but raw dumps are not automatically
  copied: they may be large and contain sensitive device memory. The collector
  records whether a dump is available in `/sys/class/devcoredump`.

Files are in `/var/lib/phoenix-wifi-diagnostics`, readable by root and the dedicated
`phoenix-wifi-diagnostics` group (the configured operator joins it at login).
They include network identifiers and local addresses; review before sharing.
Capture files survive reboot and rotate in place. No upload or AI processing runs.

After deploying and rebooting, verify the kernel configuration, service state,
initial samples, debug mask, selected trace events, and permissions before calling
the capture ready. Capture capability is not proof of the underlying defect.
Stop with `sudo systemctl stop phoenix-wifi-diagnostics`; restart with
`sudo systemctl restart phoenix-wifi-diagnostics` for another incident window.
Remove this diagnostic service and the four kernel flags after investigation.
Retain a working boot generation throughout the diagnostic trial.

Validation:

```sh
python3 -B hosts/metal/wifi/tests/diagnostics.py
nix eval --impure --file hosts/metal/wifi/tests/configuration.nix
nix build --impure --no-link --file hosts/metal/wifi/tests/runtime.nix
```

The unit tests cover bounds, incident triggering and cleanup failure handling.
The disposable VM checks real tracefs event formats, allocation, snapshotting,
isolation and cleanup under the production service sandbox. Firmware, live
hardware statistics and the complete capture remain host acceptance checks.

Sources: [kernel trace instances](https://docs.kernel.org/trace/ftrace.html#instances),
[NetworkManager logging](https://networkmanager.dev/docs/api/latest/NetworkManager.conf.html#logging-section),
and the exact held Linux 7.3 `ath12k/{Kconfig,debug.h,debug.c,mac.c,debugfs.c}`
and `net/{mac80211,wireless}/trace.h` sources inspected for this configuration.
