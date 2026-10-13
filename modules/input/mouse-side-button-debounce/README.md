# Side-button shortcuts

Import `default.nix` for the fixed Razer Viper V2 Pro. A restricted non-root
service clones pointer capabilities and preserves movement, ordinary buttons,
and high-resolution scrolling. It translates BTN_EXTRA to held F23 and BTN_SIDE
to held F24 on a separate virtual keyboard. Hyprland/Kando own menu bindings.
The side buttons no longer provide Back/Forward. No keyboard interaction is needed.

Presses pass immediately; stable releases wait 180 ms to suppress long-hold
chatter. libinput already has debounce; the need for this additional window has
not been established by a comparative hardware test. The held-key translation,
not extra debounce, fixes pointer focus retention over application windows.

```sh
python3 -B modules/input/mouse-side-button-debounce/test.py
```

Tests use fake devices and time: no hardware is grabbed. Disconnect and shutdown
release held keys, ungrab the physical device, and destroy both virtual devices.
