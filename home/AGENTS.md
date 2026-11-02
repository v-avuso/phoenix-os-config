# Home/session integration

- Caelestia volume steps have two owners: shell `services.audioIncrement`
  controls pointer scrolling; Hyprland `volumeStep` controls media keys/knobs.
  Check both paths when changing volume increments.
- For live Hyprland commands, check the installed `hyprctl --help` before choosing
  an interface. Phoenix uses Lua Hyprland: launch a fixed executable with
  `hyprctl eval 'hl.exec_cmd("/absolute/executable")'`; legacy `dispatch exec`
  may be rejected. Match the session startup API without restarting the desktop.
