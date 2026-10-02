# Repository instructions

## Work efficiently

- Prefer CLI, structured APIs, and local files. Computer use/screenshots are a
  last resort when those interfaces cannot perform the task; do not open an
  application UI merely to inspect settings available in files or an API.
- Read relevant code and nearby rationale; Nix files describe current behavior.
  README is orientation, docs/VISION.md is future direction. Preserve cooling,
  authentication, and recovery constraints documented in operational guides.
- Keep changes scoped. Preserve concurrent/dirty edits and do not stage or
  commit another worker's files. Coordinate ownership before parallel edits.

## Commands and validation

- User PATH provides `phoenix-target --info`, `phoenix-dry-build`,
  `phoenix-build`, `phoenix-test`, `phoenix-switch`, and `phoenix-boot` in every
  shell. `phoenix-rebuild --print <action>` previews the dispatcher command.
- `config/user.nix` owns `repoDirectory`; `PHOENIX_REPO_ROOT` overrides the
  checkout and `PHOENIX_TARGET=metal|vm` overrides target detection.
- Evaluate with `nix eval --no-write-lock-file
  path:.#nixosConfigurations.metal.config.system.build.toplevel.drvPath`; use the
  corresponding `vm` output when relevant. `nix flake check --no-build
  --no-write-lock-file path:.` checks evaluation, including untracked new modules
  without staging them. Git flakes omit untracked files. Neither proves runtime.
- For mutable settings, command, desktop, or security changes, run appropriate
  focused fixtures from tests/README.md; docs-only edits need document validation.
- `phoenix-dry-build` evaluates a build plan; `phoenix-build` builds without
  activation. `test` activates now; `switch` activates and updates next boot;
  `boot` updates next boot. Never activate merely to validate an edit.
- Activate only within the user's authorized task scope. Report evaluation,
  build, and runtime validation separately. Do not silently update flake.lock.
- Metal hardware configuration is tracked. VM hardware is a tracked placeholder;
  VM deployment requires a real reviewed snapshot. Evaluation is not bootability.

## Privilege and authentication

- Use approval tooling yourself when sandbox permissions are needed. Sandbox
  escalation permits execution; it does not grant operating-system root access.
- For privileged OS actions needing authentication, use the available graphical
  Polkit flow (`pkexec` with a concrete absolute executable and reviewed
  arguments). Use a helper's supported graphical flow when it provides one.
- Pinned nixos-rebuild-ng hardcodes sudo; `NIX_SUDO=pkexec` is unsupported.
  Build as the user, then use `pkexec /nix/store/<built-system>/bin/switch-to-configuration
  test` for authorized temporary activation. Persistent switch additionally
  needs a deliberate system-profile update; do not equate these operations.
- Do not open an empty Codex terminal or start an interactive sudo/password
  prompt expecting the user to authenticate there. Never request passwords or
  secrets in chat. Do not disable authentication or add permissive rules to
  bypass it. If graphical approval is unavailable, state the exact limitation.

## Application ownership

- Follow docs/CONFIGURATION_STATE.md. Separate declarative settings, writable
  experiment baselines, and persistent user state before changing ownership.
- Preserve registered Caelestia/VSCodium experiments at boot; explicit
  switch/test reasserts baselines. Promote reviewed settings to Nix beforehand.
- Never reconcile whole profiles, credentials, databases, history, sessions,
  documents, or other private user state. Keep fan-policy reconciliation
  specialized and hardware safety intact.

## Git and documentation

- Use Conventional Commits: `type(scope): imperative summary`; include a concise
  scope when meaningful. Non-trivial commits need a body explaining why,
  non-obvious tradeoffs, and relevant validation.
- Keep docs compact: update current behavior in README/recovery/state guides,
  future direction in VISION, and local rationale in comments/commit bodies.
  Avoid duplicating code inventories or maintaining an exhaustive decision log.
