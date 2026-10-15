# Shared chats trial

The 2026-10-15 cold handoff is complete. This conversation was resumed in
Sandbox and then Native. Preserve shared history: **do not repeat
`codex-history-enable --apply` or restore the original Native databases.**
Sharing is temporarily active; the next-boot profile still has sharing off.
Reliable task execution remains under investigation. See [HANDOFF.md](HANDOFF.md).

## Next diagnostic trial

Wait for the coordinator's checked installation request. Keep Native open while
authenticating that OS dialog; no ChatGPT sign-in or history migration is needed.
When installation is complete and the coordinator asks for the trial:

- Open **ChatGPT Community (Sandboxed)** from the launcher and accept the normal
  close-and-switch offer. Let current work finish first.
- In Sandbox's permission selector beneath the composer, use **Custom
  (config.toml)**. This uses the existing worker configuration with OpenShell as
  the containment boundary; **Approve for me** requests incompatible nested
  Bubblewrap. No extra configuration file needs manual maintenance.
- Resume this conversation and try the requested harmless task. `pwd` succeeded
  in this mode during the 2026-10-15 trial; broader containment acceptance remains.
  Report exact failures; do not sign in again or repeat migration.
- Return to Native through its launcher if needed. Confirm **Approve for me**
  before subsequent Native commands because permission selections may be shared.
  Preserve shared history and report missing chats or changes to pins.

If starting `codex-desktop-sandboxed` in a terminal, it intentionally stays in the
foreground until the GUI exits. This waiting is not an unfinished deployment.

First-time setup on a different, uninitialized installation belongs in the
[technical cold handoff guide](history-layout.md#explicit-cold-handoff).
