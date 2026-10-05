"""Deterministic policy helpers for a later stable-update planner.

This module validates caller-supplied observations and policy. It does not
verify that a revision was published on the advertised channel, fetch Git,
prove ancestry, inspect a package, or enforce a pin. Those facts must be
verified by the planner's independent observers and adapters.
"""

from __future__ import annotations

from contextlib import contextmanager
from datetime import date, datetime, timezone
import fcntl
import json
import os
from pathlib import Path
import re
import tempfile
from typing import Any, Iterator, Mapping


SCHEMA_VERSION = 1
CHANNEL = "nixos-26.05"
MAX_TIMESTAMP = 253402300799  # 9999-12-31T23:59:59Z
_REVISION = re.compile(r"(?:[0-9a-fA-F]{40}|[0-9a-fA-F]{64})\Z")
_APP = re.compile(r"[a-z0-9][a-z0-9._+-]*\Z")
_DAY_KEY = re.compile(r"(?:0|[1-9][0-9]*)\Z")


class PolicyError(ValueError):
    """Invalid policy, observation, or ledger data."""


def _timestamp(value: Any, field: str) -> int:
    if type(value) is not int or not 0 <= value <= MAX_TIMESTAMP:
        raise PolicyError(f"{field} must be an integer UTC Unix timestamp")
    return value


def _revision(value: Any, field: str = "revision") -> str:
    if not isinstance(value, str) or not _REVISION.fullmatch(value):
        raise PolicyError(f"{field} must be a full SHA-1 or SHA-256 revision")
    return value.lower()


def _channel(value: Any) -> str:
    if value != CHANNEL:
        raise PolicyError(f"channel must be {CHANNEL!r}")
    return CHANNEL


def _no_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise PolicyError(f"duplicate JSON field: {key}")
        result[key] = value
    return result


def _validate_record(record: Any) -> dict[str, Any]:
    if not isinstance(record, dict) or set(record) != {"channel", "revision", "firstSeen"}:
        raise PolicyError("observation must contain exactly channel, revision, and firstSeen")
    return {
        "channel": _channel(record["channel"]),
        "revision": _revision(record["revision"]),
        "firstSeen": _timestamp(record["firstSeen"], "firstSeen"),
    }


def _validate_ledger(data: Any) -> dict[str, Any]:
    if not isinstance(data, dict) or set(data) != {"version", "observations"}:
        raise PolicyError("ledger must contain exactly version and observations")
    if type(data["version"]) is not int or data["version"] != SCHEMA_VERSION:
        raise PolicyError(f"unsupported ledger version (expected {SCHEMA_VERSION})")
    if not isinstance(data["observations"], list):
        raise PolicyError("ledger observations must be a list")
    observations = [_validate_record(item) for item in data["observations"]]
    revisions: set[str] = set()
    for item in observations:
        revision = item["revision"]
        if revision in revisions:
            raise PolicyError(f"duplicate or inconsistent observation for {revision}")
        revisions.add(revision)
    return {"version": SCHEMA_VERSION, "observations": observations}


@contextmanager
def _ledger_lock(path: Path) -> Iterator[None]:
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = path.with_name(path.name + ".lock")
    descriptor = os.open(lock_path, os.O_CREAT | os.O_RDWR | os.O_CLOEXEC, 0o600)
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX)
        yield
    finally:
        fcntl.flock(descriptor, fcntl.LOCK_UN)
        os.close(descriptor)


def _read_ledger(path: Path) -> dict[str, Any]:
    try:
        raw = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return {"version": SCHEMA_VERSION, "observations": []}
    except UnicodeDecodeError as exc:
        raise PolicyError(f"malformed existing ledger: {exc}") from exc
    try:
        parsed = json.loads(raw, object_pairs_hook=_no_duplicate_keys)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise PolicyError(f"malformed existing ledger: {exc}") from exc
    return _validate_ledger(parsed)


def _write_ledger(path: Path, ledger: dict[str, Any]) -> None:
    payload = json.dumps(ledger, sort_keys=True, indent=2) + "\n"
    temporary: str | None = None
    try:
        fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            os.fchmod(stream.fileno(), 0o600)
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        temporary = None
        directory_fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        if temporary is not None:
            try:
                os.unlink(temporary)
            except FileNotFoundError:
                pass


def load_ledger(path: str | os.PathLike[str]) -> dict[str, Any]:
    """Read a validated ledger under its inter-process lock.

    A missing file is an empty ledger. Existing invalid data raises PolicyError.
    """
    ledger_path = Path(path)
    with _ledger_lock(ledger_path):
        return _read_ledger(ledger_path)


def observe(
    path: str | os.PathLike[str], channel: str, revision: str, first_seen: int
) -> dict[str, Any]:
    """Retain an observation without resetting the first-seen time."""
    candidate = _validate_record({"channel": channel, "revision": revision, "firstSeen": first_seen})
    ledger_path = Path(path)
    with _ledger_lock(ledger_path):
        ledger = _read_ledger(ledger_path)
        previous = next(
            (item for item in ledger["observations"] if item["revision"] == candidate["revision"]),
            None,
        )
        if previous is not None:
            if previous["channel"] != candidate["channel"]:
                raise PolicyError("revision was already recorded on a different channel")
            return ledger
        ledger["observations"].append(candidate)
        ledger["observations"].sort(key=lambda item: (item["firstSeen"], item["revision"]))
        _write_ledger(ledger_path, ledger)
        return ledger


def validate_policy(policy: Any, supported_apps: set[str] | frozenset[str]) -> dict[str, Any]:
    """Validate and normalize the JSON/Nix-mappable policy shape."""
    if not isinstance(policy, Mapping) or set(policy) != {"defaultDays", "ageGroups", "holds"}:
        raise PolicyError("policy must contain exactly defaultDays, ageGroups, and holds")
    supported = frozenset(supported_apps)
    for app in supported:
        if not isinstance(app, str) or not _APP.fullmatch(app):
            raise PolicyError(f"invalid supported application identifier: {app!r}")

    def days(value: Any, where: str) -> int:
        if type(value) is not int or not 0 <= value <= 365:
            raise PolicyError(f"{where} must be a whole number from 0 through 365")
        return value

    default_days = days(policy["defaultDays"], "defaultDays")
    groups = policy["ageGroups"]
    if not isinstance(groups, Mapping):
        raise PolicyError("ageGroups must be an object")
    normalized_groups: dict[str, list[str]] = {}
    assigned: set[str] = set()
    for key, members in groups.items():
        if not isinstance(key, str) or not _DAY_KEY.fullmatch(key) or int(key) > 365:
            raise PolicyError(f"invalid canonical ageGroups day key: {key!r}")
        if not isinstance(members, list):
            raise PolicyError(f"ageGroups[{key!r}] must be a list")
        normalized_members: list[str] = []
        for app in members:
            if not isinstance(app, str) or not _APP.fullmatch(app):
                raise PolicyError(f"invalid application identifier in ageGroups[{key!r}]")
            if app not in supported:
                raise PolicyError(f"unsupported application identifier: {app}")
            if app in assigned:
                raise PolicyError(f"application appears in multiple age groups: {app}")
            assigned.add(app)
            normalized_members.append(app)
        normalized_groups[key] = normalized_members

    holds = policy["holds"]
    if not isinstance(holds, Mapping):
        raise PolicyError("holds must be an object")
    normalized_holds: dict[str, dict[str, str]] = {}
    for app, hold in holds.items():
        if not isinstance(app, str) or not _APP.fullmatch(app):
            raise PolicyError(f"invalid hold application identifier: {app!r}")
        if app not in supported:
            raise PolicyError(f"unsupported application identifier: {app}")
        if app in normalized_holds:
            raise PolicyError(f"duplicate hold for application: {app}")
        required_fields = {"reason", "reviewAfter", "pin"}
        allowed_fields = required_fields | {"resumeAtVersion"}
        if not isinstance(hold, Mapping) or not required_fields <= set(hold) or not set(hold) <= allowed_fields:
            raise PolicyError(f"hold for {app} must contain reason, reviewAfter, pin, and optional resumeAtVersion")
        reason, pin, review_after = hold["reason"], hold["pin"], hold["reviewAfter"]
        if not isinstance(reason, str) or not reason.strip():
            raise PolicyError(f"hold reason for {app} must be nonempty")
        if not isinstance(pin, str) or not pin.strip():
            raise PolicyError(f"hold pin for {app} must be nonempty")
        if not isinstance(review_after, str):
            raise PolicyError(f"hold reviewAfter for {app} must be an ISO calendar date")
        try:
            parsed_date = date.fromisoformat(review_after)
        except ValueError as exc:
            raise PolicyError(f"hold reviewAfter for {app} must be an ISO calendar date") from exc
        if parsed_date.isoformat() != review_after:
            raise PolicyError(f"hold reviewAfter for {app} must use YYYY-MM-DD")
        normalized_hold = {
            "reason": reason,
            "reviewAfter": review_after,
            "pin": pin,
        }
        resume_version = hold.get("resumeAtVersion")
        if resume_version is not None:
            if not isinstance(resume_version, str) or not resume_version.strip():
                raise PolicyError(f"hold resumeAtVersion for {app} must be a nonempty version or null")
            normalized_hold["resumeAtVersion"] = resume_version
        normalized_holds[app] = normalized_hold
    return {
        "defaultDays": default_days,
        "ageGroups": normalized_groups,
        "holds": normalized_holds,
    }


def select(
    ledger: Any,
    policy: Any,
    *,
    now: int,
    supported_apps: set[str] | frozenset[str],
    application: str | None = None,
    current_revision: str,
    allowed_descendants: set[str] | frozenset[str],
    revoked_revisions: set[str] | frozenset[str] = frozenset(),
    previous_check: int | None = None,
    release_decision: Any = None,
) -> dict[str, Any]:
    """Select the newest eligible retained snapshot using caller-supplied facts.

    ``allowed_descendants`` must be produced by an independent ancestry check
    and include the currently approved revision. Revisions outside that set are
    never considered. For a conditional hold, ``release_decision`` must bind
    the active application and exact configured threshold to the exact eligible
    revisions; its revision list means independently verified stable payloads
    in the same release family at or above that threshold. This helper never
    compares versions or infers ancestry from strings or dates.
    """
    now = _timestamp(now, "now")
    if previous_check is not None:
        previous_check = _timestamp(previous_check, "previous_check")
        if now < previous_check:
            return {"status": "waiting", "reason": "clock-rollback", "now": now}

    validated_policy = validate_policy(policy, supported_apps)
    validated_ledger = _validate_ledger(ledger)
    current = _revision(current_revision, "current_revision")
    allowed = frozenset(_revision(value, "allowed descendant") for value in allowed_descendants)
    revoked = frozenset(_revision(value, "revoked revision") for value in revoked_revisions)
    if current not in allowed:
        raise PolicyError("allowed_descendants must include current_revision")
    hold = None
    release_revisions: set[str] = set()
    if application is not None:
        if application not in frozenset(supported_apps):
            raise PolicyError(f"unsupported application identifier: {application}")
        hold = validated_policy["holds"].get(application)
        if hold is not None:
            utc_today = datetime.fromtimestamp(now, tz=timezone.utc).date()
            due = utc_today >= date.fromisoformat(hold["reviewAfter"])
            resume_version = hold.get("resumeAtVersion")
            if resume_version is not None and isinstance(release_decision, Mapping):
                if (
                    release_decision.get("application") == application
                    and release_decision.get("threshold") == resume_version
                    and isinstance(release_decision.get("eligibleRevisions"), list)
                ):
                    try:
                        release_revisions = {
                            _revision(value, "release decision revision")
                            for value in release_decision["eligibleRevisions"]
                        }
                    except PolicyError:
                        # Untrusted or incompatible release evidence keeps the hold.
                        release_revisions = set()
            if not release_revisions:
                return {
                    "status": "held",
                    "application": application,
                    "reason": hold["reason"],
                    "pin": hold["pin"],
                    "reviewAfter": hold["reviewAfter"],
                    "reviewDue": due,
                    "resumeAtVersion": resume_version,
                    "evidence": {"holdTakesPrecedence": True, "holdReleased": False},
                }
        else:
            release_revisions = set()
        days = next(
            (int(day) for day, apps in validated_policy["ageGroups"].items() if application in apps),
            validated_policy["defaultDays"],
        )
    else:
        days = validated_policy["defaultDays"]

    cutoff = now - days * 86400
    eligible = [
        item for item in validated_ledger["observations"]
        if item["channel"] == CHANNEL
        and item["firstSeen"] <= cutoff
        and item["revision"] in allowed
        and item["revision"] not in revoked
        and (hold is None or item["revision"] in release_revisions)
    ]
    if not eligible:
        if application is not None and hold is not None:
            return {
                "status": "held",
                "application": application,
                "reason": hold["reason"],
                "pin": hold["pin"],
                "reviewAfter": hold["reviewAfter"],
                "reviewDue": datetime.fromtimestamp(now, tz=timezone.utc).date()
                    >= date.fromisoformat(hold["reviewAfter"]),
                "resumeAtVersion": hold.get("resumeAtVersion"),
                "evidence": {"holdTakesPrecedence": True, "holdReleased": False},
            }
        return {
            "status": "waiting",
            "reason": "no-eligible-observation",
            "application": application,
            "requiredDays": days,
            "eligibleAtOrBefore": cutoff,
        }
    # Most recently first observed wins. Revision order breaks timestamp ties.
    chosen = max(eligible, key=lambda item: (item["firstSeen"], item["revision"]))
    evidence = {
        "firstSeen": chosen["firstSeen"],
        "ageDays": (now - chosen["firstSeen"]) // 86400,
        "requiredDays": days,
        "allowedByCaller": True,
        "revoked": False,
    }
    if application is not None and hold is not None:
        evidence["holdReleaseDecision"] = {
            "application": application,
            "threshold": hold["resumeAtVersion"],
            "revision": chosen["revision"],
            "callerVerified": True,
        }
    if chosen["revision"] == current:
        return {
            "status": "unchanged",
            "application": application,
            "revision": current,
            "evidence": evidence,
        }
    return {
        "status": "eligible",
        "application": application,
        "revision": chosen["revision"],
        "channel": chosen["channel"],
        "evidence": evidence,
    }
