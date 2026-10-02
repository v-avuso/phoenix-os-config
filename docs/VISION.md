# Vision

Phoenix aims to make a personal workstation easy to understand, secure in daily
use, and recoverable after configuration failure, disk loss, or replacement.
This is direction for future work, not an implementation checklist or a promise
that the current machine already provides every property.

- **Recovery:** tested independent backups, encrypted private bootstrap
  material, and a practical restore procedure; an optional recovery image only
  when it improves that procedure.
- **Explicit ownership:** clear boundaries between the system, user settings,
  application state, credentials, and hardware safety mechanisms.
- **Containment:** stronger application isolation and reviewed network policy
  that protect everyday use without constant approval prompts.
- **Experimentation:** interactive settings changes with reviewed promotion
  into Nix, so experimentation remains easy and lasting intent stays versioned.
- **Replaceable components:** desktop, login, and application choices that can
  change without spreading their assumptions across the repository.

Keep concrete proposals in the task backlog. Update operational documentation
when behavior is implemented; preserve significant decisions in commit bodies
and relevant code comments rather than a second chronological decision log.
