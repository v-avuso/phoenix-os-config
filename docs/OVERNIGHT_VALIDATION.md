# Overnight validation

This session permits builds/static fixtures only. No activation, service restart,
GUI interaction, logout/reboot or hardware mutation is authorized overnight.
Task specifications remain in the private `.codex/work-queue.md`.

## Notes/status permission blocker

Automatic approval review rejected the requested writes to
`.codex/work-queue.md` and `.codex/next-day-validation.md`: this workspace makes
`.codex` read-only for the assistant. This guide mirrors status and actionable
notes without changing those protected files. Grant write access to those two
specific files tomorrow to restore the requested private-note workflow; broader
profile/authentication access is unnecessary.

## Agent sandbox

- Installed first iteration: approved source `ed913e5`, acceptance report
  `c7777c3`. GUI task, close/reopen and reviewed persistent switch passed before
  the unattended session. No new sign-in is needed.
- New hardening (`cc98afe`): GUI RPC frames are bounded to 16 MiB in both directions;
  oversized or expanded frames close with a generic diagnostic. Temporary
  subprocess/socket fixtures verify bounds, cleanup, backpressure and spaced
  requests on a shared socket. This is not yet activated.
- After reviewed activation, run a normal GUI task, close/reopen and confirm
  saved task/login survive without profile errors. Oversized legitimate results
  need a reviewed remedy; do not reauthenticate to fix a frame-limit error.
- Optional: type `chat` in the launcher; expect Sandboxed before Native.

## Music namespace — feat(music): add Psysonic and Navidrome

- Follow-up fix changes only `modules/services/music.nix`: read-only
  `/home/v/sync/music` → `/var/lib/navidrome/music`, with supported
  `ND_MUSICFOLDER` selecting the internal path. No duplicate mount destination;
  upstream CA/store/etc mounts, RootDirectory and ProtectHome remain intact.
- ACLs remain: source files/directories still need Navidrome group read/traverse
  after binding. `/home/v` remains 0700; no broad group or write grant was added.
- Full metal build `/nix/store/2kk870fyaxcc26n5597lclxcfy70r7i8-nixos-system-phoenix-26.05.20260924.c508844`
  succeeds; metal/VM/default evaluation and generated-unit checks pass.
- Tomorrow: reviewed activation, inspect live mount namespace and read-only
  mount flag; verify representative MP3/Opus reads as the service user. Run the
  supported scan and confirm nonzero tracks/albums, then check Psysonic.
  No live scan/count/client acceptance is claimed tonight.
- Newer unrelated commits prevent safely amending original music commit
  `3d17787`; the follow-up preserves that history.

## Queue status

| Task | Status |
| --- | --- |
| Music namespace | Implemented; full metal build and all-host evaluation pass; runtime pending |
| Idle shader | Read-only plan complete; implementation next; monitor tests deferred |
| Session restore | Unsafe hyprsession startup rejected; maintained alternative under review |
| Kando | Exact 2.3 schema/shortcuts/debounce plan investigated; implementation pending |
| Dynamic wallpaper/theme | Pending |
| Thunar integration | Pending |
