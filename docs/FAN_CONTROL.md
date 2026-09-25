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

The module deliberately sets no driver parameters, register layouts, ACPI
resource overrides, or PWM profiles. In particular, it does not set
`acpi_enforce_resources=lax`, force a register layout, or enable
`msi_fan_brute_force`.

## Intended Fan Policy

These are the intended target curves, recorded before the Linux sensors and
fan channels are known. Configure them in CoolerControl only after discovery
and physical channel identification on the bare-metal machine.

| Curve | Temperature | Fan output |
| --- | --- | ---: |
| GPU | `<= 60.0 °C` | 0% |
| GPU | `60.1–70.0 °C` | 40% |
| GPU | `70.1–80.0 °C` | 60% |
| GPU | `> 80.0 °C` | 80% |
| CPU | `<= 69.9 °C` | 0% |
| CPU | approximately `70.2–85.0 °C` | 50% |
| CPU | `> 85 °C` | approximately 81% |

Use approximately `2 °C` hysteresis for both curves. The case-fan policy is
`max(CPU curve, GPU curve, 25%)`. The GPU's own three fans use the GPU curve.
The pump is fixed at 50%, the chipset fan at 80%, and the EZ-Connect fan at
80%. Remaining case fans use the mixed CPU/GPU policy; the Windows aliases
expected to represent those case fans are `top`, `bottom`, `side`, `rear`,
`unclear_1`, `system_fan_5`, and `system_fan_6`. Confirm each physical fan
before attaching its policy.

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

The aliases are not yet bound to Linux channels. Confirm the physical fan
connected to each channel before assigning its permanent Phoenix alias or
policy.

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

Identify physical fan destinations on the bare-metal machine one PWM channel
at a time, with temperatures and cooling monitored and a clear way to restore
firmware control. Do not infer the destination from a matching-looking Linux
number or sensor label. Once each channel is positively identified, bind the
permanent Phoenix aliases (`top`, `bottom`, `side`, `rear`, `pump`, and others)
to the discovered Linux device/channel and then create the CoolerControl
profiles described above. No mapping or profile is activated by this initial
foundation.
