#!/usr/bin/env python3
"""Keep the NCT6687D safety lease while CoolerControl owns its fan channels."""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

LEASE_SECONDS = 30
REFRESH_SECONDS = 10
STARTUP_TIMEOUT_SECONDS = 180
STARTUP_HEALTH_GRACE_SECONDS = 20
FALLBACK_TIMEOUT_SECONDS = 10
RETRY_SECONDS = 1
FALLBACK_POLL_SECONDS = 0.05
PWM_MAX = 255
FIRMWARE_MODE = "2"
MANUAL_MODE = "1"
EXPECTED_LABELS = {
    "fan1": "CPU Fan",
    "fan2": "Pump Fan",
    "fan3": "System Fan #1",
    "fan4": "System Fan #2",
    "fan5": "System Fan #3",
    "fan6": "System Fan #4",
    "fan7": "System Fan #5",
    "fan8": "System Fan #6",
}
MANAGED_CHANNELS = tuple(f"fan{i}" for i in range(1, 7))
UNMANAGED_CHANNELS = ("fan7", "fan8")
# Broad independent safety floors; these are not fan-curve targets. The bottom
# fan is intentionally allowed to stop, and the pump retains a conservative
# minimum to avoid treating a stopped pump as an acceptable live override.
PWM_MINIMUM = {
    "fan1": 51,
    "fan2": 128,
    "fan3": 51,
    "fan4": 51,
    "fan5": 51,
    "fan6": 0,
    "fan7": 0,
    "fan8": 0,
}
COOLERCONTROL_HEALTH_URL = "http://127.0.0.1:11987/health"


class NotReady(RuntimeError):
    pass


class CoolerControlUnavailable(NotReady):
    pass


class ManualModePending(NotReady):
    pass


def read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8").strip()
    except OSError as exc:
        raise NotReady(f"cannot read {path}: {exc}") from exc


def run(command: list[str], timeout: float = 5.0) -> str:
    try:
        result = subprocess.run(
            command, check=False, capture_output=True, text=True, timeout=timeout
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise NotReady(f"could not run {command[0]}: {exc}") from exc
    if result.returncode:
        detail = result.stderr.strip() or f"exit status {result.returncode}"
        raise NotReady(f"{command[0]} failed: {detail}")
    return result.stdout.strip()


def nct_hwmon(sysfs_root: Path) -> Path:
    matches = [
        name_file.parent
        for name_file in sysfs_root.glob("hwmon*/name")
        if read(name_file) == "nct6687"
    ]
    if len(matches) != 1:
        raise NotReady(f"expected one NCT6687 hwmon device, found {len(matches)}")
    hwmon = matches[0]
    for channel, expected in EXPECTED_LABELS.items():
        actual = read(hwmon / f"{channel}_label")
        if actual != expected:
            raise NotReady(
                f"{channel}_label mismatch: expected {expected!r}, got {actual!r}"
            )
    try:
        device = (hwmon / "device").resolve(strict=True)
    except OSError as exc:
        raise NotReady(f"cannot resolve NCT6687 device identity: {exc}") from exc
    if "nct6687" not in str(device).lower():
        raise NotReady(f"unexpected NCT6687 device path: {device}")
    return hwmon


def coolercontrol_invocation() -> str:
    run(["systemctl", "is-active", "--quiet", "coolercontrold.service"], timeout=2)
    invocation = run(
        ["systemctl", "show", "--property=InvocationID", "--value", "coolercontrold.service"]
    )
    if not invocation:
        raise NotReady("coolercontrold has no active invocation ID")
    return invocation


def validate_daemon_health() -> None:
    # CoolerControl 4.3.1 protects /health with its API auth middleware. A
    # response (including 401/404) proves the local daemon event loop answered;
    # transport errors and server failures indicate an unhealthy daemon.
    request = urllib.request.Request(COOLERCONTROL_HEALTH_URL, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=2) as response:
            status = response.status
    except urllib.error.HTTPError as exc:
        status = exc.code
    except (OSError, TimeoutError) as exc:
        raise CoolerControlUnavailable(
            f"CoolerControl health endpoint did not respond: {exc}"
        ) from exc
    if status >= 500:
        raise NotReady(f"CoolerControl health endpoint returned HTTP {status}")


def read_pwm(hwmon: Path, channel: str) -> int:
    path = hwmon / f"pwm{channel.removeprefix('fan')}"
    try:
        value = int(read(path))
    except ValueError as exc:
        raise NotReady(f"{path} is not numeric") from exc
    if not 0 <= value <= PWM_MAX:
        raise NotReady(f"{channel} PWM {value} is outside hardware range 0–{PWM_MAX}")
    if value < PWM_MINIMUM[channel]:
        minimum = PWM_MINIMUM[channel] * 100 / PWM_MAX
        raise NotReady(f"{channel} PWM {value} is below its broad safe floor ({minimum:.0f}%)")
    return value


def validate_ownership(hwmon: Path) -> str:
    invocation = coolercontrol_invocation()
    validate_daemon_health()
    for channel in MANAGED_CHANNELS:
        mode = read(hwmon / f"pwm{channel.removeprefix('fan')}_enable")
        if mode != MANUAL_MODE:
            raise ManualModePending(
                f"{channel} is not userspace/manual-owned (pwm_enable={mode!r})"
            )
    for channel in UNMANAGED_CHANNELS:
        mode = read(hwmon / f"pwm{channel.removeprefix('fan')}_enable")
        if mode != FIRMWARE_MODE:
            raise NotReady(f"{channel} must remain firmware-owned (pwm_enable={mode!r})")
    for channel in EXPECTED_LABELS:
        read_pwm(hwmon, channel)
    return invocation


def expire_lease(hwmon: Path) -> None:
    watchdog = hwmon / "fan_control_watchdog"
    if not watchdog.is_file():
        raise NotReady(f"{watchdog} is absent; kernel firmware fallback is unavailable")
    try:
        watchdog.write_text("1\n", encoding="ascii")
    except OSError as exc:
        raise NotReady(f"cannot request one-second firmware fallback: {exc}") from exc
    if read(watchdog) != "1":
        raise NotReady("could not observe the one-second fallback lease")

    deadline = time.monotonic() + FALLBACK_TIMEOUT_SECONDS
    while read(watchdog) != "0":
        if time.monotonic() >= deadline:
            raise NotReady("kernel firmware fallback did not complete within 10s")
        time.sleep(FALLBACK_POLL_SECONDS)
    for channel in MANAGED_CHANNELS:
        mode = read(hwmon / f"pwm{channel.removeprefix('fan')}_enable")
        if mode != FIRMWARE_MODE:
            raise NotReady(f"fallback completed but {channel} mode is {mode!r}, expected '2'")


def arm_lease(hwmon: Path) -> None:
    watchdog = hwmon / "fan_control_watchdog"
    try:
        watchdog.write_text(f"{LEASE_SECONDS}\n", encoding="ascii")
    except OSError as exc:
        raise NotReady(f"cannot arm NCT6687 safety lease: {exc}") from exc
    if read(watchdog) != str(LEASE_SECONDS):
        raise NotReady("NCT6687 did not retain the requested safety lease")


def recover_from_fallback(hwmon: Path, previous_invocation: str | None) -> str:
    print("CoolerControl ownership/safety check failed; returning channels to firmware", flush=True)
    expire_lease(hwmon)

    # coolercontrold's supported apply_on_boot path reinitializes NCT devices
    # and reapplies saved settings. Its preStart reconciles Phoenix baseline.
    run(["systemctl", "restart", "coolercontrold.service"], timeout=120)
    deadline = time.monotonic() + STARTUP_TIMEOUT_SECONDS
    last_problem = "waiting for a fresh CoolerControl invocation"
    while time.monotonic() < deadline:
        try:
            current = validate_ownership(hwmon)
            if previous_invocation and current == previous_invocation:
                raise NotReady("CoolerControl invocation did not change after recovery restart")
            arm_lease(hwmon)
            print("CoolerControl reclaimed NCT fan channels; safety lease rearmed", flush=True)
            return current
        except (NotReady, OSError) as exc:
            last_problem = str(exc)
            time.sleep(RETRY_SECONDS)
    raise NotReady(f"CoolerControl recovery timed out after 180s: {last_problem}")


def wait_for_initial_health(hwmon: Path) -> str:
    deadline = time.monotonic() + STARTUP_HEALTH_GRACE_SECONDS
    last_problem = "CoolerControl API has not started"
    while True:
        try:
            return validate_ownership(hwmon)
        except (CoolerControlUnavailable, ManualModePending) as exc:
            last_problem = str(exc)
        if time.monotonic() >= deadline:
            raise NotReady(
                f"CoolerControl did not become responsive within "
                f"{STARTUP_HEALTH_GRACE_SECONDS}s: {last_problem}"
            )
        time.sleep(RETRY_SECONDS)


def stop_keeper() -> None:
    unit = "phoenix-nct6687-watchdog.service"
    state_command = ["systemctl", "show", "--property=ActiveState", "--value", unit]
    state = run(state_command)
    if state not in ("inactive", "failed"):
        run(["systemctl", "stop", unit])
        state = run(state_command)
    if state not in ("inactive", "failed"):
        raise NotReady(f"watchdog keeper is still {state!r} after stop request")


def prepare_sleep(sysfs_root: Path) -> None:
    stop_keeper()
    hwmon = nct_hwmon(sysfs_root)
    expire_lease(hwmon)
    if read(hwmon / "fan_control_watchdog") != "0":
        raise NotReady("watchdog lease was rearmed while verifying firmware fallback")
    print("NCT6687 firmware fallback confirmed for fan1-fan6 before sleep", flush=True)


def run_keeper(sysfs_root: Path) -> None:
    hwmon = nct_hwmon(sysfs_root)
    try:
        # systemd marks coolercontrold active before its API listener and
        # device initialization are ready. Wait for that observed startup
        # condition; other ownership/safety failures still recover immediately.
        invocation = wait_for_initial_health(hwmon)
        arm_lease(hwmon)
        print(f"NCT6687 watchdog armed with a {LEASE_SECONDS}s lease on {hwmon}", flush=True)
    except (NotReady, OSError) as exc:
        print(f"NCT6687 ownership not ready at startup: {exc}", file=sys.stderr, flush=True)
        invocation = recover_from_fallback(hwmon, None)

    while True:
        time.sleep(REFRESH_SECONDS)
        try:
            current_hwmon = nct_hwmon(sysfs_root)
            if current_hwmon != hwmon:
                raise NotReady("NCT6687 device changed while lease was armed")
            current_invocation = validate_ownership(hwmon)
            if current_invocation != invocation:
                raise NotReady("CoolerControl restarted; verify firmware fallback before rearming")
            arm_lease(hwmon)
        except (NotReady, OSError) as exc:
            print(f"NCT6687 lease renewal stopped: {exc}", file=sys.stderr, flush=True)
            invocation = recover_from_fallback(hwmon, invocation)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sysfs-root", type=Path, required=True)
    parser.add_argument("--prepare-sleep", action="store_true")
    args = parser.parse_args()
    try:
        if args.prepare_sleep:
            prepare_sleep(args.sysfs_root)
        else:
            run_keeper(args.sysfs_root)
    except (NotReady, OSError) as exc:
        print(f"NCT6687 watchdog recovery failed: {exc}", file=sys.stderr, flush=True)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
