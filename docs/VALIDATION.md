# Validation

## Before activation

Evaluate both host outputs, build changed packages/services, and run the focused
[Test instructions](../tests/README.md) before committing. These checks do not
prove desktop, hardware, or authentication behavior. VM hardware is still a
placeholder: runtime VM verification is deferred until a real snapshot exists.

An authorized `test`/`switch` resets unpromoted Caelestia and VSCodium settings
to Nix baselines. Review and promote experiments worth keeping **before** it.
Keep a known-good boot generation and TTY recovery available.
The agent handles authorized activation through graphical Polkit authentication.
`test` changes only the running system; `switch` also selects the next-boot
generation. If starting with `test`, complete basic current-session checks before
authorizing `switch`. Reboot after `test` alone returns to the previous boot
generation. Perform the acceptance pass below after a persistent `switch`.

## One combined acceptance pass

After authorized activation, the agent can check service status/journals,
settings file ownership, UPower/power-profile services,
ClamAV database/daemon/scanner readiness, firewall
settings, OpenSnitch observation, and single GeoClue-agent ownership through
CLI. No need to open application UIs for those checks.

User checks:

1. **Settings:** change a harmless Caelestia setting and VSCodium
   setting/keybinding in their UIs; verify saving works. Confirm editor
   history/workspace state remains intact. Inspect only settings diffs.
2. **Reboot and desktop:** reboot, then confirm SDDM offers Hyprland without
   Plasma on metal. The old login-manager process may retain old choices until
   reboot. Log in, confirm experiments persisted, and check monitors, Qt apps,
   network, audio, and location/night-light behavior. VM retains Plasma/X11.
3. **Session:** graceful logout returns to SDDM; log in again and confirm
   experiments persist. KeePassXC should not autostart.
   Check graphical authentication and lock/unlock with password fallback and
   the enrolled key.
4. **Baseline reset when ready:** ask the agent to reassert the baseline through
   authorized activation and confirm both apps regain declared settings.
   Caelestia should reload without killing the session; VSCodium should observe
   the change without losing history/globalStorage/workspace state.

Retain [fan safety checks](FAN_CONTROL.md) for cooling verification; don't
manufacture a cooling failure or remove live antivirus databases. Offline-first
ClamAV recovery is covered by isolated graph/fixture checks; a full runtime
scenario remains deferred to a disposable VM. OpenSnitch remains quiet outbound
observation, not an enforced outbound allowlist. Record failures before further
changes; system rollback does not restore private data.
