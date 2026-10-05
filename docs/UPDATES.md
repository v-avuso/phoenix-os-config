# Automatic updates

## Policy and cost

- **Routine AI cost: zero.** Updates use Nix, Git and deterministic controller checks. They do not invoke Codex, scan every upstream source with an LLM, or require approval. Manual configuration changes use graphical Polkit authentication while AI review is suspended.
- **Distribution trust:** Stable NixOS and tested `nixos-unstable` channels supply package maintenance. Known-vulnerability evaluation remains enabled. This is neither a comprehensive CVE scanner nor a malware detector; no custom quarantine/security fast lane is maintained.
- **Fresh applications:** Firefox and everyday Codex CLI use unstable because they are deeply and frequently used. Community desktop follows checked stable publisher releases. Shared unstable also supplies compatible desktop dependencies; it can change more than these two applications. Explanations live in `config/updates.json` and package declarations.
- **Control plane:** The protected reviewer CLI has its own deliberate pin in `agent/reviewer-codex.nix`; everyday CLI updates do not change it. That separate pin still needs deliberate maintenance.
- **Release lifecycle:** Supported-release upgrades remain deliberate. Following the same stable branch indefinitely does not extend its support lifetime. Keep rollback generations.

## Scheduling and Git

- **Defaults:** `services.phoenixUpdates` uses `baselineHour = 21`, `intervalHours = 24`, `sourceBranch = "main"`, `cleanupBranches = true`. Hours are local time; the interval must divide 24. Six hours yields 03:00, 09:00, 15:00, 21:00. Persistent systemd scheduling catches up once after downtime; it does not wake the computer.
- **Isolation:** Prepare from the committed configured branch in a private timestamp-named `codex/updates/YYYYMMDD-HHMMSS` worktree. A different checked-out branch defers the run. Uncommitted unrelated edits are preserved; dirty updater-owned files, busy Git indexes and changed HEAD defer publication.
- **Source boundary:** Committed source must match the active or preceding staged approved source. The root controller accepts only permitted publisher/input lock changes and satisfied exception removals. New configuration, hooks, trust settings, patches, publishers and exception additions require authenticated manual deployment.
- **One commit:** Successful integration advances the target branch by one `chore(updates): update service - refresh supported package sources` commit, without a merge commit, history rewriting or force push. This marks routine maintenance rather than implementation of the service. Existing history is retained. Unchanged runs create no commit. Only `flake.lock` and satisfied removals in `config/updates.json` are updater-owned.
- **Cleanup:** Delete completed/discarded candidate branches; keep a pending integration candidate. Set `cleanupBranches = false` to preserve candidates for diagnosis. Historical prototype work remains in commit `ed38a0b`; unrelated branches are never deleted.
- **Dirty checkout:** Unrelated staged/unstaged edits are preserved and can coexist with an update. Local changes to `flake.lock` or `config/updates.json` defer a new run; changes to files the candidate modifies also block integration. The updater never commits your edits.
- **Main advances before staging:** Any new commit, including an unrelated one, invalidates the candidate's original HEAD; the run defers without integration. The next attempt uses the new committed branch only after it matches an activated or staged approved source. Deploy deliberate configuration changes with `phoenix-switch` or `phoenix-boot` first; automatic updates do not deploy arbitrary new user commits.
- **Main advances during building/staging:** Boot staging may succeed before the final Git check. Failed integration is explicitly `staged-pending-integration`; `pending.json` and its candidate branch remain. The next run integrates only if HEAD is still the original commit and affected local edits are resolved. If HEAD advanced, it defers until current committed work is manually deployed; that newer deployment supersedes the pending candidate and allows a fresh update.
- **Conflict handling:** No automatic rebase, merge-conflict resolution, stash, reset or AI invocation. Git index locking, two-tree checkout and compare-and-swap protect concurrent work. Temporary contention retries later; changed committed configuration needs the deliberate deployment above. Thus conflict handling is safe, but not entirely hands-off in every race.
- **Branch limits:** Existing development branches do not inherit updated main automatically. Merge/rebase before building them. `phoenix-switch` from the updated branch activates its pins and replaces the next-boot profile; `test` does not replace that profile. Restart applications to use new binaries; some changes need reboot. Boot staging alone does not patch running software.

## Central exceptions

- **Location:** `config/updates.json` groups `holds` and `patches`; JSON `_comments` explain usage. Temporary bug-fix patch files belong in `config/update-patches/`. Feature patches belong beside their application module.
- **Identifiers:** Simple top-level Nixpkgs attributes, e.g. `kando`; `codex-cli` maps to `codex`. Firefox/Codex CLI observe `packageSources`; other entries observe stable `nixpkgs`; ordinary entries cannot expire against an unrelated unstable version. Community desktop has its separate two-input hold adapter; arbitrary desktop patch recipes are not supported.
- **Holds:** `pin` is a full immutable Nixpkgs revision, `reason` explains the regression, `resumeAtVersion` is the first acceptable stable numeric version. Null/omitted means indefinite; never invent a future version. A hold pins the named package, not the entire channel. Kando retains its existing 2.3.0 adapter requirement.

```json
"holds": {
  "firefox": {
    "pin": "<reviewed 40-character Nixpkgs revision>",
    "reason": "Regression; upstream expects the fix in version 150.0",
    "resumeAtVersion": "150.0"
  }
}
```

- **Temporary fixes:** Append patches to the upstream derivation; keep existing patches and packaging. Reusable archive extraction defaults are inappropriate across unrelated packages. Use an exceptional custom recipe only when upstream packaging cannot express the workaround.

```json
"patches": {
  "thunar": {
    "reason": "Temporary bug fix pending upstream release",
    "patchFiles": ["config/update-patches/thunar-fix.patch"],
    "removeAtVersion": null,
    "source": "nixpkgs"
  }
}
```

- **Expiry:** The updater removes entries only when a verified numeric upstream version meets the threshold and the candidate passes checks/build/staging. Unknown/prerelease versions retain exceptions. A patch stays while its package has an unreleased hold. Patch files may remain for provenance after removal; the updater does not delete source files.
- **Limits:** A version threshold records an expected fix, not proof that the bug is fixed. Review indefinite entries when upstream resolves them. Old held revisions may lack later vulnerability flags.
- **Desktop holds:** `pin = { "native": "<revision>", "sandbox": "<revision>" }`; deliberately update both corresponding lock pins when adding a downgrade. Evaluation rejects mismatches. Do not hand-edit NAR hashes; use Nix input overrides with `--output-lock-file flake.lock`.

## Operations and implementation

- **Reviewer suspension:** AI deployment review is disabled by explicit user decision: full tracked-source/upstream batches were too broad for the compute budget, and repeated invocation failures provided no actionable diagnosis. Manual deployment now requires graphical Polkit authentication; routine updates retain deterministic controller checks. Reviewer code and saved authentication are retained.
- **Inspect:** `systemctl status phoenix-updates.timer`, `journalctl -u phoenix-updates.service`, `/var/lib/phoenix-updates/last-result.json`. `phoenix-update` runs an immediate serialized check. Failures emit a fixed desktop notification; no credentials or private profiles are collected.
- **Checks:** Exact-head Community publisher CI and stable payload validation; known-vulnerability Nix evaluation; unprivileged build; immutable source/closure binding; root baseline/profile rechecks. Missing Community checks retain that group while channel updates can proceed. Unchanged failed candidates back off for a day.
- **Permissions:** The automatic action stages next boot only; it cannot supply a command, closure or verdict, reboot, or garbage-collect. Manual configuration changes require graphical operator authentication. Git commands use sanitized metadata to prevent inherited hooks and filters.
- **Upstream comparison:** Stock `system.autoUpgrade` supplies scheduling and direct rebuild/update/commit flags. Its systemd unit can be extended without patching upstream, but a pre-hook alone cannot coordinate isolated preparation, conditional exceptions, protected deployment and safe checkout publication. The small adapter reuses systemd, Nix lock/build operations and Git integration; it does not implement an advisory framework.
- **Validation:** Focused updater/controller fixtures cover dirty Git, source/publisher rejection, exception expiry, boot-only activation and no reviewer invocation. Full-host evaluation/build and a real service run are separate checks; mocks alone do not establish deployment success.

## Activation recovery

- **ClamAV:** Signature downloads are timer-driven (two minutes after boot and hourly, with missed calendar checks caught up). They are not a required activation job. Existing databases/scanners remain usable while offline; first-install recovery starts scanning after a successful download.
- **Retries:** FreshClam failures retry after five minutes, capped at three starts within thirty minutes; the hourly timer permits later recovery. Keep failures visible rather than marking network errors successful. No AI or database deletion is involved.
- **Controller refresh:** Changed deployment units reload gracefully after their active request/response, then systemd starts installed code/settings. This avoids killing the controller during its own deployment. Older controllers require one authenticated restart when adopting this mechanism; thereafter no manual restart is expected.
- **Switch result:** A failed auxiliary service can make the command return nonzero even after configuration/profile activation. Inspect the running system, next-boot profile and failed unit before assuming rollback or repeating the whole switch.
