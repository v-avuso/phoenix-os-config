"""Deterministic acceptance rules for routine, already-published updates.

This deliberately does not produce a reviewer verdict. It limits unattended
source changes to frozen input identities, exact package policy, and declared
patch files before the protected controller builds the frozen source.
"""
import base64
import json
import re
import urllib.request
from pathlib import Path

VERSION = re.compile(r"[0-9]+(?:\.[0-9]+){1,3}\Z")
REVISION = re.compile(r"[0-9a-f]{40,64}\Z")
ROOT_INPUTS = {"nixpkgs", "nixpkgs-unstable", "codex-desktop-linux", "codex-desktop-sandbox"}
COMMUNITY_CHECKS = {"source-and-node", "rust", "nix", "official-linux-gate"}


def _lock(files):
    value = json.loads(files["flake.lock"])
    if (not isinstance(value, dict) or not isinstance(value.get("nodes"), dict) or
            not isinstance(value.get("root"), str) or value["root"] not in value["nodes"]):
        raise ValueError("invalid update lock")
    root = value["nodes"][value["root"]]
    if not isinstance(root, dict) or not isinstance(root.get("inputs"), dict):
        raise ValueError("invalid update lock root")
    return value


def _node(lock, alias):
    name = lock["nodes"][lock["root"]]["inputs"].get(alias)
    if not isinstance(name, str) or name not in lock["nodes"]:
        raise ValueError("missing approved update input")
    return lock["nodes"][name]


def _closure(lock, aliases):
    pending = [_node_name(lock, alias) for alias in aliases]
    seen = set()
    while pending:
        name = pending.pop()
        if name in seen:
            continue
        seen.add(name)
        node = lock["nodes"][name]
        if not isinstance(node, dict) or not isinstance(node.get("inputs", {}), dict):
            raise ValueError("invalid dependency graph")
        for child in node.get("inputs", {}).values():
            if isinstance(child, str) and child in lock["nodes"]:
                pending.append(child)
            elif isinstance(child, list):
                for item in child:
                    if isinstance(item, str) and item in lock["nodes"]:
                        pending.append(item)
    return seen


def _node_name(lock, alias):
    name = lock["nodes"][lock["root"]]["inputs"].get(alias)
    if not isinstance(name, str) or name not in lock["nodes"]:
        raise ValueError("missing approved update input")
    return name


def _identity(node):
    locked = node.get("locked")
    original = node.get("original")
    if not isinstance(locked, dict) or not isinstance(original, dict):
        raise ValueError("invalid locked input identity")
    identity = {key: locked.get(key) for key in ("type", "owner", "repo", "dir") if key in locked}
    if not identity.get("type") or not identity.get("owner") or not identity.get("repo"):
        raise ValueError("unsupported locked input identity")
    if any(original.get(key) != locked.get(key) for key in ("type", "owner", "repo") if key in original):
        raise ValueError("input publisher identity changed")
    return identity


def validate_lock(before_files, after_files, verify_current=None):
    before, after = _lock(before_files), _lock(after_files)
    if (set(before) != set(after) or before.get("version") != after.get("version") or
            before["root"] != after["root"] or
            before["nodes"][before["root"]] != after["nodes"][after["root"]]):
        raise ValueError("root input declarations changed")
    old_nodes, new_nodes = before["nodes"], after["nodes"]
    prior_origins = {json.dumps(node.get("original"), sort_keys=True) for node in old_nodes.values()
                     if isinstance(node, dict) and isinstance(node.get("original"), dict)}
    changed_aliases = {alias for alias in ROOT_INPUTS if _node(before, alias) != _node(after, alias)}
    desktop_aliases = {"codex-desktop-linux", "codex-desktop-sandbox"}
    if changed_aliases & desktop_aliases:
        if not desktop_aliases <= changed_aliases:
            raise ValueError("Community native and sandbox inputs must update together")
        native, sandbox = (_node(after, alias)["locked"] for alias in sorted(desktop_aliases))
        if any(native.get(key) != sandbox.get(key) for key in ("owner", "repo", "rev", "narHash")):
            raise ValueError("Community native and sandbox inputs must share one source revision")
    old_selected = _closure(before, changed_aliases) if changed_aliases else set()
    new_selected = _closure(after, changed_aliases) if changed_aliases else set()
    changed = {name for name in old_nodes.keys() | new_nodes.keys() if old_nodes.get(name) != new_nodes.get(name)}
    if changed - (old_selected | new_selected | {before["root"]}):
        raise ValueError("unselected dependency changed")
    root_sources = {
        "nixpkgs": ("NixOS", "nixpkgs"),
        "nixpkgs-unstable": ("NixOS", "nixpkgs"),
        "codex-desktop-linux": ("ilysenko", "codex-desktop-linux"),
        "codex-desktop-sandbox": ("ilysenko", "codex-desktop-linux"),
    }
    for alias in ROOT_INPUTS:
        original = _node(before, alias).get("original", {})
        owner, repo = root_sources[alias]
        if (original.get("type") != "github" or original.get("owner") != owner or
                original.get("repo") != repo):
            raise ValueError("root update publisher declaration is unsupported")
        if alias == "nixpkgs" and not re.fullmatch(r"nixos-[0-9]{2}\.[0-9]{2}", str(original.get("ref", ""))):
            raise ValueError("stable NixOS release branch is unsupported")
        if alias == "nixpkgs-unstable" and original.get("ref") != "nixos-unstable":
            raise ValueError("unstable channel declaration changed")
    allowed_locked = {"type", "owner", "repo", "dir", "rev", "narHash", "lastModified", "revCount", "dirtyRev"}
    for name, node in new_nodes.items():
        if name == after["root"]:
            continue
        if not isinstance(node, dict) or not isinstance(node.get("locked"), dict) or set(node["locked"]) - allowed_locked:
            raise ValueError("unsupported locked metadata")
        if name not in old_nodes:
            origin = json.dumps(node.get("original"), sort_keys=True)
            if origin not in prior_origins:
                raise ValueError("new dependency publisher or input")
            _identity(node)
            prior_nodes = [old for old in old_nodes.values()
                           if json.dumps(old.get("original"), sort_keys=True) == origin]
            if not any(node.get("inputs", {}) == old.get("inputs", {}) for old in prior_nodes):
                raise ValueError("new dependency input declaration")
            continue
        previous = old_nodes[name]
        if node.get("original") != previous.get("original"):
            raise ValueError("dependency original identity changed")
        if set(previous) != set(node):
            raise ValueError("dependency metadata fields changed")
        before_inputs, after_inputs = previous.get("inputs", {}), node.get("inputs", {})
        if not isinstance(before_inputs, dict) or not isinstance(after_inputs, dict) or before_inputs != after_inputs:
            raise ValueError("dependency input declaration changed")
        old_identity, new_identity = _identity(previous), _identity(node)
        if old_identity != new_identity:
            raise ValueError("dependency publisher identity changed")
        old_locked, new_locked = previous["locked"], node["locked"]
        if (set(old_locked) | set(new_locked)) - allowed_locked:
            raise ValueError("unsupported locked metadata")
        for key in set(old_locked) & set(new_locked):
            if key not in {"rev", "narHash", "lastModified", "revCount", "dirtyRev"} and old_locked[key] != new_locked[key]:
                raise ValueError("locked input identity changed")
    if verify_current is not None:
        for alias in sorted(changed_aliases):
            verify_current(alias, _node(after, alias))
        root_name = after["root"]
        for name in sorted(changed - old_selected - new_selected - {root_name}):
            raise ValueError("dependency escaped selected input closure")
        for name in sorted(changed & (old_selected | new_selected)):
            if name in {_node_name(after, alias) for alias in changed_aliases}:
                continue
            previous, candidate = old_nodes.get(name), new_nodes.get(name)
            if previous is not None and candidate is not None and previous.get("locked") != candidate.get("locked"):
                verify_current(None, candidate)
    return after


def _policy(files):
    policy = json.loads(files["config/updates.json"])
    if not isinstance(policy, dict) or policy.get("version") != 1:
        raise ValueError("unsupported update policy")
    if set(policy) - {"version", "packageSources", "holds", "patches", "_comments"}:
        raise ValueError("unsupported update policy fields")
    sources = policy.get("packageSources")
    if not isinstance(sources, dict) or set(sources) != {"firefox", "codex-desktop", "codex-cli"}:
        raise ValueError("unsupported package selection")
    if (sources["firefox"] not in {"nixpkgs", "nixpkgs-unstable"} or
            sources["codex-desktop"] != {"native": "codex-desktop-linux", "sandbox": "codex-desktop-sandbox"} or
            sources["codex-cli"] not in {"nixpkgs", "nixpkgs-unstable"}):
        raise ValueError("unsupported package adapter")
    holds = policy.get("holds", {})
    patches = policy.get("patches", {})
    if not isinstance(holds, dict) or not isinstance(patches, dict):
        raise ValueError("invalid update exceptions")
    for package, hold in holds.items():
        if (not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_+-]*", package) or not isinstance(hold, dict) or
                not {"pin", "reason"} <= set(hold) or set(hold) - {"pin", "reason", "resumeAtVersion", "source"} or
                not isinstance(hold["reason"], str) or not hold["reason"].strip()):
            raise ValueError("invalid package hold")
        threshold = hold.get("resumeAtVersion")
        if threshold is not None and (not isinstance(threshold, str) or not VERSION.fullmatch(threshold)):
            raise ValueError("invalid package hold threshold")
        effective_source = sources.get(package) if package in {"firefox", "codex-cli"} else "nixpkgs"
        if ((package in {"firefox", "codex-cli"} and hold.get("source", effective_source) != effective_source) or
                (package not in {"firefox", "codex-cli"} and hold.get("source", "nixpkgs") != "nixpkgs")):
            raise ValueError("hold source does not match the selected package")
        pin = hold["pin"]
        if package == "codex-desktop":
            if (not isinstance(pin, dict) or set(pin) != {"native", "sandbox"} or
                    any(not isinstance(revision, str) or not REVISION.fullmatch(revision)
                        for revision in pin.values())):
                raise ValueError("invalid desktop hold pin")
        elif not isinstance(pin, str) or not REVISION.fullmatch(pin):
            raise ValueError("invalid package hold revision")
    for package, patch in patches.items():
        if (not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_+-]*", package) or package == "codex-desktop" or
                not isinstance(patch, dict) or set(patch) - {"reason", "patchFiles", "removeAtVersion", "source"} or
                not {"reason", "patchFiles"} <= set(patch) or not isinstance(patch["reason"], str) or
                not patch["reason"].strip()):
            raise ValueError("invalid package patch policy")
        effective_source = sources.get(package) if package in {"firefox", "codex-cli"} else "nixpkgs"
        if ((package in {"firefox", "codex-cli"} and patch.get("source", effective_source) != effective_source) or
                (package not in {"firefox", "codex-cli"} and patch.get("source", "nixpkgs") != "nixpkgs")):
            raise ValueError("patch source does not match the selected package")
        paths = patch["patchFiles"]
        if (not isinstance(paths, list) or not paths or len(paths) != len(set(paths)) or
                any(not isinstance(path, str) or not re.fullmatch(r"config/update-patches/[A-Za-z0-9_+-]+\.patch", path)
                    for path in paths)):
            raise ValueError("invalid central patch file list")
        threshold = patch.get("removeAtVersion")
        if threshold is not None and (not isinstance(threshold, str) or not VERSION.fullmatch(threshold)):
            raise ValueError("invalid patch removal threshold")
    return policy


def _version(package, policy, lock, system, evaluate, desktop_version):
    if package == "codex-desktop":
        return desktop_version(lock)
    if package in {"firefox", "codex-cli"}:
        alias = policy["packageSources"][package]
        attribute = "codex" if package == "codex-cli" else "firefox"
    else:
        alias, attribute = "nixpkgs", package
    revision = _node(lock, alias)["locked"].get("rev")
    if not isinstance(revision, str) or not REVISION.fullmatch(revision):
        raise ValueError("selected package source is not immutable")
    version = evaluate(alias, revision, attribute, system)
    if not isinstance(version, str) or not VERSION.fullmatch(version):
        raise ValueError("selected package has no stable numeric version")
    return version


def validate_source(before_files, before_modes, after_files, after_modes, system, compare, evaluate,
                    desktop_version, verify_current=None):
    """Validate all changed files and narrowly permitted exception removals.

    Callbacks run Nix version lookup as the isolated unprivileged builder. The
    routine path cannot alter the flake declaration or submit a closure/verdict.
    """
    if before_files.get("flake.nix") != after_files.get("flake.nix"):
        raise ValueError("root flake declarations changed")
    before_policy, after_policy = _policy(before_files), _policy(after_files)
    for policy in (before_policy, after_policy):
        for patch in policy.get("patches", {}).values():
            for path in patch["patchFiles"]:
                if (path not in before_files or path not in after_files or
                        before_modes.get(path) != after_modes.get(path) or
                        before_files[path] != after_files[path]):
                    raise ValueError("routine updates cannot add, remove, or edit patch files")
    mutable_policy = lambda p: {key: value for key, value in p.items() if key not in {"holds", "patches"}}
    if mutable_policy(before_policy) != mutable_policy(after_policy):
        raise ValueError("update policy fields changed")
    # Resolve publisher heads once per request, including multi-exception expiry.
    lock = validate_lock(before_files, after_files, verify_current)
    for name in ("holds", "patches"):
        old, new = before_policy.get(name, {}), after_policy.get(name, {})
        if not set(new) <= set(old):
            raise ValueError("update exceptions may only be removed")
        for package in new:
            if old[package] != new[package]:
                raise ValueError("update exception fields changed")
        for package in set(old) - set(new):
            threshold = old[package].get("resumeAtVersion") if name == "holds" else old[package].get("removeAtVersion")
            if threshold is None:
                raise ValueError("indefinite update exception cannot be removed")
            observed = _version(package, before_policy, lock, system,
                                evaluate, desktop_version)
            if compare(observed, threshold) < 0:
                raise ValueError("update exception threshold is not satisfied")
            if name == "patches" and package in after_policy.get("holds", {}):
                raise ValueError("patch removal waits for the package hold to be satisfied")
    allowed = {"flake.lock", "config/updates.json"}
    for path in allowed:
        if path in before_files and path in after_files and before_modes.get(path) != after_modes.get(path):
            raise ValueError("routine update cannot change source file modes")
    if (set(before_files) - set(after_files) | set(after_files) - set(before_files) |
            {name for name in before_files.keys() & after_files.keys()
             if before_files[name] != after_files[name] or before_modes.get(name) != after_modes.get(name)}) - allowed:
        raise ValueError("routine update changed an undeclared source file")
    return lock


def validate_community_payload(path):
    payload = json.loads((Path(path) / "nix/upstream-linux-packages.json").read_text())
    if not isinstance(payload, dict) or set(payload) != {"version", "amd64", "arm64"}:
        raise ValueError("Community payload schema changed")
    version = payload["version"]
    if not isinstance(version, str) or not VERSION.fullmatch(version):
        raise ValueError("Community payload version is not stable")
    for arch in ("amd64", "arm64"):
        record = payload[arch]
        if (not isinstance(record, dict) or set(record) != {"repositoryPath", "sha256", "sri"} or
                not re.fullmatch(r"[0-9a-f]{64}", str(record.get("sha256", "")))):
            raise ValueError("Community package metadata is invalid")
        expected_path = "pool/main/c/chatgpt/chatgpt_%s_%s.deb" % (version, arch)
        expected_sri = "sha256-" + base64.b64encode(bytes.fromhex(record["sha256"])).decode()
        if record["repositoryPath"] != expected_path or record["sri"] != expected_sri:
            raise ValueError("Community payload path or hash is inconsistent")
    return version


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, response, code, message, headers, new_url):
        return None


def validate_community_checks(revision, open_url=None):
    """Require the updater's fixed upstream checks on the exact locked head."""
    if not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise ValueError("invalid Community revision")
    if open_url is None:
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), _NoRedirect())

        def open_url(url):
            request = urllib.request.Request(url, headers={
                "User-Agent": "phoenix-update-controller",
                "Accept": "application/vnd.github+json"})
            with opener.open(request, timeout=30) as response:
                if not response.geturl().startswith("https://api.github.com/"):
                    raise ValueError("unexpected Community API redirect")
                data = response.read(2 * 1024 * 1024 + 1)
            if len(data) > 2 * 1024 * 1024:
                raise ValueError("Community check response too large")
            return json.loads(data)

    checks, total = [], None
    for page in range(1, 11):
        result = open_url("https://api.github.com/repos/ilysenko/codex-desktop-linux/commits/%s/check-runs?per_page=100&page=%d" % (revision, page))
        if not isinstance(result, dict) or not isinstance(result.get("check_runs"), list) or type(result.get("total_count")) is not int:
            raise ValueError("Community checks are unavailable")
        if total is None:
            total = result["total_count"]
        checks.extend(result["check_runs"])
        if len(checks) >= total:
            break
    else:
        raise ValueError("Community checks exceed pagination bound")
    for name in COMMUNITY_CHECKS:
        matches = [record for record in checks if isinstance(record, dict) and record.get("name") == name]
        if not matches or any(record.get("head_sha") != revision or
                              not isinstance(record.get("app"), dict) or record["app"].get("slug") != "github-actions" or
                              record.get("status") != "completed" or record.get("conclusion") != "success"
                              for record in matches):
            raise ValueError("required Community check failed or is missing")
