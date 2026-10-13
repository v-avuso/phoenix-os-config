# Idle command integration

When changing IPC wrappers, verify the complete pinned CLI argument route:
`caelestia shell` adds `ipc call` itself. Check output or a captured route;
an invalid IPC target can still return exit status zero.

Manual idle monitors must use a positive timeout on the pinned Hyprland:
zero-timeout notifications never emit resumed on input. Verify the compositor
transition as well as QML cleanup; simulated resume events alone miss this.

Caelestia IPC selects the package configuration path. After shell package
changes, verify the running instance uses the new path; use the upstream
user service to update runtime ownership, not only a successful activation.
