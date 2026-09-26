#!/usr/bin/env python3
"""Keep the NCT6687D MSI manual-control lease alive while CoolerControl owns it."""

from __future__ import annotations

import argparse
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
        try:
            if name_file.read_text(encoding="utf-8").strip() == "nct6687":
                matches.append(name_file.parent)
        except OSError as exc:
            raise NotReady(f"cannot read {name_file}: {exc}") from exc
    if len(matches) != 1:
        raise NotReady(f"expected one NCT6687 hwmon device, found {len(matches)}")

    hwmon = matches[0]
    for channel, expected in EXPECTED_LABELS.items():
        label_path = hwmon / f"{channel}_label"
        try:
            actual = label_path.read_text(encoding="utf-8").strip()
        except OSError as exc:
            raise NotReady(f"cannot read {label_path}: {exc}") from exc
        if actual != expected:
            raise NotReady(
                f"{label_path} label mismatch: expected {expected!r}, got {actual!r}"
            )

    try:
        device_path = (hwmon / "device").resolve(strict=True)
    except OSError as exc:
        raise NotReady(f"cannot resolve NCT device path: {exc}") from exc
    uid = hashlib.sha256(("Hwmon" + str(device_path)).encode()).hexdigest()
    return hwmon, uid


def validate_profiles(config_path: Path, policy_path: Path, nct_uid: str) -> None:
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
    if {channel: configured.get(channel, {}).get("profile_uid") for channel in EXPECTED_ASSIGNMENTS} != EXPECTED_ASSIGNMENTS:
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


def coolercontrol_invocation() -> str:
    if run(["systemctl", "is-active", "--quiet", "coolercontrold.service"], timeout=2) != "":
        raise NotReady("coolercontrold is not active")
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


def validate_manual_channels(hwmon: Path) -> None:
    for channel in EXPECTED_ASSIGNMENTS:
        enable_path = hwmon / f"pwm{channel.removeprefix('fan')}_enable"
        try:
            mode = enable_path.read_text(encoding="utf-8").strip()
        except OSError as exc:
            raise NotReady(f"cannot read {enable_path}: {exc}") from exc
        if mode != "1":
            raise NotReady(f"{channel} is not in CoolerControl manual mode (pwm_enable={mode!r})")


def validate_ready(
    config_path: Path, policy_path: Path, sysfs_root: Path
) -> tuple[Path, str]:
    invocation = coolercontrol_invocation()
    hwmon, nct_uid = nct_hwmon(sysfs_root)
    validate_profiles(config_path, policy_path, nct_uid)
    validate_applied_logs(invocation)
    validate_manual_channels(hwmon)
    return hwmon, invocation


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--policy", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--sysfs-root", type=Path, required=True)
    args = parser.parse_args()

    deadline = time.monotonic() + STARTUP_TIMEOUT_SECONDS
    last_problem = "policy not ready"
    while time.monotonic() < deadline:
        try:
            hwmon, invocation = validate_ready(args.config, args.policy, args.sysfs_root)
            watchdog = hwmon / "fan_control_watchdog"
            if not watchdog.is_file():
                raise NotReady(f"{watchdog} is absent; MSI brute-force mode is not active")
            watchdog.write_text(f"{LEASE_SECONDS}\n", encoding="ascii")
            print(f"NCT6687 watchdog armed with a {LEASE_SECONDS}s lease on {hwmon}", flush=True)
            break
        except (NotReady, OSError) as exc:
            last_problem = str(exc)
            time.sleep(1)
    else:
        print(f"NCT6687 watchdog not armed: {last_problem}", file=sys.stderr)
        return 1

    while True:
        time.sleep(REFRESH_SECONDS)
        try:
            current_hwmon, current_invocation = validate_ready(
                args.config, args.policy, args.sysfs_root
            )
            if current_hwmon != hwmon or current_invocation != invocation:
                raise NotReady("CoolerControl invocation or NCT device changed")
            watchdog.write_text(f"{LEASE_SECONDS}\n", encoding="ascii")
        except (NotReady, OSError) as exc:
            # Never disarm: stopping refresh lets the kernel restore saved firmware curves/modes.
            print(f"NCT6687 watchdog refresh stopped: {exc}", file=sys.stderr, flush=True)
            return 1


if __name__ == "__main__":
    raise SystemExit(main())
