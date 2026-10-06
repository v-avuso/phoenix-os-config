# NixOS repository guidance

## Repository map and ownership

- Nix files describe current configuration; README provides orientation and
  docs/VISION.md describes future direction. Preserve cooling, authentication,
  and recovery constraints documented in operational guides.
- Keep agent policy and adapters under `modules/development/ai/agent`.
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
- Use the available graphical Polkit flow for privileged OS actions:
  `pkexec` with a concrete absolute executable and reviewed arguments,
  or a helper's supported graphical flow.
- The project's pinned nixos-rebuild-ng hardcodes sudo;
  `NIX_SUDO=pkexec` is unsupported. Build as the user, then use
  `pkexec /nix/store/<built-system>/bin/switch-to-configuration test`
  for authorized temporary activation.
- Persistent switch additionally requires a deliberate system-profile
  update; temporary activation does not perform that update.
