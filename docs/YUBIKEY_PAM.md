# YubiKey Bio PAM authentication

The shared security module enables `pam_u2f` with FIDO2 user verification
required, so the YubiKey Bio asks for an enrolled fingerprint. The module uses
`sufficient` control: successful key verification authenticates directly; an
absent key or failed verification falls through to the normal Unix password.
NixOS applies the U2F default to PAM services; SSH is explicitly excluded.
For Plasma 6.6, `kde` remains the password service and U2F runs through
`kde-fingerprint`, which KScreenLocker treats as a non-interactive authenticator
and starts automatically. This compatibility route can be removed when Phoenix
moves to native `kde-u2f` support or stops using Plasma.

## Enroll the Bio key

1. Enroll fingerprints on the YubiKey Bio with Yubico Authenticator.
2. After the system configuration is activated, create the per-user mapping:

   ```sh
   install -d -m 700 "$HOME/.config/Yubico"
   umask 077
   pamu2fcfg -u "$USER" -V > "$HOME/.config/Yubico/u2f_keys"
   ```

   Touch the key's sensor when it blinks. `-V` requests FIDO2 user verification
   during registration; the PAM configuration also requires verification at
   authentication time. The default relying-party ID is `pam://$HOSTNAME`, so
   register and authenticate on the same host name.

3. Confirm the mapping exists and is readable only by your user, then try
   `sudo -v` while the key is connected. Keep a working password session open
   until you have verified the new authentication path.

The mapping contains public credential data rather than a password or private
key, but it is still user-specific and should remain outside this repository.
For login-time authentication, keep the mapping on storage available before
login; an encrypted home that is unlocked only after login cannot supply it.

## Services and cue visibility

Interactive local PAM services include TTY login, KDE screen unlock, `sudo`,
`sudo -i`, `su`, `su -`, and Polkit. SDDM's NixOS PAM stack includes `login`,
so it uses the same U2F rule without adding a second module invocation. Polkit's
`polkit-1` PAM stack also inherits the global U2F setting. NixOS adjusts its
socket-activated helper sandbox when global U2F is enabled, giving it read-only
home access for the mapping and HID access for the key.

| Prompt | PAM service | `pam_u2f` cue visibility |
| --- | --- | --- |
| Terminal `sudo` | `sudo` | Visible in the terminal's PAM conversation. |
| SDDM | `sddm` → `login` | SDDM forwards PAM informational messages to the greeter; whether the active theme renders them is theme-dependent, so the cue is not guaranteed. |
| KDE lock screen | `kde-fingerprint` | The non-interactive authenticator starts automatically. The user verified that a Bio touch immediately unlocks the screen. |
| Polkit | `polkit-1` | Plasma's Polkit dialog displays PAM informational messages. |

No graphical cue shim is installed. A PAM frontend that does not render
`PAM_TEXT_INFO` can still authenticate with the key; it simply will not show
the “touch your device” text.

Caelestia's lock uses a separate U2F PAM context alongside password
authentication. Failed key verification is reported as a generic PAM
authentication failure and retried; the Quickshell PAM result API does not
provide a structured signal for a Bio fingerprint-lockout state. The lock UI
therefore shows generic security-key failure feedback rather than guessing
from error text or device-specific behavior. A blocked Bio can still be
recovered with the authenticator's FIDO2 PIN.
