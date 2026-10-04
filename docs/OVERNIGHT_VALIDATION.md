# Overnight validation

The overnight session permitted builds/static fixtures only. The later daytime
follow-up permits task-related activation, but reboot acceptance stays deferred.
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
- Hardening (`cc98afe`): GUI RPC frames are bounded to 16 MiB in both directions;
  oversized or expanded frames close with a generic diagnostic. Temporary
  subprocess/socket fixtures verify bounds, cleanup, backpressure and spaced
  requests on a shared socket. The user's subsequent switch installed this source;
  normal GUI task/reopen acceptance after that switch is still outstanding.
- After reviewed activation, run a normal GUI task, close/reopen and confirm
  saved task/login survive without profile errors. Oversized legitimate results
  need a reviewed remedy; do not reauthenticate to fix a frame-limit error.
- Optional: type `chat` in the launcher; expect Sandboxed before Native.
- Queued changes have reached the protected controller's 512 KiB whole-source
  bound. They still evaluate/build, but reviewed activation now needs a deliberate
  bounded-review design/capacity update; neither the client nor root controller
  limit was relaxed overnight. Do not bypass this by omitting tracked files.
- The user's switch changed the installed baseline to source
  `/nix/store/3if0zg7byd9vnzsm72lzz95fzv8f7d4b-source`; the earlier small-update
  route based on `ed913e5` is obsolete. Do not treat historical headroom as current.
- The protected reviewer's non-secret metadata now confirms Sol 6.1 at 272,000
  tokens / 95% effective context. The new declaration admits 768 KiB source and
  independently bounds complete instruction plus schema at 1 MiB, rejecting
  observed pinned-CLI compaction before accepting a verdict. All 27 guard fixtures
  pass; fresh protected review and persistent installation now pass without Polkit.
  Existing reviewer login is retained; no new OAuth sign-in is required.
- Conditional shared history support is prepared using upstream SQLite/session/
  writer locations, without a custom importer. Enable only after a coordinated
  exit of all writers; browser profiles and refresh ownership stay separate.
  Real shared listing/resume/archive/writer exclusion remain pending; retained
  sandbox histories are not silently merged. See the long-term sandbox guide.

## Daytime feedback and refinement

- Main now includes the feature branch without rewriting history. Separate commits
  cover Kando release gestures, Thunar submenus/quick ZIP, Psysonic output recovery,
  idle integration/`blank`, Native scaling and review-capacity guards.
- User confirmed Navidrome/Psysonic playback before selecting an unusable output,
  most session restoration, initial Thunar integration and wallpaper/light theme.
  Wallpaper is accepted for this iteration. Other feedback is partial acceptance.
- Psysonic's saved output alone was reset to system default with a key-only backup;
  a bounded launch then stayed open. The initial exit cause is not established as
  OOM. The patched package builds; audible playback still needs acceptance.
- Subsequent live follow-up confirmed the patched app was installed and stable.
  Remaining silence was its PipeWire stream gain at 0%, while internal gain was
  100% and the default speaker remained 30%. Restored only that verified stream
  to 100%; recreating it retained the gain through WirePlumber. App stays open,
  paused; the user subsequently confirmed audible playback. No reboot is needed.
- Idle integration used unsupported callback names; corrected to the exact schema.
  `idle` is Python IDLE, so the new command is `blank` (`blank off` restores).
  Source/API/state fixtures pass. A live check found the installed wrapper lacks
  its patched idle IPC target; package integration is being corrected before
  shell reload and actual blank/wake acceptance.
- Kando now uses portal release for held gestures, valid key names, swapped mouse
  bindings, no pointer warp, and upward F11 in Firefox/both ChatGPT variants.
  Patched package/gesture lifecycle fixtures pass; physical input testing is pending.
- For execution while the button remains held, enable maintained hover mode with
  a fixed 150px stroke beyond the 50px center dead zone: 200px total, no pause or
  additional click. Kando's own warp was already disabled; Hyprland's global
  `cursor.no_warps` prevents compositor focus/workspace warps. No per-window guard
  exists in the pinned implementation. The Foot store path is regenerated with
  package changes and reasserted with the menu baseline, not a manual hash.
- Thunar groups image conversions and adds Archive → Create ZIP, retaining the
  broader archive plugin. Safety/packaging fixtures pass; inspect live menus after
  activation. Native scaling now uses upstream Wayland detection on direct launch,
  including session restore; verify font size after reopen, then later after reboot.
- Protected persistent switch installed the held-gesture changes without Polkit;
  Kando alone was restarted. Live hover mode, distance and compositor no-warp
  settings match. Physical gesture/playback checks remain pending. No reboot or
  live display blanking occurred. Private notes remain read-only; this guide
  tracks their acceptance.

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
| Idle shader | Implemented; full metal build and all-host evaluation pass; monitor tests deferred |
| Session restore | Conservative hypr-persist prototype implemented; tests/full build pass; reboot acceptance deferred |
| Kando | Implemented; exact upstream schema and fake-input checks pass; build/GUI acceptance recorded below |
| Dynamic wallpaper/theme | Implemented; adapter checks and upstream package build pass; combined/manual acceptance below |
| Thunar integration | Implemented; exact GTK/image fixtures pass; combined build and live acceptance below |

## Idle display — feat(display): blank idle monitors without DPMS

- Caelestia blanks after 300 seconds using an opaque black compositor shader,
  hiding the cursor without locking or changing DPMS. Wake restores the previous
  shader while it is still owned, and restores cursor visibility independently.
- Pinned Hyprland 0.56.2 recreates Lua/config state on reload; fixtures cover
  this reset, helper re-execution, competing shaders and partial apply recovery.
  Lua fixtures, all-host evaluation and full metal build pass; built system:
  `/nix/store/l0md58kxk21sjzyg9pwk21699n9lwqgy-nixos-system-phoenix-26.05.20260924.c508844`.
- Tomorrow after reviewed activation: idle all three monitors, wake with mouse
  and keyboard, verify cursor return and existing inhibition/night-light
  behavior. Reload the config while blanked; it should clear blanking. No live
  shader, DPMS, lock or monitor action was performed overnight.

## Session restore — feat(desktop): restore Hyprland sessions

- Pin hypr-persist 0.1.2, save every 120 seconds, and use private
  `~/.local/state/phoenix-hypr-persist/sessions/last.toml`. Native SIGTERM saves
  before Caelestia's normal logout closes clients. No foreign snapshots are
  imported; remembered commands are executable user state, never broker authority.
- Simple restore adopts existing windows or launches missing apps. Layout-tree
  reconstruction is disabled because upstream's layout path can close splash
  windows. Exact Codex class overrides retain their respective installed Native
  and Sandboxed launchers across deployment changes.
- All-host evaluation, 264 upstream/added tests and full metal build pass:
  `/nix/store/3yni5c7qbaw5467mfd1q8pxwlv35jv68-nixos-system-phoenix-26.05.20260924.c508844`.
  Tomorrow after reviewed
  activation: multiple Firefox windows, terminals, Thunar and Electron; different
  workspaces/monitors plus floating windows; logout/login then reboot. Expect
  useful app/workspace restoration without duplicate windows or closing live apps.
- Prototype limits: adopted geometry and monitor/layout fidelity are limited;
  temporary legacy Hyprland rules are unsupported, though explicit placement is
  Lua-compatible. Verify partially closed shutdown snapshots and stopping during
  initial restore. Do not repeatedly launch apps to mask a lifecycle failure.

## Kando — feat(kando): add contextual radial menus

- Pin the packaged 2.3 integration: a controlled writable config root, one
  session service, native Wayland, two portal shortcut IDs and minimal global,
  Firefox, Codex and fallback menus. Two JSON baselines reset at service start;
  private profile/cache state is not reconciled. Menu-launched apps use normal
  config and separate user units so a Kando restart should leave them running.
- The physical Razer's two side buttons use a separate non-root libevdev filter:
  immediate presses, 180 ms stable-release debounce, cloned capabilities and
  unchanged high-resolution wheel events. A closed device policy grants only
  the fixed mouse and uinput nodes; no human account gains input-group access.
- Exact upstream schema/context-selection, packaging and fake input/lifecycle
  fixtures, all-host evaluation and full metal build pass:
  `/nix/store/4dwvx6wyhxv55n32cyv4jabvd8036vw0-nixos-system-phoenix-26.05.20260924.c508844`.
  No real input device was opened or grabbed, and no app/service was started.
- Tomorrow after reviewed activation: approve/register global shortcuts if the
  portal asks; verify side-button global/context menus, native Wayland, focus
  return, quick/held gestures, Firefox/Codex/fallback selection, wheel/pointer
  behavior and mouse disconnect/reconnect. Restart Kando deliberately: declared
  menus/settings must return and menu-launched apps must retain their profiles
  and remain open. Confirm the service actually uses the controlled config root.

## Wallpaper/theme — feat(desktop): add time-aware wallpaper and theme

- Use upstream Timewall 2.1.0 at `19897aee9fee4f4ebd5cbd37b0fc4e3271cb6480`.
  The external HEIC remains a runtime string, outside Git/Nix store; no asset
  rename/read occurs during evaluation or building. Configured schedule uses its
  eight encoded frames: 1@00:00, 2@04:00, 3@06:00, 4@09:00, 0@12:00,
  5@16:00, 6@19:00, 7@22:00 (appearance metadata also identifies light 0/dark 6).
- `phoenix-timewall.service` selects the current frame immediately, then checks
  every 600 seconds. `phoenix-timewall-theme.service` reconciles at session start;
  `phoenix-timewall-theme-light/dark.timer` run at 07:00/20:00 local time.
  `--no-smart` prevents frames from changing the separate light/dark policy.
  The palette name is preserved; a dark-only palette can reject light mode.
- Fixed Caelestia writes share a private lock. Upstream state files are watched
  by the shell, so no readiness polling or sleeps are added. A private systemd
  RuntimeDirectory prevents a crashed daemon's saved setter PID crossing runs.
  Missing/unreadable/invalid assets or daemon failure select generated black;
  after fallback, fix the cause and restart this service deliberately.
  Timewall's asynchronous setter cannot report backend exit status; the adapter
  logs failures and attempts black, but cannot guarantee a broken backend works.
- Ten isolated adapter fixtures, actual-package/config checks, all-host
  evaluation and full metal build pass:
  `/nix/store/fam9wmasppvcfcvzn6q7v3b1i6spw3xq-nixos-system-phoenix-26.05.20260924.c508844`.
  Tomorrow after reviewed activation: inspect service/timers and journal,
  current frame/mode and successive frames; verify ordinary manual Caelestia
  commands. Test missing-file fallback only with guaranteed file restoration,
  then restart the service and confirm the dynamic image returns. No live setter,
  theme change, asset rename or service action was performed overnight.

## Thunar — fix(files): complete Thunar integration

- Caelestia now chooses the matching light/dark GTK theme and generates opaque
  palette-aware selection backgrounds. Thunar's scoped CSS monitor reloads valid
  generated updates without another theme owner; invalid/missing CSS keeps the
  last good provider. Source defects are verified, but the original live light
  symptom still needs acceptance. Removing rules can require one restart because
  GTK's original user provider stays loaded; the config directory must exist.
- Use supported Thunar/xfconf, GVfs, Tumbler, archive/volume/media-tags plugins.
  Engrampa is a shipped archive-plugin backend; Xarchiver has no shipped adapter.
  This avoids a custom archive integration or full Xfce/KDE session. Middle-click
  opens tabs, Ctrl+M toggles the initially hidden menu bar, and Thunar is the
  directory MIME default. Persistent bookmarks/history/session state stay intact.
- Four image actions produce JPEG/PNG/WebP/JXL copies beside their originals.
  Existing files are never replaced; repeated/same-format inputs are skipped.
  Conversion uses the existing ImageMagick dependency and stdin filenames, with
  first-frame output, white JPEG transparency and lossless JXL defaults.
- Exact patched GTK lifecycle/selection tests and mocked/real generated-image
  tests pass, including light→dark→light, atomic imported-CSS updates, malformed
  files, literal bracket/colon filenames, batch collisions and JXL pixel equality.
  Metal/VM packaging assertions and the full combined metal build pass:
  `/nix/store/dj708v9552l56byycd7fq0xjbhcc0vmv-nixos-system-phoenix-26.05.20260924.c508844`.
  The built wrapper includes the three plugins; `engrampa.desktop` and ZIP tools
  exist. Net system closure growth versus the previous Timewall build is about
  70 MiB, including small Caja/MATE libraries but no full desktop/session.
- After reviewed activation: test both theme directions, icon/list single and
  Ctrl multi-selection in focused/unfocused windows; tabs/middle-click/Ctrl+M;
  thumbnails and trash; removable/internal drives and Windows volumes when
  present (unlock only with authorization). Create/extract multi-file ZIP;
  convert temporary image selections in all four formats and verify originals;
  inspect audio Properties metadata. No live mount/UI/service action was taken.
