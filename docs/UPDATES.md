# Automatic updates

`config/updates.json` owns package selection and temporary holds. The NixOS
module is connected through `modules/services/default.nix`. It checks every six
hours with up to fifteen minutes of jitter and catches up after power-off.

The system follows supported `nixos-26.05`; Firefox uses tested
`nixos-unstable` for useful freshness in a deeply used daily application.
Stable Firefox also receives security maintenance. The shared unstable input
also supplies compatible Hyprland/Caelestia/Timewall dependencies, so advancing
it can affect those applications. Community desktop and CLI follow their own
checked stable upstream releases, rather than Nixpkgs unstable. Each choice has
an explanation in the JSON comments and package declarations. No local cooldown
or daily LLM vulnerability research is used. Existing protected deployment
review still runs on actual source changes.

Each run starts from a committed source identical to the active or next-boot
reviewed source. It prepares an isolated Git worktree and commits only
`flake.lock`, the CLI recipe, and satisfied hold removals. Nix constructs locks;
maintained `nix-update` updates the conventional CLI recipe. Unchanged candidates
skip builds/review. Failed unchanged candidates retry at most daily. Community
requires its exact stable payload and successful `source-and-node`, `rust`,
`nix`, and `official-linux-gate` checks; missing checks retain that application
while independent channel updates can continue. Explicitly pinned framework
inputs retain their existing pins; this is not a blanket unlock of every input.

The protected controller builds and reviews the exact source/closure, including
complete evidence from changed upstream module/build/containment code, split
at file boundaries into at most 24 separately bound reviews, followed by the
complete configuration review. Dependency evidence compares against the
root-owned preceding next-boot source, so already staged upstream changes are
not reviewed repeatedly before reboot. The protected reviewer CLI is pinned separately from the everyday CLI, so routine
CLI updates do not replace review isolation or trigger expensive publisher-code
reviews. Deliberate reviewer upgrades must supply exact official
source evidence for changed publisher runtime authority, including configuration,
rule loading, execution and sandbox authority used by the protected reviewer; an unknown guard contract blocks deployment. This is
source evidence, not proof that a release binary reproduces that source;
Bazel repository-cache lock metadata is outside this runtime authority scope.
These checks can consume additional model compute on
actual source changes, especially the initial backlog. Excessive,
unsupported, or uncertain evidence is rejected, never truncated. Ordinary
Nixpkgs package maintenance retains distribution trust; this is not a malware
scanner or a comprehensive CVE scan. The reviewer pin requires deliberate security
maintenance; routine user CLI updates and holds do not update that control-plane pin. Known-vulnerability evaluation remains
enabled. The source transport admits 896 KiB, but the existing complete
serialized review limit remains 1 MiB and observed compaction rejects verdicts.

A successful candidate is staged for next boot without restarting applications
or rebooting. Git imports it using an index lock and compare-and-swap, preserving
unrelated staged/unstaged edits. A changed HEAD or dirty affected file defers
updates. If the checkout changes during review, boot staging can succeed while
Git integration waits: the result explicitly records that state and retries
when safe. New committed user work must be deployed first; the updater does not
silently deploy it. Never automatically stash, reset, or resolve user conflicts.

`phoenix-switch` applies integrated pins sooner, followed by an application
restart. Some changes require reboot. Boot staging alone does not patch running
software. Normal builds still use the ordinary checkout. Keep supported-release
upgrades deliberate: following one stable branch forever does not extend its
support lifetime. Retain existing generations for rollback.

## Holds

JSON `_comments` is documentation, not executable policy. Keys normally name
simple top-level Nixpkgs attributes, e.g. `kando`; special adapters are
`firefox`, `codex-desktop`, and `codex-cli`. Use a real immutable pin, a reason,
and optionally the **first version allowed again**:

```json
"firefox": {
  "pin": "<reviewed 40-character Nixpkgs revision>",
  "reason": "Regression; upstream expects the fix in the stated version",
  "resumeAtVersion": "<actual numeric stable fix version>"
}
```

Ordinary Nixpkgs holds use the same revision format and may specify
`"source": "nixpkgs-unstable"` for resume observation; default is `nixpkgs`.
Firefox observes its configured source and always pins only Firefox, letting
other packages advance. Kando starts with its already-existing 2.3.0 compatibility
pin and no resume threshold: its adapter explicitly requires that version.

CLI `pin` is `{ "version": "<stable version>", "hash": "<matching sha256 SRI>" }`.
Community `pin` is `{ "native": "<source revision>", "sandbox": "<source revision>" }`;
set both corresponding `flake.lock` pins as part of a deliberate downgrade.
Evaluation rejects a mismatch, so a manual lock update cannot override a hold.
Use Nix's input override with `--output-lock-file flake.lock` to persist exact
selected revisions; do not hand-edit lock graph hashes.

Omit `resumeAtVersion` or set it to `null` for an indefinite hold. Never invent a
sentinel version. A verified stable version at or above the threshold permits
ordinary checks; unknown/prerelease versions stay held. Successful staging and
Git integration automatically remove satisfied entries in the update commit.
Failed review/build leaves current pins and holds unchanged. The threshold is an
expected fix, not proof of functional correctness; review indefinite holds when
upstream supplies a fix. Old held metadata may miss later vulnerability flags.

## Operation and validation

Inspect `systemctl status phoenix-updates.timer`,
`journalctl -u phoenix-updates.service`, and
`/var/lib/phoenix-updates/last-result.json`. Failures issue a fixed desktop
notification; credentials, profiles and CVE classifications are not collected.
Run `phoenix-update` as the desktop user for an immediate serialized check.
The service uses the existing protected controller socket and cannot
reboot or garbage-collect generations.

Fixtures in `tests/update-runner.py`, `tests/upstream-review.py`,
`tests/agent-deployment.py`, and `tests/agent-review.py` cover the full mocked
update/hold/commit workflow, dirty Git preservation, required publisher checks,
source-evidence rejection, and separate boot/runtime rollback. Full-host
build/review and an actual timer run are distinct deployment acceptance checks.
The earlier delayed-update prototype is preserved in commit `ed38a0b`; its unused
cooldown code is removed from the active tree and can be restored from Git.

## Why a small adapter

Stock `system.autoUpgrade` supplies scheduling and direct `nixos-rebuild`, but
its local-flake update/commit flags do not preserve this checkout's concurrent
edits, exact conditional package holds, or protected Phoenix source review.
Reuse systemd, Nix, Git's merge machinery and `nix-update`; custom code is limited
to source acceptance, holds and coordination. A custom security fast lane would
add advisory mapping and exception maintenance, so it is deliberately absent.
Revisit cooldowns if maintained feeds offer verified security bypass coverage.
