# Shared chats

The 2026-10-15 cold handoff and primary GUI workflow are accepted: this same
conversation resumed in Sandbox, **Custom (config.toml)** was preselected, and
`pwd` returned `/home/v/repos/code/phoenix-os-config`. The operator then returned
to Native with workspace-write/auto_review.

Preserve shared history: **do not repeat `codex-history-enable --apply` or restore
the original Native databases.** The accepted sharing configuration is now installed
persistently: the running system and next-boot profile both retain it. No new
sign-in or migration is required. See [HANDOFF.md](HANDOFF.md).

## Normal use

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

## Existing managed worktrees

Sandbox CLI work can use registered worktrees under the operator's managed root
(`/home/v/.codex/worktrees` here); use its absolute path inside the container. Only
that subtree joins the default project mounts. An explicit operator workspace
list replaces those defaults. For an authorized temporary deployment, agents use:

```sh
phoenix-authorize --task TASK --reason "Concrete nonsecret purpose" -- phoenix-test --worktree /absolute/registered/worktree
```

This freezes Git-visible dirty content and uses independent host review before
real temporary activation. The current-UID contained workflow is accepted;
`test` leaves the boot profile unchanged. Keep Native available and do not repeat
history migration or sign-in. See [acceptance evidence](HANDOFF.md#contained-managed-worktree-deployment-acceptance).

Broader archive/pin/window observations and disabled experimental broker controls
are separate from the accepted shared-chat workflow. First-time setup on another,
uninitialized installation belongs in the
[technical cold handoff guide](history-layout.md#explicit-cold-handoff).
