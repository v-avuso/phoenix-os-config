# Shared chats trial

Sharing trial is **not active**. Copy this guide before quitting.

Open a terminal. Quit Native normally via tray/menu, close Sandbox and all Codex
CLI clients. Paste:

```sh
codex-history-enable &&
codex-history-enable --apply &&
ai-broker --task gui-sharing-trial \
  --reason 'Temporarily test shared chats and GUI switching' -- \
  phoenix-test --worktree /home/v/.codex/worktrees/gui-sharing-trial/phoenix-os-config &&
codex-desktop-sandboxed
```

Authenticate one OS dialog; no sign-in.

If it fails, stop. Reopen Native normally and report the terminal error. Do not
rerun apply or change history.

- Check existing/archived Native chats and pins.
- Resume this chat; send a reply.
- Open the other variant: test Keep/Close; confirm your reply remains. No extra login.
