# NixOS repository guidance

## Repository map and ownership

- Nix files describe current configuration; README provides orientation and
  docs/VISION.md describes future direction. Preserve cooling, authentication,
  and recovery constraints documented in operational guides.
- Keep modules reasonably self-contained: colocate their implementation,
  documentation, tests, fixtures and engineering guidance. Reserve root-level
  `docs/` and `tests/` for repository-wide and genuinely cross-module concerns;
  root README may briefly describe and link to modules.
- Prefer reusable modules enabled by an import and minimal configuration. Keep
  one or two related files flat; normally group three or more (including tests)
  in a named feature directory with concise filenames. Cohesive modules may keep
  tests at module level; avoid disproportionate abstraction. See docs/ARCHITECTURE.md.
- Keep agent policy and adapters under `modules/development/ai/agent`.
- For media pipeline work, explicitly read `modules/apps/media/AGENTS.md`;
  root-started sessions must not assume subtree guidance was loaded.
- Follow docs/CONFIGURATION_STATE.md for application ownership.
  Registered Caelestia/VSCodium experiments survive boot; explicit switch/test
  reasserts baselines. Promote reviewed settings to Nix beforehand.
- Keep fan-policy reconciliation specialized and preserve hardware safety.
- Update current behavior in README/recovery/state guides and future direction
  in VISION.
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
- Git flakes omit untracked files: the coordinator stages only owned new
  files before combined checks.
- Never use `path:.` on this checkout: it copies ignored private task notes
  into the Nix store. Standalone fixtures must also use a Git-flake source
  or a vetted disposable source tree.

## Commands and validation

- User PATH provides `phoenix-target --info`, `phoenix-dry-build`,
  `phoenix-build`, `phoenix-test`, `phoenix-switch`, and `phoenix-boot`.
  `phoenix-rebuild --print <action>` previews the dispatcher command.
- `config/user.nix` owns `repoDirectory`; `PHOENIX_REPO_ROOT` overrides the
  checkout and `PHOENIX_TARGET=metal|vm` overrides target detection.
- Evaluate metal with:
  `nix eval --no-write-lock-file .#nixosConfigurations.metal.config.system.build.toplevel.drvPath`
  Use the corresponding `vm` output when relevant.
- Check flake evaluation with:
  `nix flake check --no-build --no-write-lock-file .`
- For mutable settings, command, desktop, or security changes, run the
  appropriate focused fixtures from tests/README.md.
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
