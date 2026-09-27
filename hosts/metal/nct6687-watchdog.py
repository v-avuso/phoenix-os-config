#!/usr/bin/env python3
"""Keep the NCT6687D MSI manual-control lease alive while CoolerControl owns it."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import subprocess
import sys
import time
import tomllib
from pathlib import Path

LEASE_SECONDS = 30
REFRESH_SECONDS = 10
STARTUP_TIMEOUT_SECONDS = 180
FALLBACK_TIMEOUT_SECONDS = 10
RETRY_SECONDS = 1
FALLBACK_POLL_SECONDS = 0.05
PWM_MAX = 255
PWM_TOLERANCE_PERCENT = 2.0
FIRMWARE_PWM_ENABLE = "2"
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
EXPECTED_ASSIGNMENTS = {
    "fan1": "phoenix-case-maximum-v1",
    "fan2": "phoenix-pump-fixed-v1",
    "fan3": "phoenix-case-maximum-v1",
    "fan4": "phoenix-case-maximum-v1",
    "fan5": "phoenix-case-maximum-v1",
    "fan6": "phoenix-bottom-stopped-v1",
}
REQUIRED_APPLIED_LOGS = {
    "fan1": "Phoenix CPU/GPU maximum",
    "fan2": "Phoenix pump fixed 80%",
    "fan3": "Phoenix CPU/GPU maximum",
    "fan4": "Phoenix CPU/GPU maximum",
    "fan5": "Phoenix CPU/GPU maximum",
    "fan6": "Phoenix bottom fan stopped temporarily",
}


class NotReady(RuntimeError):
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


def nct_hwmon(sysfs_root: Path) -> tuple[Path, str]:
    matches = []
    for name_file in sysfs_root.glob("hwmon*/name"):
        if read(name_file) == "nct6687":
            matches.append(name_file.parent)
    if len(matches) != 1:
        raise NotReady(f"expected one NCT6687 hwmon device, found {len(matches)}")

    hwmon = matches[0]
    for channel, expected in EXPECTED_LABELS.items():
        actual = read(hwmon / f"{channel}_label")
        if actual != expected:
            raise NotReady(
                f"{hwmon / f'{channel}_label'} label mismatch: expected {expected!r}, got {actual!r}"
            )

    try:
        device_path = (hwmon / "device").resolve(strict=True)
    except OSError as exc:
        raise NotReady(f"cannot resolve NCT device path: {exc}") from exc
    uid = hashlib.sha256(("Hwmon" + str(device_path)).encode()).hexdigest()
    return hwmon, uid


def validate_profiles(config_path: Path, policy_path: Path, nct_uid: str) -> tuple[dict, dict]:
    try:
        config = tomllib.loads(config_path.read_text(encoding="utf-8"))
        policy = json.loads(policy_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, tomllib.TOMLDecodeError) as exc:
        raise NotReady(f"cannot read CoolerControl policy/config: {exc}") from exc

    devices = config.get("devices", {})
    if not isinstance(devices, dict):
        raise NotReady("CoolerControl devices table is missing or invalid")
    if devices.get(nct_uid) != policy["nctDeviceName"]:
        raise NotReady("CoolerControl NCT device UID does not match the live hwmon device")
    named_devices = {name: uid for uid, name in devices.items()}
    for key in ("cpuDeviceName", "gpuDeviceName"):
        if list(name for name in devices.values() if name == policy[key]) != [policy[key]]:
            raise NotReady(f"expected exactly one CoolerControl device named {policy[key]!r}")

    settings = config.get("settings", {})
    if settings.get("apply_on_boot") is not True:
        raise NotReady("CoolerControl apply_on_boot is not enabled")

    device_settings = config.get("device-settings", {})
    configured = device_settings.get(nct_uid, {})
    if not isinstance(configured, dict):
        raise NotReady("CoolerControl NCT device settings are invalid")
    if {
        channel: configured.get(channel, {}).get("profile_uid")
        for channel in EXPECTED_ASSIGNMENTS
    } != EXPECTED_ASSIGNMENTS:
        raise NotReady("CoolerControl Phoenix fan assignments do not match the expected policy")
    if any(channel in configured for channel in ("fan7", "fan8")):
        raise NotReady("CoolerControl fan7/fan8 must remain unmanaged")

    functions = config.get("functions", [])
    if not isinstance(functions, list):
        raise NotReady("CoolerControl functions are invalid")
    function_spec = policy["function"]
    function_by_uid = {function.get("uid"): function for function in functions}
    actual_function = function_by_uid.get(function_spec["uid"])
    expected_function = {
        "name": function_spec["name"],
        "f_type": "Standard",
        "duty_minimum": 1,
        "duty_maximum": 100,
        "step_size_min_decreasing": 0,
        "step_size_max_decreasing": 0,
        "response_delay": function_spec["response_delay"],
        "deviance": function_spec["deviance"],
        "only_downward": False,
        "threshold_hopping": function_spec["threshold_hopping"],
    }
    if actual_function is None or any(
        actual_function.get(key) != value for key, value in expected_function.items()
    ):
        raise NotReady("CoolerControl Phoenix response function differs from the declared policy")

    profiles = config.get("profiles", [])
    if not isinstance(profiles, list):
        raise NotReady("CoolerControl profiles are invalid")
    profile_by_uid = {profile.get("uid"): profile for profile in profiles}
    policy_profiles = {profile["uid"]: profile for profile in policy["profiles"]}
    for uid, expected in policy_profiles.items():
        actual = profile_by_uid.get(uid)
        if actual is None or actual.get("p_type") != expected["p_type"]:
            raise NotReady(f"CoolerControl profile {uid!r} is missing or has the wrong type")
        if expected["p_type"] == "Graph" and actual.get("function_uid") != function_spec["uid"]:
            raise NotReady(f"CoolerControl graph profile {uid!r} has the wrong response function")
        if expected["p_type"] == "Fixed" and actual.get("speed_fixed") != expected["speed_fixed"]:
            raise NotReady(f"CoolerControl fixed profile {uid!r} has the wrong duty")
        if expected["p_type"] == "Graph" and actual.get("speed_profile") != expected["speed_profile"]:
            raise NotReady(f"CoolerControl graph profile {uid!r} differs from the declared staircase")

    mix = profile_by_uid.get("phoenix-case-maximum-v1", {})
    if mix.get("mix_function_type") != "Max" or set(mix.get("member_profile_uids", [])) != {
        "phoenix-case-cpu-v1",
        "phoenix-case-gpu-v1",
    }:
        raise NotReady("CoolerControl CPU/GPU Max profile is incomplete")
    cpu_uid = named_devices.get(policy["cpuDeviceName"])
    gpu_uid = named_devices.get(policy["gpuDeviceName"])
    for profile_uid, device_uid, temp_name in (
        ("phoenix-case-cpu-v1", cpu_uid, policy["cpuTempName"]),
        ("phoenix-case-gpu-v1", gpu_uid, policy["gpuTempName"]),
    ):
        source = profile_by_uid[profile_uid].get("temp_source", {})
        if source.get("device_uid") != device_uid or source.get("temp_name") != temp_name:
            raise NotReady(f"CoolerControl profile {profile_uid!r} has the wrong temperature source")

    return config, policy


def coolercontrol_invocation() -> str:
    run(["systemctl", "is-active", "--quiet", "coolercontrold.service"], timeout=2)
    invocation = run(
        ["systemctl", "show", "--property=InvocationID", "--value", "coolercontrold.service"]
    )
    if not invocation:
        raise NotReady("coolercontrold has no active invocation ID")
    return invocation


def validate_applied_logs(invocation: str) -> None:
    journal = run(
        [
            "journalctl",
            "--boot",
            "--unit=coolercontrold.service",
            "--output=cat",
            "--no-pager",
            f"_SYSTEMD_INVOCATION_ID={invocation}",
        ]
    )
    for channel, profile_name in REQUIRED_APPLIED_LOGS.items():
        expected = f"Successfully applied:: nct6687 | {channel} | Profile: {profile_name}"
        if expected not in journal:
            raise NotReady(f"CoolerControl has not confirmed applying {channel}'s Phoenix profile")


def read_pwm(hwmon: Path, channel: str) -> int:
    path = hwmon / f"pwm{channel.removeprefix('fan')}"
    try:
        return int(read(path))
    except ValueError as exc:
        raise NotReady(f"{path} is not numeric") from exc


def read_cpu_temperature(sysfs_root: Path) -> float:
    matches = [
        name_file.parent
        for name_file in sysfs_root.glob("hwmon*/name")
        if read(name_file) == "k10temp"
    ]
    if len(matches) != 1:
        raise NotReady(f"expected one k10temp device, found {len(matches)}")
    hwmon = matches[0]
    if read(hwmon / "temp1_label") != "Tctl":
        raise NotReady("k10temp temp1 is not labelled Tctl")
    try:
        return int(read(hwmon / "temp1_input")) / 1000.0
    except ValueError as exc:
        raise NotReady("k10temp Tctl is not numeric") from exc


def read_gpu_temperature(nvidia_smi: Path, expected_name: str) -> float:
    output = run(
        [
            str(nvidia_smi),
            "--query-gpu=name,temperature.gpu",
            "--format=csv,noheader,nounits",
        ]
    )
    matches = [
        row
        for row in csv.reader(output.splitlines())
        if len(row) == 2 and row[0].strip() == expected_name
    ]
    if len(matches) != 1:
        raise NotReady(f"expected one NVIDIA temperature for {expected_name!r}")
    try:
        return float(matches[0][1].strip())
    except ValueError as exc:
        raise NotReady(f"NVIDIA temperature for {expected_name!r} is not numeric") from exc


def curve_duty(points: list, temperature: float) -> float:
    """Evaluate a CoolerControl graph profile between its configured points."""
    if not points:
        raise NotReady("CoolerControl graph profile has no speed points")
    if temperature <= float(points[0][0]):
        return float(points[0][1])
    for left, right in zip(points, points[1:]):
        left_temp, left_duty = float(left[0]), float(left[1])
        right_temp, right_duty = float(right[0]), float(right[1])
        if temperature <= right_temp:
            if right_temp <= left_temp:
                raise NotReady("CoolerControl graph temperatures are not strictly increasing")
            fraction = (temperature - left_temp) / (right_temp - left_temp)
            return left_duty + fraction * (right_duty - left_duty)
    return float(points[-1][1])


def curve_duty_range(points: list, temperature: float, deviance: float) -> tuple[float, float]:
    # The configured deviance can retain the preceding output close to a step.
    low_temp, high_temp = temperature - deviance, temperature + deviance
    duties = [curve_duty(points, low_temp), curve_duty(points, high_temp)]
    duties.extend(
        float(duty)
        for point_temp, duty in points
        if low_temp <= float(point_temp) <= high_temp
    )
    return min(duties), max(duties)


def validate_manual_channels(hwmon: Path) -> None:
    for channel in EXPECTED_ASSIGNMENTS:
        enable_path = hwmon / f"pwm{channel.removeprefix('fan')}_enable"
        mode = read(enable_path)
        if mode != "1":
            raise NotReady(f"{channel} is not in CoolerControl manual mode (pwm_enable={mode!r})")


def validate_pwm_targets(
    hwmon: Path,
    config: dict,
    policy: dict,
    sysfs_root: Path,
    nvidia_smi: Path,
) -> None:
    profiles = {profile["uid"]: profile for profile in config["profiles"]}
    function = next(
        (
            item
            for item in config["functions"]
            if item.get("uid") == "phoenix-case-standard-v1"
        ),
        None,
    )
    if function is None:
        raise NotReady("CoolerControl Phoenix response function is missing")

    cpu_range = curve_duty_range(
        profiles["phoenix-case-cpu-v1"]["speed_profile"],
        read_cpu_temperature(sysfs_root),
        float(function["deviance"]),
    )
    gpu_range = curve_duty_range(
        profiles["phoenix-case-gpu-v1"]["speed_profile"],
        read_gpu_temperature(nvidia_smi, policy["gpuDeviceName"]),
        float(function["deviance"]),
    )
    max_range = (max(cpu_range[0], gpu_range[0]), max(cpu_range[1], gpu_range[1]))

    # The NCT6687 sysfs PWM scale is 0–255. Verify each Max-controlled channel
    # against the active graph outputs, allowing the configured deviance band.
    for channel in ("fan1", "fan3", "fan4", "fan5"):
        duty = read_pwm(hwmon, channel) * 100.0 / PWM_MAX
        if not max_range[0] - PWM_TOLERANCE_PERCENT <= duty <= max_range[1] + PWM_TOLERANCE_PERCENT:
            raise NotReady(
                f"{channel} PWM duty {duty:.1f}% is outside the requested CPU/GPU Max range "
                f"{max_range[0]:.1f}–{max_range[1]:.1f}%"
            )

    pump_duty = read_pwm(hwmon, "fan2") * 100.0 / PWM_MAX
    if abs(pump_duty - 80.0) > PWM_TOLERANCE_PERCENT:
        raise NotReady(f"fan2 pump PWM duty is {pump_duty:.1f}%, expected approximately 80%")

    bottom_pwm = read_pwm(hwmon, "fan6")
    if bottom_pwm != 0:
        raise NotReady(f"fan6 bottom PWM is {bottom_pwm}, expected 0")


def validate_ready(
    config_path: Path,
    policy_path: Path,
    sysfs_root: Path,
    nvidia_smi: Path,
) -> tuple[Path, str]:
    invocation = coolercontrol_invocation()
    hwmon, nct_uid = nct_hwmon(sysfs_root)
    config, policy = validate_profiles(config_path, policy_path, nct_uid)
    validate_applied_logs(invocation)
    validate_manual_channels(hwmon)
    validate_pwm_targets(hwmon, config, policy, sysfs_root, nvidia_smi)
    return hwmon, invocation


def wait_until_ready(
    config_path: Path,
    policy_path: Path,
    sysfs_root: Path,
    nvidia_smi: Path,
    timeout_seconds: int,
    phase: str,
) -> tuple[Path, str]:
    deadline = time.monotonic() + timeout_seconds
    last_problem = "policy not ready"
    while True:
        try:
            return validate_ready(config_path, policy_path, sysfs_root, nvidia_smi)
        except (NotReady, OSError) as exc:
            last_problem = str(exc)
        if time.monotonic() >= deadline:
            raise NotReady(f"{phase} timed out after {timeout_seconds}s: {last_problem}")
        time.sleep(RETRY_SECONDS)


def stop_keeper() -> None:
    unit = "phoenix-nct6687-watchdog.service"
    state_command = [
        "systemctl",
        "show",
        "--property=ActiveState",
        "--value",
        unit,
    ]
    state = run(state_command)
    if state not in ("inactive", "failed"):
        run(["systemctl", "stop", unit])
        state = run(state_command)
    if state not in ("inactive", "failed"):
        raise NotReady(f"watchdog keeper is still {state!r} after stop request")


def prepare_sleep(sysfs_root: Path) -> None:
    """Stop lease refresh, force the driver's saved firmware fallback, and verify it."""
    stop_keeper()
    hwmon, _nct_uid = nct_hwmon(sysfs_root)
    watchdog = hwmon / "fan_control_watchdog"
    if not watchdog.is_file():
        raise NotReady(f"{watchdog} is absent; MSI brute-force watchdog is unavailable")

    try:
        watchdog.write_text("1\n", encoding="ascii")
    except OSError as exc:
        raise NotReady(f"cannot request one-second firmware fallback: {exc}") from exc

    # The driver reports the configured timeout, not time remaining. Observe
    # 1->0 so zero means the expiry callback completed its saved-state restore.
    if read(watchdog) != "1":
        raise NotReady("could not observe the one-second watchdog lease after arming it")

    deadline = time.monotonic() + FALLBACK_TIMEOUT_SECONDS
    while True:
        timeout = read(watchdog)
        if timeout == "0":
            break
        if timeout != "1":
            raise NotReady(f"unexpected watchdog value during fallback: {timeout!r}")
        if time.monotonic() >= deadline:
            raise NotReady(
                f"kernel firmware fallback did not complete within {FALLBACK_TIMEOUT_SECONDS}s"
            )
        time.sleep(FALLBACK_POLL_SECONDS)

    for channel in EXPECTED_ASSIGNMENTS:
        mode_path = hwmon / f"pwm{channel.removeprefix('fan')}_enable"
        mode = read(mode_path)
        if mode != FIRMWARE_PWM_ENABLE:
            raise NotReady(
                f"kernel fallback completed but {channel} is not in the expected firmware mode "
                f"({mode_path.name}={mode!r}, expected {FIRMWARE_PWM_ENABLE})"
            )

    if read(watchdog) != "0":
        raise NotReady("watchdog lease was re-armed while verifying firmware fallback")

    print(
        "NCT6687 firmware fallback confirmed for fan1-fan6; "
        "no watchdog lease will remain across sleep",
        flush=True,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--policy", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--sysfs-root", type=Path, required=True)
    parser.add_argument("--nvidia-smi", type=Path, required=True)
    parser.add_argument("--prepare-sleep", action="store_true")
    args = parser.parse_args()

    if args.prepare_sleep:
        try:
            prepare_sleep(args.sysfs_root)
        except (NotReady, OSError) as exc:
            print(f"NCT6687 pre-sleep fallback failed: {exc}", file=sys.stderr, flush=True)
            return 1
        return 0

    try:
        hwmon, invocation = wait_until_ready(
            args.config,
            args.policy,
            args.sysfs_root,
            args.nvidia_smi,
            STARTUP_TIMEOUT_SECONDS,
            "startup recovery",
        )
        watchdog = hwmon / "fan_control_watchdog"
        if not watchdog.is_file():
            raise NotReady(f"{watchdog} is absent; MSI brute-force mode is not active")
        watchdog.write_text(f"{LEASE_SECONDS}\n", encoding="ascii")
        print(f"NCT6687 watchdog armed with a {LEASE_SECONDS}s lease on {hwmon}", flush=True)
    except (NotReady, OSError) as exc:
        print(f"NCT6687 watchdog not armed: {exc}", file=sys.stderr)
        return 1

    while True:
        time.sleep(REFRESH_SECONDS)
        try:
            current_hwmon, current_invocation = validate_ready(
                args.config, args.policy, args.sysfs_root, args.nvidia_smi
            )
            if current_hwmon != hwmon:
                raise NotReady("NCT device changed during recovery")
            current_watchdog = current_hwmon / "fan_control_watchdog"
            if not current_watchdog.is_file():
                raise NotReady(f"{current_watchdog} is absent; MSI brute-force mode is not active")
            if current_invocation != invocation:
                print("CoolerControl invocation changed; recovery verified against its new invocation", flush=True)
                invocation = current_invocation
            current_watchdog.write_text(f"{LEASE_SECONDS}\n", encoding="ascii")
            watchdog = current_watchdog
        except (NotReady, OSError) as exc:
            # No refresh on failed recovery: kernel expiry restores firmware control.
            print(f"NCT6687 watchdog refresh stopped: {exc}", file=sys.stderr, flush=True)
            return 1


if __name__ == "__main__":
    raise SystemExit(main())
