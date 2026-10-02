# Configuration and state

Nix/Home Manager is the source of truth for lasting configuration. Application
files may also contain private data or live experiments; identify ownership
before writing or reconciling them.

## Three ownership models

| Model | Behavior | Examples |
| --- | --- | --- |
| Declarative configuration | Store-backed files or managed keys; edits belong in Nix | Shell logic, static Hyprland files, security policies |
| Writable baseline | Ordinary writable settings file initialized from Nix; explicit activation reasserts its baseline | Caelestia `shell.json`, VSCodium settings/keybindings |
| Persistent application/user state | App owns it; restore separately and leave it out of reconciliation | Browser databases, credentials, documents, sessions |

CoolerControl uses a specialized, hardware-aware reconciler for Phoenix-owned
fan profiles. Its safety boundary and firmware fallback take precedence over
convenient settings experiments; preserve unrelated daemon state. Do not
replace this mechanism with generic file copying.

## Writable baseline lifecycle

Caelestia's isolated `shell.json` on metal and VSCodium's `User/settings.json`
and `User/keybindings.json` use the same narrow JSON writer. The shared
NixOS/Home Manager integration applies this lifecycle to enabled baselines on
both hosts:

- A fresh home gets a writable file from the declared baseline; a legacy managed
  symlink can be migrated to an ordinary file.
- Live UI edits are allowed. Existing experiments survive logout and reboot.
- Explicit NixOS `switch`/`test` activation reasserts the baseline, even when
  reactivating the same generation. Direct Home Manager activation also
  reasserts it. `build`/`dry-build` do not change the file; `boot` does not
  reassert an existing runtime file on the next boot.
- To retain an experiment, inspect the runtime settings against the baseline,
  review meaningful changed keys, and update the Nix declaration **before**
  activating. Reassertion deliberately discards unpromoted changes.

These rules cover registered settings files, not every mutable file. Static
Hyprland configuration remains store-backed. VSCodium has its own Home Manager
registration with writable settings/keybindings under its native `VSCodium`
configuration directory, while extensions remain immutable and workspace/app
state remains app-owned. Firefox needs a carefully selected preference
allowlist before any such change.

## Protected state and extension rules

Never blanket-overwrite Firefox or Codex profiles, cookies, history, bookmarks,
logins, certificates, extension storage, application databases, credentials,
KeePass databases/keys/pairings, Obsidian vaults, workspace/repository lists,
session state, documents, or caches as configuration.

Adopt another writable baseline only when interactive edits are useful and the
settings file or selected keys can be separated from user state. Define which
activation reasserts it, initialization and symlink migration, permissions,
reload behavior, rollback limits, and semantic change review. Keep sensitive
policy settings declarative. Reuse the existing narrow JSON writer when those
same file-level semantics apply; avoid a blanket profile framework or sweeping
application state into the baseline registry.
