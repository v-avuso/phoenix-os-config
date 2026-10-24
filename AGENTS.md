# NixOS repository guidance

## Repository map and ownership

- Nix files describe current configuration; README provides orientation and
  docs/VISION.md describes future direction. Preserve cooling, authentication,
  and recovery constraints documented in operational guides.
- Keep reusable component sources separate from NixOS/Home Manager wiring;
  deployment should reference those sources rather than maintain copies.
  Multi-file Nix modules use a named directory with `default.nix`, enabled by an
  import and minimal configuration; single-file modules may remain flat.
  See [module boundaries](docs/ARCHITECTURE.md) for repository layout.
- Keep agent policy and adapters under `modules/development/ai/agent`.
- For media pipeline work, explicitly read `modules/apps/media/AGENTS.md`;
  root-started sessions must not assume subtree guidance was loaded.
- For Typst publishing work, read [Typst guidance](modules/apps/documents/typst/AGENTS.md)
  and its linked component guidance before editing designs or adapters.
- Follow docs/CONFIGURATION_STATE.md for application ownership.
  Registered Caelestia/VSCodium experiments survive boot; explicit switch/test
  reasserts baselines. Promote reviewed settings to Nix beforehand.
- Keep fan-policy reconciliation specialized and preserve hardware safety.
- Update current operation in README/recovery/state guides and future direction
  in VISION; component READMEs/design docs own local architecture and rationale.
- Agents may run inside OpenShell; use named broker diagnostics for
  containment issues.

## Configuration review and sources

- Review changes against the last activated source and resulting closure,
  including relevant scripts, locked inputs, activation hooks, root services,
  authentication, cooling, and recovery. Use the installed review boundary.
- For changed locked dependencies supplying modules or containment code,
  inspect the exact upstream implementation/diff and provide bounded source
  evidence.
- Do not silently update flake.lock.
- When inspecting an offline NixOS root, resolve absolute `/etc` and Nix-store
  symlinks within that root; host traversal can read the running installation
  instead of the target being inspected. Cold Btrfs migration mounts use
  `ro,rescue=nologreplay`; test emitted options and native mount validation
  together so spelling changes preserve the no-write boundary.
  Cold SQLite WAL checks use disposable writable DB/WAL copies: `mode=ro` can
  still require SHM creation. Retain the underlying error; do not infer missing
  or corrupt state from a read-only access failure.
- Before closing a storage migration, exercise reviewed deployment as well as
  human switching. Complete home omits service-owned reviewer login under
  `/var/lib/phoenix-deploy-review`; restore it selectively through the installed
  importer. Keep login continuity separate from root approval authority: old
  checkpoints require matching target/policy/closure, never blanket adoption.
- Hardware identity checks must compare native fields with only documented
  padding removed; `lsblk --raw` can hex-escape NVMe serial padding. Exercise
  native/fallback representations rather than only mocked, trimmed output.
- Git flakes omit untracked files: the coordinator stages only owned new
  files before combined checks.
- Never use `path:.` on this checkout: it copies ignored private task notes
  into the Nix store. Standalone fixtures must also use a Git-flake source
  or a vetted disposable source tree.
- When moving packaged sources or links, preserve public package identifiers and
  deployment contracts unless migration is in scope. Verify referenced files and
  relative link chains in Git-flake Nix-store sources and affected Home Manager
  outputs, including isolated subtree copies when packaging selects a subtree.

## Commands and validation

- User PATH provides `phoenix-target --info`, `phoenix-dry-build`,
  `phoenix-build`, `phoenix-gc`, `phoenix-test`, `phoenix-switch`, and `phoenix-boot`.
  `phoenix-rebuild --print <action>` previews the dispatcher command.
- `config/user.nix` owns `repoDirectory`; `PHOENIX_REPO_ROOT` overrides the
  checkout. Root UUID selects `metal|metal-4tb`; `PHOENIX_TARGET` can confirm
  that selection (or `vm`) but a mismatch fails closed.
- Evaluate metal with:
  `nix eval --no-write-lock-file .#nixosConfigurations.metal.config.system.build.toplevel.drvPath`
  Use the corresponding `vm` output when relevant.
- Check flake evaluation with:
  `nix flake check --no-build --no-write-lock-file .`
- For mutable settings, command, desktop, or security changes, run the
  appropriate focused fixtures from tests/README.md.
- Run fast fixtures first; use disposable nixpkgs `runNixOSTest` VMs for real systemd,
  root UID, socket, activation and rollback semantics; see [VM fixtures](modules/development/ai/agent/tests/activation-runtime.nix)
  and [acceptance limits](modules/development/ai/agent/security-review.md). Prefer isolated trials to disruptive host experiments;
  VM passes do not establish host desktop, biometric or reboot acceptance.
- Metal hardware configuration is tracked. VM hardware is a tracked
  placeholder; VM deployment requires a real reviewed snapshot.
  Evaluation does not establish bootability.

## Activation and privilege

- `phoenix-dry-build` evaluates a build plan; `phoenix-build` builds without
  activation. `test` activates now; `switch` activates and updates next boot;
  `boot` updates next boot.
- Task-related activation is authorized within the requested scope unless
  the task explicitly requests a pause, without reminders to save mutable
  desktop settings. This does not authorize unrelated privileged actions.
  Never activate merely to validate an edit.
- Before privileged broker operations, explicitly read
  `modules/development/ai/agent/AGENTS.md` and the
  [authorization usage](modules/development/ai/agent/authorization/README.md);
  root-started chats do not automatically load subtree guidance.
- Agents deploy through `ai-broker --task TASK --reason PURPOSE -- phoenix-test
  --worktree /absolute/selected-worktree`; use `phoenix-switch` in that mapping
  for authorized persistent deployment. Build/evaluate as the user first. The
  installed controller freezes source, reviews and binds activation; switch owns
  the system-profile update, while test leaves the boot profile unchanged.
- Human `phoenix-test`/`phoenix-switch`/`phoenix-boot` retain terminal
  `nixos-rebuild --sudo` authentication and progress. The pinned rebuild hardcodes
  sudo; `NIX_SUDO=pkexec` is unsupported, not an agent deployment workaround.
- For authorized operations not yet broker-mapped, use a supported native human
  Polkit flow with a concrete immutable helper and reviewed arguments. A rejected
  or unavailable review requires its explicit human fallback; never bypass that
  boundary with direct `pkexec`, sudo or a manual profile update.
