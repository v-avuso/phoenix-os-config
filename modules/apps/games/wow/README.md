# World of Warcraft Retail (metal-4tb)

### Intentions

Manage release archives in the existing Lutris/Battle.net Retail AddOns directory,
without moving the installation, writing WTF, adopting unrelated add-ons, or
controlling the game. `wow.nix` owns the package, dedicated `phoenix-retail`
profile and user `v`'s daily 09:00 Europe/Berlin timer. `Persistent=true` catches
missed runs when the user manager returns; it does not wake the computer.

Edit [`wow-addons.json`](wow-addons.json) to declare desired source URIs. The
small `wow-addons sync` adapter queries instawow's native JSON list and installs
missing entries. Edit the manifest, then deploy the configuration to publish
its new immutable copy; `sync` uses that deployed copy. Each timer run syncs then executes `instawow update`. Removing
an entry never deletes an add-on: removal remains an explicit operator action.
Instawow's SQLite database, cache, profile and rollback history remain mutable;
the manifest is an additive desired set, not a mirror of all installed add-ons.

```sh
wow-addons search "quest"              # interactive selection; cancel to avoid installing
wow-addons sync                         # apply deployed manifest additions
wow-addons install github:owner/repo    # immediate addition; also edit manifest
wow-addons list --format detailed
wow-addons update
wow-addons remove github:owner/repo     # remove from manifest first
wow-addons rollback github:owner/repo
systemctl --user start wow-addons-update.service
systemctl --user list-timers wow-addons-update.timer
journalctl --user -u wow-addons-update.service
```

CLI and timer operations share a one-hour-wait flock; the oneshot cannot overlap
itself. Use `wow-addons` for this profile to retain that lock. Errors propagate
from instawow to systemd; stdout/stderr go to the journal under the host's journal
retention policy. The service limits writes to AddOns and tool state/cache and
makes WTF read-only. There is no game-process check, signal, restart or reload.
Existing unmanaged folders cause an installation conflict rather than replacement;
back them up and explicitly select `wow-addons install --replace SOURCE` only
when adoption is intended. Never use automatic whole-directory reconciliation.

Sources: [ElvUI via Tukui](https://github.com/tukui-org/ElvUI),
[ToxiUI releases](https://github.com/Toxicom/toxiui/releases), and
[WindTools releases](https://github.com/wind-addons/ElvUI_WindTools/releases).
The locked and current Nixpkgs recipes still provide 7.0.0.post1, whose catalogue
parser rejects `forever_classic`. `wow.nix` pins the complete upstream 7.3.0
source and checksum instead of carrying compatibility patches or updating the
system lockfile. The override adds upstream's versioningit build backend and
wcwidth dependency. Click 8.4.1 is pinned because the locked Click lacks a required API. Three
dependency lower bounds (aiohttp, rapidfuzz, yarl) are relaxed to reuse the locked Python packages; focused upstream tests
and live catalogue/release checks validate this combination. Revisit these
relaxations on package updates; remove the override once the locked Nixpkgs
package supplies a verified release. Source/version stamping is build metadata,
not a runtime compatibility patch.
[Instawow](https://github.com/layday/instawow) supports native profiles, rollback
and GitHub ZIP release assets. CurseForge resolution was tested and reports
`access token missing`; author distribution restrictions can further prevent
downloads. Search may still display CurseForge catalogue entries when downloads
are disabled. These three sources require no CurseForge key. Do not commit tokens.

Updates may write files while WoW is running. Already loaded Lua remains in memory;
this is not hot patching. Manually reloading during an update can read a mixed
version; wait for the service to finish. A later manual `/reload` may reload
existing add-ons, while newly installed add-ons or changed file discovery may
require exiting and reopening WoW. No in-game reload/restart is automated.
Actual in-game behaviour and UI compatibility require player acceptance; successful
archive installation/update and unchanged WTF hashes do not prove those outcomes.


## Installation and profile

Retail is installed at:

```text
/home/v/Games/battlenet/drive_c/Program Files (x86)/World of Warcraft/_retail_
/home/v/Games/battlenet/drive_c/Program Files (x86)/World of Warcraft/_retail_/Interface/AddOns
```

`wow-addons` selects `phoenix-retail` automatically. Native commands need the
explicit profile: `instawow -p phoenix-retail list` and
`instawow -p phoenix-retail search "quest"`. The native default profile is separate;
listing it does not show this profile's managed add-ons. The declarative profile
file is `~/.config/instawow/profiles/phoenix-retail/config.json`; its SQLite database
is `db.sqlite` beside it. Home Manager deploys a writable profile baseline using
Phoenix's existing JSON writer, so native OAuth configuration can rewrite it.
Home Manager activation reasserts the declared profile/path; keep lasting path
changes in Nix. Global configuration, credentials and database remain app-owned.

## GitHub authentication

GitHub OAuth is already configured on this installation. Do not repeat onboarding
or replace its token during deployment. For a **new installation only**, use:

```sh
umask 077
instawow -p phoenix-retail profile configure global_config.access_tokens.github
```

Accept GitHub authentication, open <https://github.com/login/device>, enter the
generated device code, approve the instawow application, and wait for completion.
Do not paste access tokens into command arguments, chat, Git or logs. The OAuth
request asks for no additional scopes: expected access is read-only public data,
not permission to modify repositories or read private repositories. Review the
actual GitHub consent screen before approval. Authenticated GitHub API requests
normally allow 5,000 requests/hour instead of the unauthenticated 60/hour;
secondary limits can still apply. See [GitHub rate limits](https://docs.github.com/en/rest/using-the-rest-api/rate-limits-for-the-rest-api)
and [OAuth scopes](https://docs.github.com/en/apps/oauth-apps/building-oauth-apps/scopes-for-oauth-apps).

On Linux, credentials are plaintext under `$XDG_CONFIG_HOME/instawow` (default
`~/.config/instawow`). The existing credentials and native configuration writes use `config.json`;
7.3 preserves this format. It can also read an optional separate
`config.access_tokens.json` override if one has been provisioned. Preserve both
files if present. They are global,
shared across profiles, and must never be managed by Nix or copied into Git/the
Nix store. Keep the instawow config directory mode **0700** and credential files
**0600**, owned by `v`; `umask 077` protects newly created files. Do not publish
`instawow debug` output without inspecting its redaction behaviour.

## Future settings and recovery outputs

The manifest manages packages only. The timer never imports profiles or reapplies
settings. Future configuration work must first research each add-on's supported
interfaces and assign overlapping responsibilities (unit frames, nameplates,
quest tracking, etc.) to an explicit owner. Follow [scoped agent guidance](AGENTS.md).

**Personal backup:** Once the concrete add-ons are chosen, document a quiescent
backup of complete WTF settings, the manifest/repository revision, add-on versions
and any required per-add-on exports. Keep private account/realm/character mappings
and credentials outside Git, in restricted private storage. Back up instawow state
with the process stopped or SQLite's backup API, not an inconsistent live database
copy. Restore into a backed-up destination while WoW and add-on writers are stopped;
map installation/account paths deliberately and verify in game. Credentials are a
separate secret backup or fresh onboarding step, not part of a shareable preset.

**Shareable preset:** Prefer supported portable exports per add-on, accompanied by
the manifest, compatible versions, feature-ownership decisions, import order and
manual steps. Sanitize account, character, realm, chat/friend information, tokens
and other private fields; review actual export contents and test in a disposable
profile/installation before sharing. Do not publish an entire WTF directory.
No generic importer/exporter or speculative preset scripts are provided. Add
concrete files only when the selected add-ons offer a reliable, tested mechanism.
