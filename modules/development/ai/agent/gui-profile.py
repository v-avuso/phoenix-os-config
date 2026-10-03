"""One-time selected desktop preferences; run under the host GUI lifetime lock.

Never synchronize profiles. Pinned desktop atoms include auth resume tokens,
drafts and history; only the fixed, typed preference fields below are imported.
Worker CLI config is separate and is not changed by this display-state seed.
"""
import json
import math
import os
import re
from pathlib import Path
import sys
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
        approved = [Path(path) for path in workspaces]
        chosen = {}
        for key, value in projects.items():
            if not isinstance(value, dict) or value.get("id") != key or not isinstance(value.get("rootPaths"), list):
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


def seed(config):
    marker, source, destination = map(Path, (config["marker"], config["source"], config["destination"]))
    if marker.exists() or not source.exists():
        return
    if destination.resolve() != destination or marker.resolve() != marker:
        raise ValueError("Desktop preferences destination must not be aliased")
    account = None
    launcher = read_object(Path(config["launcherConfig"]))
    account_file = Path(launcher["state"]) / "account-id.json"
    if account_file.exists():
        account = str(uuid.UUID(json.loads(account_file.read_text())))
    patch = selected(read_object(source), account, config["workspaces"])
    current = read_object(destination) if destination.exists() else {}
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
    destination.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    with tempfile.NamedTemporaryFile(mode="w", dir=destination.parent, delete=False) as stream:
        temporary = Path(stream.name)
        try:
            json.dump(current, stream)
            stream.flush()
            os.fsync(stream.fileno())
            os.replace(temporary, destination)
        finally:
            temporary.unlink(missing_ok=True)
    marker.write_text("Selected desktop preferences seeded; worker config unchanged.\n")


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
