#!/usr/bin/env python3
"""Reconcile Phoenix-owned CoolerControl profiles before coolercontrold starts."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import subprocess
import stat
import sys
import tempfile
from pathlib import Path

import tomlkit


class ProvisionError(RuntimeError):
    pass


def read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8").strip()
    except OSError as exc:
        raise ProvisionError(f"cannot read {path}: {exc}") from exc


def unique_device_uid(devices: dict, expected_name: str) -> str:
    matches = [uid for uid, name in devices.items() if name == expected_name]
    if len(matches) != 1:
        raise ProvisionError(
            f"expected exactly one CoolerControl device named {expected_name!r}; found {len(matches)}"
        )
    return matches[0]


def nct_hardware(sysfs_root: Path, expected_channels: dict[str, str]) -> tuple[str, Path]:
    matches = []
    for name_file in sysfs_root.glob("hwmon*/name"):
        if read(name_file) == "nct6687":
            matches.append(name_file.parent)
    if len(matches) != 1:
        raise ProvisionError(f"expected one nct6687 hwmon device; found {len(matches)}")

    hwmon = matches[0]
    for channel, expected_label in expected_channels.items():
        label_file = hwmon / f"{channel}_label"
        actual_label = read(label_file)
        if actual_label != expected_label:
            raise ProvisionError(
                f"{label_file} label mismatch: expected {expected_label!r}, got {actual_label!r}"
            )
    try:
        device_path = (hwmon / "device").resolve(strict=True)
    except OSError as exc:
        raise ProvisionError(f"cannot resolve NCT device path for {hwmon}: {exc}") from exc
    uid = hashlib.sha256(("Hwmon" + str(device_path)).encode()).hexdigest()
    return uid, hwmon


def inline_table(values: dict):
    table = tomlkit.inline_table()
    for key, value in values.items():
        table[key] = inline_table(value) if isinstance(value, dict) else tomlkit.item(value)
    return table


def profile_table(spec: dict, cpu_uid: str, gpu_uid: str, policy: dict) -> dict:
    table = {
        "uid": spec["uid"],
        "name": spec["name"],
        "p_type": spec["p_type"],
        "function_uid": "phoenix-case-standard-v1"
        if spec["p_type"] == "Graph"
        else "0",
    }
    if spec["p_type"] == "Graph":
        source_uid = cpu_uid if spec["temp_source"] == "cpu" else gpu_uid
        # Use the host-declared CoolerControl channel IDs.
        temp_name = policy["cpuTempName"] if spec["temp_source"] == "cpu" else policy["gpuTempName"]
        table["temp_source"] = inline_table({"device_uid": source_uid, "temp_name": temp_name})
        table["speed_profile"] = spec["speed_profile"]
        table["temp_min"] = 20.0
        table["temp_max"] = 120.0
    elif spec["p_type"] == "Mix":
        table["member_profile_uids"] = spec["member_profile_uids"]
        table["mix_function_type"] = spec["mix_function_type"]
    elif spec["p_type"] == "Fixed":
        table["speed_fixed"] = spec["speed_fixed"]
    else:
        raise ProvisionError(f"unsupported Phoenix profile type: {spec['p_type']!r}")
    return table


def replace_owned_table(array, wanted: dict, section: str) -> None:
    uid = wanted["uid"]
    entries = [entry for entry in array if entry.get("uid") == uid]
    if len(entries) > 1:
        raise ProvisionError(f"duplicate {section} UID {uid!r}")
    name_collisions = [entry for entry in array if entry.get("name") == wanted["name"] and entry.get("uid") != uid]
    if name_collisions:
        raise ProvisionError(f"{section} name {wanted['name']!r} belongs to another UID")
    table = tomlkit.table()
    for key, value in wanted.items():
        table[key] = tomlkit.item(value)
    if entries:
        index = array.index(entries[0])
        array[index] = table
    else:
        array.append(table)


def validate_gpu_sensor(document, gpu_uid: str, policy: dict, nvidia_smi: Path) -> None:
    """Require CoolerControl to expose a live GPU Temp source for the expected GPU."""
    settings = document.get("settings")
    gpu_settings = settings.get(gpu_uid, {}) if isinstance(settings, dict) else {}
    if not isinstance(gpu_settings, dict):
        raise ProvisionError(f"CoolerControl settings for GPU {gpu_uid} are invalid")
    if gpu_settings.get("disable", False) is True:
        raise ProvisionError("NVIDIA RTX 5090 is disabled in CoolerControl settings")
    channel_settings = gpu_settings.get("channel_settings", {})
    if not isinstance(channel_settings, dict):
        raise ProvisionError("CoolerControl NVIDIA channel settings are invalid")
    gpu_temp_settings = channel_settings.get(policy["gpuTempName"], {})
    if not isinstance(gpu_temp_settings, dict):
        raise ProvisionError("CoolerControl NVIDIA GPU Temp channel settings are invalid")
    if gpu_temp_settings.get("disabled", False) is True:
        raise ProvisionError("CoolerControl NVIDIA GPU Temp channel is disabled")
    legacy_disabled = gpu_settings.get("disable_channels", [])
    if not isinstance(legacy_disabled, list):
        raise ProvisionError("CoolerControl NVIDIA disabled channel list is invalid")
    if policy["gpuTempName"] in legacy_disabled:
        raise ProvisionError("CoolerControl NVIDIA GPU Temp channel is disabled")

    expected_name = policy["gpuDeviceName"]
    try:
        result = subprocess.run(
            [
                str(nvidia_smi),
                "--query-gpu=name,temperature.gpu",
                "--format=csv,noheader,nounits",
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ProvisionError(f"cannot read NVIDIA GPU temperature using {nvidia_smi}: {exc}") from exc
    if result.returncode != 0:
        detail = result.stderr.strip() or f"exit status {result.returncode}"
        raise ProvisionError(f"nvidia-smi GPU temperature query failed: {detail}")

    rows = [row for row in csv.reader(result.stdout.splitlines()) if row]
    expected = [row for row in rows if len(row) == 2 and row[0].strip() == expected_name]
    if len(expected) != 1:
        raise ProvisionError(
            f"expected one NVIDIA temperature source for {expected_name!r}; found {len(expected)}"
        )
    try:
        temperature = float(expected[0][1].strip())
    except ValueError as exc:
        raise ProvisionError(
            f"NVIDIA temperature for {expected_name!r} is not numeric: {expected[0][1].strip()!r}"
        ) from exc
    if not 0.0 <= temperature <= 150.0:
        raise ProvisionError(
            f"NVIDIA temperature for {expected_name!r} is outside the valid range: {temperature}"
        )


def validate_gpu_mix(policy: dict, cpu_uid: str, gpu_uid: str) -> None:
    """Require the assigned Max mix to reference both validated graph sources."""
    profiles = {profile["uid"]: profile for profile in policy["profiles"]}
    cpu_profiles = [
        profile for profile in profiles.values()
        if profile.get("p_type") == "Graph" and profile.get("temp_source") == "cpu"
    ]
    gpu_profiles = [
        profile for profile in profiles.values()
        if profile.get("p_type") == "Graph" and profile.get("temp_source") == "gpu"
    ]
    if len(cpu_profiles) != 1 or len(gpu_profiles) != 1:
        raise ProvisionError("Phoenix policy must define exactly one CPU and one GPU graph profile")
    mix_profiles = [profile for profile in profiles.values() if profile.get("p_type") == "Mix"]
    if len(mix_profiles) != 1:
        raise ProvisionError("Phoenix policy must define exactly one CPU/GPU mix profile")
    mix = mix_profiles[0]
    if mix.get("mix_function_type") != "Max" or set(mix.get("member_profile_uids", [])) != {
        cpu_profiles[0]["uid"],
        gpu_profiles[0]["uid"],
    }:
        raise ProvisionError("Phoenix Maximum mix must include both CPU and GPU graph profiles")
    if policy["gpuTempName"] != "GPU Temp":
        raise ProvisionError("Phoenix GPU graph must use CoolerControl's NVIDIA 'GPU Temp' channel")
    if not cpu_uid or not gpu_uid:
        raise ProvisionError("Phoenix CPU/GPU graph profiles require validated device UIDs")
    if any(policy["assignments"].get(channel) != mix["uid"] for channel in ("fan1", "fan3", "fan4", "fan5")):
        raise ProvisionError("all curve-controlled case fans must use the validated CPU/GPU Maximum mix")


def apply_policy(document, policy: dict, sysfs_root: Path, nvidia_smi: Path) -> None:
    devices = document.get("devices")
    if devices is None or not isinstance(devices, dict):
        raise ProvisionError("CoolerControl [devices] table is absent; start the daemon once, then restart it to provision")

    nct_uid, _hwmon = nct_hardware(sysfs_root, policy["channels"])
    configured_nct_uid = unique_device_uid(devices, policy["nctDeviceName"])
    if configured_nct_uid != nct_uid:
        raise ProvisionError(
            "CoolerControl NCT UID does not match the current NCT sysfs device path "
            f"(configured {configured_nct_uid}, detected {nct_uid})"
        )

    cpu_uid = unique_device_uid(devices, policy["cpuDeviceName"])
    gpu_uid = unique_device_uid(devices, policy["gpuDeviceName"])
    validate_gpu_sensor(document, gpu_uid, policy, nvidia_smi)
    validate_gpu_mix(policy, cpu_uid, gpu_uid)

    # Confirm that CoolerControl's expected CPU source corresponds to the live
    # k10temp Tctl sensor before writing any profile references.
    cpu_hwmon = [p.parent for p in sysfs_root.glob("hwmon*/name") if read(p) == "k10temp"]
    if len(cpu_hwmon) != 1 or read(cpu_hwmon[0] / "temp1_label") != "Tctl":
        raise ProvisionError("expected exactly one k10temp device with temp1_label=Tctl")

    funcs = document.get("functions")
    if funcs is None:
        funcs = tomlkit.aot()
        document["functions"] = funcs
    if not isinstance(funcs, list):
        raise ProvisionError("CoolerControl functions setting is not an array of tables")
    fn = policy["function"]
    function = {
        "uid": fn["uid"],
        "name": fn["name"],
        "f_type": "Standard",
        "duty_minimum": 1,
        "duty_maximum": 100,
        "step_size_min_decreasing": 0,
        "step_size_max_decreasing": 0,
        "response_delay": fn["response_delay"],
        "deviance": fn["deviance"],
        "only_downward": False,
        "threshold_hopping": fn["threshold_hopping"],
    }
    replace_owned_table(funcs, function, "function")

    profiles = document.get("profiles")
    if profiles is None:
        profiles = tomlkit.aot()
        document["profiles"] = profiles
    if not isinstance(profiles, list):
        raise ProvisionError("CoolerControl profiles setting is not an array of tables")
    for spec in policy["profiles"]:
        replace_owned_table(profiles, profile_table(spec, cpu_uid, gpu_uid, policy), "profile")

    settings = document.get("settings")
    if settings is None or settings.get("apply_on_boot") is not True:
        raise ProvisionError("CoolerControl settings.apply_on_boot must already be true")

    device_settings = document.get("device-settings")
    if device_settings is None:
        device_settings = tomlkit.table()
        document["device-settings"] = device_settings
    if not isinstance(device_settings, dict):
        raise ProvisionError("CoolerControl [device-settings] table is invalid")

    channels = device_settings.get(nct_uid)
    if channels is None:
        channels = tomlkit.table()
        device_settings[nct_uid] = channels
    if not isinstance(channels, dict):
        raise ProvisionError(f"device-settings.{nct_uid} is not a table")
    for channel, profile_uid in policy["assignments"].items():
        if channel not in policy["channels"]:
            raise ProvisionError(f"assignment channel {channel!r} has no validated label")
        channels[channel] = inline_table({"profile_uid": profile_uid})
    # Removing saved entries leaves these channels in CoolerControl's Unmanaged
    # state and prevents a stale persisted profile from being reapplied.
    for channel in ("fan7", "fan8"):
        channels.pop(channel, None)


def atomic_write(path: Path, data: str, reference: Path | None = None) -> None:
    original_stat = (reference or path).stat()
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as target:
            target.write(data)
            target.flush()
            os.fsync(target.fileno())
        os.chmod(temp_name, stat.S_IMODE(original_stat.st_mode))
        os.chown(temp_name, original_stat.st_uid, original_stat.st_gid)
        os.replace(temp_name, path)
        dir_fd = os.open(path.parent, os.O_DIRECTORY)
        try:
            os.fsync(dir_fd)
        finally:
            os.close(dir_fd)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--policy", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--sysfs-root", type=Path, required=True)
    parser.add_argument("--nvidia-smi", type=Path, required=True)
    parser.add_argument("--output", type=Path, help="write rendered config here instead of changing --config")
    args = parser.parse_args()

    try:
        policy = json.loads(args.policy.read_text(encoding="utf-8"))
        if not args.config.exists():
            print("CoolerControl config not initialized; leaving daemon unmanaged on this first start", file=sys.stderr)
            return 0
        if args.config.is_symlink():
            raise ProvisionError("refusing to modify a symlinked CoolerControl config.toml")
        original = args.config.read_text(encoding="utf-8")
        document = tomlkit.parse(original)
        apply_policy(document, policy, args.sysfs_root, args.nvidia_smi)
        rendered = document.as_string()
        destination = args.output or args.config
        if rendered != original:
            atomic_write(destination, rendered, args.config)
        elif args.output and destination != args.config:
            atomic_write(destination, rendered, args.config)
        print(
            "Phoenix CoolerControl profiles reconciled for "
            f"{policy['nctDeviceName']} at {args.sysfs_root}"
        )
        return 0
    except (OSError, ValueError, KeyError, TypeError, ProvisionError, tomlkit.exceptions.TOMLKitError) as exc:
        print(f"Phoenix CoolerControl policy not applied: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
