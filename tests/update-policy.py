#!/usr/bin/env python3
"""Temporary-file fixtures for the deterministic update policy core."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from modules.services.updates.policy import (
    CHANNEL,
    PolicyError,
    load_ledger,
    observe,
    select,
    validate_policy,
)


NOW = 1_800_000_000
REV_A = "a" * 40
REV_B = "b" * 40
REV_C = "c" * 40
APPS = {"firefox", "codex-cli", "codex-desktop"}
POLICY = {"defaultDays": 3, "ageGroups": {"1": ["firefox"]}, "holds": {}}


def ledger(*observations: tuple[str, int]) -> dict:
    return {
        "version": 1,
        "observations": [
            {"channel": CHANNEL, "revision": revision, "firstSeen": first_seen}
            for revision, first_seen in observations
        ],
    }


def choose(data: dict, *, app: str | None = None, current: str = REV_A,
           allowed: set[str] | None = None, revoked: set[str] | None = None,
           now: int = NOW, previous: int | None = None, policy: dict = POLICY,
           release_decision: dict | None = None) -> dict:
    return select(
        data,
        policy,
        now=now,
        supported_apps=APPS,
        application=app,
        current_revision=current,
        allowed_descendants=allowed if allowed is not None else {REV_A, REV_B, REV_C},
        revoked_revisions=revoked or set(),
        previous_check=previous,
        release_decision=release_decision,
    )


class UpdatePolicyTests(unittest.TestCase):
    def test_default_waits_until_exact_72_hour_boundary(self) -> None:
        data = ledger((REV_B, NOW - 3 * 86400))
        self.assertEqual(choose(data, current=REV_A, now=NOW - 1)["status"], "waiting")
        result = choose(data, current=REV_A)
        self.assertEqual(result["status"], "eligible")
        self.assertEqual(result["revision"], REV_B)

    def test_firefox_waits_until_exact_24_hour_boundary(self) -> None:
        data = ledger((REV_B, NOW - 86400))
        self.assertEqual(choose(data, app="firefox", current=REV_A, now=NOW - 1)["status"], "waiting")
        self.assertEqual(choose(data, app="firefox", current=REV_A)["status"], "eligible")

    def test_repeated_observation_preserves_first_seen(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "ledger.json"
            first = observe(path, CHANNEL, REV_B, NOW - 100)
            again = observe(path, CHANNEL, REV_B, NOW)
            self.assertEqual(first["observations"][0]["firstSeen"], NOW - 100)
            self.assertEqual(again["observations"][0]["firstSeen"], NOW - 100)
            self.assertEqual(load_ledger(path), again)

    def test_frequent_new_heads_do_not_starve_an_eligible_head(self) -> None:
        data = ledger((REV_A, NOW - 4 * 86400), (REV_B, NOW - 2 * 86400), (REV_C, NOW))
        result = choose(data, current="d" * 40, allowed={REV_A, REV_B, REV_C, "d" * 40})
        self.assertEqual(result["status"], "eligible")
        self.assertEqual(result["revision"], REV_A)

    def test_clock_rollback_fails_closed(self) -> None:
        result = choose(ledger((REV_B, NOW - 10 * 86400)), previous=NOW + 1)
        self.assertEqual(result["status"], "waiting")
        self.assertEqual(result["reason"], "clock-rollback")

    def test_malformed_existing_ledger_is_not_reset(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "ledger.json"
            path.write_text("{broken", encoding="utf-8")
            with self.assertRaisesRegex(PolicyError, "malformed existing ledger"):
                observe(path, CHANNEL, REV_B, NOW)
            self.assertEqual(path.read_text(encoding="utf-8"), "{broken")

    def test_hold_precedes_group_and_stays_held_after_review_date(self) -> None:
        policy = {
            "defaultDays": 3,
            "ageGroups": {"0": ["firefox"]},
            "holds": {"firefox": {
                "reason": "waiting for upstream fix",
                "reviewAfter": "2027-06-01",
                "pin": "opaque-source-ref",
            }},
        }
        before_due = choose(ledger((REV_B, NOW - 100 * 86400)), app="firefox", policy=policy)
        self.assertEqual(before_due["status"], "held")
        self.assertFalse(before_due["reviewDue"])
        after_time = int(datetime(2027, 6, 2, tzinfo=timezone.utc).timestamp())
        after_due = choose(ledger((REV_B, NOW - 100 * 86400)), app="firefox", policy=policy, now=after_time)
        self.assertEqual(after_due["status"], "held")
        self.assertTrue(after_due["reviewDue"])
        self.assertFalse(after_due["evidence"]["holdReleased"])

    def test_conditional_hold_requires_exact_revision_and_version_adapter_decision(self) -> None:
        policy = {
            "defaultDays": 3,
            "ageGroups": {},
            "holds": {"codex-cli": {
                "reason": "waiting for the sandbox fix",
                "reviewAfter": "2026-01-01",
                "pin": "rust-v0.159.0",
                "resumeAtVersion": "0.160.0",
            }},
        }
        data = ledger((REV_B, NOW - 10 * 86400), (REV_C, NOW - 9 * 86400))
        held = choose(data, app="codex-cli", policy=policy, now=NOW + 10_000_000)
        self.assertEqual(held["status"], "held")
        self.assertTrue(held["reviewDue"])
        self.assertEqual(held["resumeAtVersion"], "0.160.0")

        mismatched = choose(
            data, app="codex-cli", policy=policy, now=NOW,
            release_decision={"application": "firefox", "threshold": "0.160.0",
                              "eligibleRevisions": [REV_B]},
        )
        self.assertEqual(mismatched["status"], "held")

        released = choose(
            data, app="codex-cli", current="d" * 40,
            allowed={REV_B, REV_C, "d" * 40}, policy=policy, now=NOW,
            release_decision={"application": "codex-cli", "threshold": "0.160.0",
                              "eligibleRevisions": [REV_B]},
        )
        self.assertEqual(released["status"], "eligible")
        self.assertEqual(released["revision"], REV_B)
        self.assertEqual(released["evidence"]["holdReleaseDecision"]["revision"], REV_B)

    def test_null_resume_version_means_indefinite_hold(self) -> None:
        policy = {
            "defaultDays": 0, "ageGroups": {},
            "holds": {"codex-desktop": {
                "reason": "containment review", "reviewAfter": "2020-01-01",
                "pin": "reviewed-source", "resumeAtVersion": None,
            }},
        }
        decision = {"application": "codex-desktop", "threshold": None,
                    "eligibleRevisions": [REV_B]}
        result = choose(ledger((REV_B, NOW - 100)), app="codex-desktop",
                        policy=policy, release_decision=decision)
        self.assertEqual(result["status"], "held")
        self.assertIsNone(result["resumeAtVersion"])

    def test_duplicate_and_unsupported_group_configuration_is_rejected(self) -> None:
        duplicate = {"defaultDays": 3, "ageGroups": {"1": ["firefox"], "2": ["firefox"]}, "holds": {}}
        with self.assertRaisesRegex(PolicyError, "multiple age groups"):
            validate_policy(duplicate, APPS)
        unsupported = {"defaultDays": 3, "ageGroups": {"1": ["unknown-app"]}, "holds": {}}
        with self.assertRaisesRegex(PolicyError, "unsupported application"):
            validate_policy(unsupported, APPS)

    def test_revoked_candidate_is_not_selected(self) -> None:
        data = ledger((REV_A, NOW - 10 * 86400), (REV_B, NOW - 9 * 86400))
        result = choose(data, current=REV_A, revoked={REV_B})
        self.assertEqual(result["status"], "unchanged")
        self.assertEqual(result["revision"], REV_A)

    def test_candidate_outside_independently_allowed_descendants_is_rejected(self) -> None:
        with self.assertRaisesRegex(PolicyError, "include current_revision"):
            choose(ledger((REV_B, NOW - 10 * 86400)), allowed={REV_B})
        result = choose(
            ledger((REV_B, NOW - 10 * 86400)),
            current=REV_A,
            allowed={REV_A},
        )
        self.assertEqual(result["status"], "waiting")
        self.assertEqual(result["reason"], "no-eligible-observation")

    def test_current_candidate_returns_unchanged(self) -> None:
        result = choose(ledger((REV_A, NOW - 10 * 86400)), current=REV_A)
        self.assertEqual(result["status"], "unchanged")
        self.assertEqual(result["revision"], REV_A)

    def test_ledger_rejects_duplicate_or_boolean_timestamp_records(self) -> None:
        duplicate = ledger((REV_A, NOW), (REV_A, NOW))
        with self.assertRaisesRegex(PolicyError, "duplicate or inconsistent"):
            select(duplicate, POLICY, now=NOW, supported_apps=APPS,
                   current_revision=REV_A, allowed_descendants={REV_A})
        boolean_time = ledger((REV_B, True))
        with self.assertRaisesRegex(PolicyError, "firstSeen"):
            select(boolean_time, POLICY, now=NOW, supported_apps=APPS,
                   current_revision=REV_A, allowed_descendants={REV_A})


if __name__ == "__main__":
    unittest.main()
