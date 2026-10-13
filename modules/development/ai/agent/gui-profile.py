"""Selected desktop preferences/projects; run under the host GUI lifetime lock.

Preferences seed once; newly seen eligible projects import once. Never synchronize
profiles. Pinned desktop atoms include auth resume tokens,
drafts and history; only the fixed, typed preference fields below are imported.
Worker CLI config is separate and is not changed by this display-state seed.
"""
import json
import math
import os
import re
from pathlib import Path
import sys
import subprocess
import tempfile
import tomllib
import uuid

BOOL_ATOMS = ("electron:onboarding-projectless-completed", "electron:onboarding-welcome-pending")
ROLE_BOOLS = ("personalizedSuggestionsEnabled", "completedConversationalOnboarding",
              "conversationalOnboardingSkipped", "onboardingCreditRewardWarningShown")
ROLES = {"default", "engineering", "data_science", "product_management", "design", "marketing",
         "sales", "finance", "operations", "people_hr", "legal", "student", "something_else"}


def number(value):
    return type(value) in (int, float) and math.isfinite(value)


def read_object(path):
    if path.stat().st_size > 16 * 1024 * 1024:
        raise ValueError("Desktop preferences exceed bounded input")
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise ValueError("Desktop preferences must be an object")
    return value


def project_id(value):
    return isinstance(value, str) and 0 < len(value) <= 256 and not any(
        ord(c) < 32 or ord(c) == 127 for c in value)


def selected(source, account, workspaces):
    result, atoms = {}, {}
    native = source.get("electron-persisted-atom-state", {})
    if not isinstance(native, dict):
        raise ValueError("Desktop preference atoms must be an object")
    for key in BOOL_ATOMS:
        if type(native.get(key)) is bool:
            atoms[key] = native[key]
    value = native.get("last_completed_onboarding")
    if type(value) is int and value >= 0:
        atoms["last_completed_onboarding"] = value
    key = "electron:onboarding-conversational-completed-by-account-id"
    value = native.get(key)
    if account and isinstance(value, dict) and type(value.get(account)) is bool:
        atoms[key] = {account: value[account]}
    key = "electron:onboarding-welcome-v2-role-state"
    value = native.get(key)
    if isinstance(value, dict):
        role = {key: value[key] for key in ROLE_BOOLS if type(value.get(key)) is bool}
        if isinstance(value.get("roles"), list) and all(x in ROLES for x in value["roles"] if isinstance(x, str)) and all(isinstance(x, str) for x in value["roles"]):
            role["roles"] = value["roles"][:32]
        if value.get("workMode") in ("coding", "non_coding", None):
            role["workMode"] = value.get("workMode")
        if role:
            atoms[key] = role
    if atoms:
        result["electron-persisted-atom-state"] = atoms
    bounds = source.get("electron-main-window-bounds")
    if isinstance(bounds, dict) and all(number(bounds.get(k)) for k in ("x", "y", "width", "height")) and 480 <= bounds["width"] <= 16384 and 600 <= bounds["height"] <= 16384:
        result["electron-main-window-bounds"] = {k: bounds[k] for k in ("x", "y", "width", "height")}
        result["electron-main-window-bounds"]["isMaximized"] = False
        if bounds.get("isMaximized") is True:
            result["electron-main-window-bounds"].update(width=min(bounds["width"], 1400), height=min(bounds["height"], 900))
    projects = source.get("local-projects", {})
    if isinstance(projects, dict):
        if len(projects) > 1024:
            raise ValueError("Desktop project metadata exceeds bounded input")
        approved = [Path(path) for path in workspaces]
        chosen = {}
        for key, value in projects.items():
            if (not project_id(key) or not isinstance(value, dict) or value.get("id") != key
                    or not isinstance(value.get("rootPaths"), list) or len(value["rootPaths"]) > 16
                    or not isinstance(value.get("name"), str) or len(value["name"]) > 256
                    or not all(number(value.get(k)) for k in ("createdAt", "updatedAt"))):
                continue
            roots = [p for p in value["rootPaths"] if isinstance(p, str) and Path(p).is_absolute()
                     and str(Path(p).resolve()) == p and any(Path(p).is_relative_to(root) for root in approved)]
            if not roots:
                continue
            project = {"id": key, "rootPaths": roots}
            if isinstance(value.get("name"), str) and len(value["name"]) <= 256:
                project["name"] = value["name"]
            for timestamp in ("createdAt", "updatedAt"):
                if number(value.get(timestamp)):
                    project[timestamp] = value[timestamp]
            chosen[key] = project
        if chosen:
            result["local-projects"] = chosen
    return result


def atomic_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    with tempfile.NamedTemporaryFile(mode="w", dir=path.parent, delete=False) as stream:
        temporary = Path(stream.name)
        try:
            json.dump(value, stream)
            stream.flush()
            os.fsync(stream.fileno())
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)


def seed(config):
    marker, source, destination = map(Path, (config["marker"], config["source"], config["destination"]))
    if not source.exists():
        return
    if destination.resolve() != destination or marker.resolve() != marker:
        raise ValueError("Desktop preferences destination must not be aliased")
    seeded = marker.exists()
    prior_marker, consumed = None, set()
    if seeded:
        if marker.stat().st_size > 128 * 1024:
            raise ValueError("Desktop project import marker exceeds bounded input")
        text = marker.read_text()
        if text != "Selected desktop preferences seeded; worker config unchanged.\n":
            try:
                prior_marker = json.loads(text)
            except ValueError:
                raise ValueError("Desktop project import marker invalid") from None
            if (not isinstance(prior_marker, dict) or set(prior_marker) != {"version", "projectIds"}
                    or type(prior_marker["version"]) is not int or prior_marker["version"] != 2
                    or not isinstance(prior_marker["projectIds"], list)
                    or len(prior_marker["projectIds"]) > 4096
                    or not all(project_id(k) for k in prior_marker["projectIds"])
                    or len(set(prior_marker["projectIds"])) != len(prior_marker["projectIds"])):
                raise ValueError("Desktop project import marker invalid")
            consumed = set(prior_marker["projectIds"])
    native = read_object(source)
    current = read_object(destination) if destination.exists() else {}
    before = json.dumps(current, sort_keys=True)
    account = None
    if not seeded:
        launcher = read_object(Path(config["launcherConfig"]))
        if launcher.get("protectedIdentity"):
            result = subprocess.run(config["accountCommand"], stdout=subprocess.PIPE, stderr=sys.stderr, cwd=config["workdir"], timeout=30, check=True)
            account = str(uuid.UUID(result.stdout.decode().strip()))
        else:
            account_file = Path(launcher["state"]) / "account-id.json"
            if account_file.exists():
                account = str(uuid.UUID(json.loads(account_file.read_text())))
    patch = selected({"local-projects": native.get("local-projects", {})} if seeded else native,
                     account, config["workspaces"])
    projects = patch.pop("local-projects", {})
    existing = current.get("local-projects", {})
    if not isinstance(existing, dict):
        raise ValueError("Existing desktop projects have incompatible shape")
    # Legacy marker cannot recover removed/server-mapped IDs; preserve all entries
    # currently present and record this migration's eligible IDs going forward.
    if seeded and prior_marker is None:
        consumed.update(k for k in existing if project_id(k))
    roots = {frozenset(v["rootPaths"]) for v in existing.values()
             if isinstance(v, dict) and isinstance(v.get("rootPaths"), list)
             and all(isinstance(p, str) for p in v["rootPaths"])}
    merged = dict(existing)
    for key, value in projects.items():
        project_roots = frozenset(value["rootPaths"])
        if key not in consumed and key not in merged and project_roots not in roots:
            merged[key] = value
            roots.add(project_roots)
        consumed.add(key)
    if len(consumed) > 4096:
        raise ValueError("Desktop project import marker exceeds bounded input")
    if merged:
        current["local-projects"] = merged
    for key, value in patch.items():
        if isinstance(value, dict) and key != "electron-main-window-bounds":
            prior = current.get(key, {})
            if not isinstance(prior, dict):
                raise ValueError("Existing desktop preferences have incompatible shape")
            if key == "electron-persisted-atom-state":
                value = {atom: ({**prior[atom], **pref} if isinstance(prior.get(atom), dict) and isinstance(pref, dict) else pref)
                         for atom, pref in value.items()}
            current[key] = {**prior, **value}
        else:
            current[key] = value
    next_marker = {"version": 2, "projectIds": sorted(consumed)}
    serialized_current = json.dumps(current)
    if len(serialized_current.encode()) > 16 * 1024 * 1024:
        raise ValueError("Desktop preferences exceed bounded output")
    if len(json.dumps(next_marker).encode()) > 128 * 1024:
        raise ValueError("Desktop project import marker exceeds bounded input")
    if not destination.exists() or json.dumps(current, sort_keys=True) != before:
        atomic_json(destination, current)
    if next_marker != prior_marker:
        atomic_json(marker, next_marker)


def worker_preferences(path):
    """Exact scalar preferences only; no permissions, tools or endpoint config."""
    path = Path(path)
    if not path.exists():
        print("Native model/display preferences absent; sandbox defaults apply.", file=sys.stderr)
        return {}
    if path.stat().st_size > 1024 * 1024:
        raise ValueError("Native preferences exceed bounded input")
    data, result = tomllib.loads(path.read_text()), {}
    model = data.get("model")
    if isinstance(model, str) and re.fullmatch(r"[A-Za-z0-9_.-]{1,80}", model):
        result["model"] = model
    for key, choices in (("model_reasoning_effort", ("none", "minimal", "low", "medium", "high", "xhigh", "max", "ultra")),
                         ("service_tier", ("default", "fast", "priority", "flex"))):
        if data.get(key) in choices:
            result[key] = data[key]
    desktop = data.get("desktop", {})
    if isinstance(desktop, dict):
        for key, choices in (("followUpQueueMode", ("queue", "steer", "interrupt")),
                             ("conversationDetailMode", ("STEPS_PROSE", "STEPS_COMMANDS", "STEPS_EXECUTION")),
                             ("appearanceTheme", ("system", "light", "dark"))):
            if desktop.get(key) in choices:
                result["desktop." + key] = desktop[key]
        if type(desktop.get("ambient-suggestions-enabled")) is bool:
            result["desktop.ambient-suggestions-enabled"] = desktop["ambient-suggestions-enabled"]
    return result


if __name__ == "__main__":
    os.umask(0o077)
    if sys.argv[1] == "--worker":
        print(json.dumps(worker_preferences(sys.argv[2])))
    else:
        seed(read_object(Path(sys.argv[1])))
