# Bare-Metal Fan Control

Phoenix uses the NixOS `programs.coolercontrol` module for the CoolerControl
GUI and its `coolercontrold` systemd daemon. The metal host also installs
`lm_sensors` and builds/loads the NCT6687D kernel module from its active
`boot.kernelPackages` set. The package option is
`phoenix.hardware.fanControl.nct6687dPackage`; if a newer kernel package set is
needed, select it through `boot.kernelPackages` so the driver stays matched to
that kernel.

`nct6687dPackage` can also be overridden directly, but any replacement must be
built for the active kernel. When changing to an unstable kernel package set,
the default follows that set's `nct6687d` package automatically.

The module does not set `acpi_enforce_resources=lax` or force a register
layout. It blacklists `nct6683` and loads `nct6687` with
`msi_fan_brute_force=1`; the driver applies this option at module load, so it
takes effect after reboot. On this board, that mode writes each SYS_FAN duty
to all seven firmware curve points, which makes the channels obey manual PWM
requests.

A root `phoenix-nct6687-watchdog.service` waits for CoolerControl's current
startup invocation to confirm all six Phoenix assignments, validates the live
hwmon labels and policy, then arms `fan_control_watchdog` for 30 seconds and
refreshes it every 10 seconds. It never disarms the watchdog on stop or error;
without refreshes, the kernel restores the saved firmware curves and control
modes. Fan policy assignments remain as described below.

## Intended Fan Policy

The metal host declares these CoolerControl 4.3.0 profiles in
`hosts/metal/fan-control.nix`. A pre-start reconciler validates the NCT device
and all eight hwmon fan labels, then merges only the Phoenix-owned profiles and
fan assignments into CoolerControl's writable `/etc/coolercontrol/config.toml`.
The daemon applies saved settings through its normal `apply_on_boot` behavior.
The config file must remain writable; it is not an immutable Nix symlink.

| Profile | Temperature/output points |
| --- | --- |
| CPU case staircase | `(20.0,20)`, `(69.9,20)`, `(70.2,50)`, `(85.0,50)`, `(85.1,81)`, `(120,81)` |
| GPU case staircase | `(20,20)`, `(60.0,20)`, `(60.1,40)`, `(70.0,40)`, `(70.1,60)`, `(80.0,60)`, `(80.1,80)`, `(120,80)` |
| CPU/GPU mix | CoolerControl `Max` of the CPU and GPU case profiles |
| Response | Standard function; 2°C deviance, 1-second response delay, threshold hopping enabled |

The tightly spaced points intentionally preserve staircase plateaus and sharp
steps to avoid known undesirable Arctic P14 RPM/noise bands. The 2°C deviance
and threshold hopping are CoolerControl's closest supported equivalents to the
requested hysteresis/threshold behavior; they do not smooth the curve.

| Linux channel | Phoenix function | Policy |
| --- | --- | --- |
| `fan1` | Top / CPU header / radiator fans | CPU/GPU `Max` |
| `fan2` | Pump | Fixed 80% |
| `fan3` | `unclear_1` | CPU/GPU `Max` |
| `fan4` | Rear | CPU/GPU `Max` |
| `fan5` | Side | CPU/GPU `Max` |
| `fan6` | Bottom | Fixed 0% while its fan rubs the bracket |
| `fan7`, `fan8` | Unused | Unmanaged |

The policy uses the CPU's `temp1` source (`k10temp` Tctl) and CoolerControl's
NVIDIA `GPU Temp` source. Before writing profiles, startup also requires a
numeric `nvidia-smi` GPU temperature for exactly the configured RTX 5090,
checks that CoolerControl has not disabled its `GPU Temp` channel, and checks
that the `Max` mix includes both graph profiles. CoolerControl 4.3.0
uses a 100°C emergency temperature when a profile source is missing, which
keeps the GPU curve at 80% instead of dropping to CPU-only behavior. The policy
does not assign any profile to NVIDIA GPU fan channels or change physical
airflow direction. Startup fails closed if the NCT UID, expected labels, CPU
sensor, GPU sensor, or mix dependencies differ.

## Windows Reference Fingerprint

This table preserves the Windows FanControl configuration's NCT6687DR control
and fan paths behind its custom aliases. It is a reference fingerprint only:
Linux may use different names and channel numbers, and these numbers must not
be copied into Linux hwmon mappings.

| Phoenix alias | Windows control path | Windows fan path | FanControl default sensor name |
| --- | --- | --- | --- |
| `top` (`Top`) | `/lpc/nct6687dr/control/0` | `/lpc/nct6687dr/fan/0` | `CPU Fan` |
| `pump` (`Pump`) | `/lpc/nct6687dr/control/1` | `/lpc/nct6687dr/fan/1` | `Pump Fan #1` |
| `chipset` (`Chipset`) | `/lpc/nct6687dr/control/2` | `/lpc/nct6687dr/fan/2` | `Chipset Fan` |
| `ez_connect` (`EZ-Connect`) | `/lpc/nct6687dr/control/3` | `/lpc/nct6687dr/fan/3` | `EZ-Connect Fan` |
| `unclear_1` (`Unclear 1`) | `/lpc/nct6687dr/control/10` | `/lpc/nct6687dr/fan/10` | `System Fan #1` |
| `rear` (`Rear`) | `/lpc/nct6687dr/control/11` | `/lpc/nct6687dr/fan/11` | `System Fan #2` |
| `side` (`Side`) | `/lpc/nct6687dr/control/12` | `/lpc/nct6687dr/fan/12` | `System Fan #3` |
| `bottom` (`Bottom`) | `/lpc/nct6687dr/control/13` | `/lpc/nct6687dr/fan/13` | `System Fan #4` |
| `system_fan_5` (`System Fan #5`) | `/lpc/nct6687dr/control/14` | `/lpc/nct6687dr/fan/14` | Not recorded |
| `system_fan_6` (`System Fan #6`) | `/lpc/nct6687dr/control/15` | `/lpc/nct6687dr/fan/15` | Not recorded |

This is the historical Windows-side fingerprint; its NCT indices are not
Linux hwmon channel numbers. The Linux channel labels and Phoenix aliases used
by the active policy are listed separately above. Windows NCT indices 2
(`Chipset`) and 3 (`EZ-Connect`) are not exposed in Linux's `msi_alt1` fan
channel set and are therefore not assigned Linux policies.

## First-Boot Discovery

Run these read-only checks on the installed bare-metal Linux system. They
enumerate the sensors and exposed hwmon files without changing fan control.

```sh
sensors
sensors -u
```

If the monitoring chip is not detected, inspect the proposed probes before
running `sudo sensors-detect`; do not accept unrelated driver parameters as a
shortcut. Then enumerate hwmon devices and their current temperature, fan, and
PWM files:

```sh
for hwmon in /sys/class/hwmon/hwmon*; do
  [ -e "$hwmon" ] || continue
  printf '\n%s (%s) device=%s\n' \
    "$hwmon" \
    "$(cat "$hwmon/name")" \
    "$(readlink -f "$hwmon/device" 2>/dev/null || true)"
  for channel in \
    "$hwmon"/temp*_label "$hwmon"/temp*_input \
    "$hwmon"/fan*_label "$hwmon"/fan*_input "$hwmon"/pwm*; do
    [ -f "$channel" ] || continue
    printf '  %-24s %s\n' "$(basename "$channel")" "$(cat "$channel")"
  done
done
```

In CoolerControl, compare its detected devices, temperature sensors, fan
readings, and PWM channels with the `sensors` output and hwmon device names.
Record the Linux device path and channel filenames alongside the Windows
fingerprint above. Temperature `*_input` files report millidegrees Celsius;
fan `*_input` files report RPM. `/sys/class/hwmon/hwmonN` numbering can change,
so retain the device name/path and channel filename as well.

The current Phoenix aliases and assignments are listed in Intended Fan
Policy. If any expected sysfs channel label changes, the startup reconciler
stops before writing policy configuration; verify the physical connection and
update the mapping intentionally before restarting CoolerControl.
