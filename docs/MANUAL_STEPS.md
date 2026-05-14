# Manual Steps

Manual setup not yet represented in NixOS config.

| Area | Step | Why Manual For Now | Target |
| --- | --- | --- | --- |
| Secrets | Restore SSH/private keys | Must not be plaintext in repo | Encrypted secrets workflow |
| Bootstrap | Restore Git signing/auth material | Requires private keys or tokens | Encrypted bootstrap process |
| Sync | Restore or re-pair Syncthing identity | Device keys and private IDs stay out of repo | Private bootstrap/backup workflow |
| Hardware | Review generated hardware config after reinstall | Disk UUIDs and devices are machine-specific | Keep documented recovery habit |
| User state | Restore selected app profiles, private notes, and data | Not system config | Separate backup or Syncthing process |
| Repositories | Re-clone working code repositories | Project repos are external state | Git remotes plus restored SSH/auth |
| Accounts | Sign into browser/password manager/cloud services | Requires user auth | Keep manual unless safe automation exists |

## TODO

- Decide secrets approach.
- Decide whether to add Home Manager.
- Decide Syncthing/bootstrap restore model.
