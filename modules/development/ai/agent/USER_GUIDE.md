# Shared chats

The 2026-10-15 cold handoff and primary GUI workflow are accepted: this same
conversation resumed in Sandbox, **Custom (config.toml)** was preselected, and
`pwd` returned `/home/v/repos/code/phoenix-os-config`. The operator then returned
to Native with workspace-write/auto_review.

Preserve shared history: **do not repeat `codex-history-enable --apply` or restore
the original Native databases.** Sharing is currently active in the temporary
installation; repository and next-boot defaults still have sharing off. Permanent
promotion needs explicit approval. See [HANDOFF.md](HANDOFF.md).

## Normal use of the accepted temporary installation

- Open **ChatGPT Community (Sandboxed)** and use the normal Keep current or
  Close and switch offer. Let active work finish before switching.
- Ordinary Sandbox chats default to **Custom (config.toml)**. This uses the worker
  configuration and OpenShell boundary; no extra configuration file needs manual
  maintenance. **Approve for me** requests incompatible nested Bubblewrap.
  Deliberate Sandbox selections and restrictive profiles remain distinct; report
  unexpected permissions before running commands.
- Continue the existing shared chat. Native and Sandbox retain separate browser
  profiles and permission preferences; no additional sign-in or migration is needed.
- Open Native through its launcher when needed. Its accepted return mode is
  **Approve for me** with workspace-write/auto_review. Report missing chats,
  unexpected permissions or changed pins without restoring stale databases.

If starting `codex-desktop-sandboxed` in a terminal, it intentionally stays in the
foreground until the GUI exits. This waiting is not an unfinished deployment.

Broader archive/pin/window observations and disabled experimental broker controls
are separate from the accepted shared-chat workflow. First-time setup on another,
uninitialized installation belongs in the
[technical cold handoff guide](history-layout.md#explicit-cold-handoff).
