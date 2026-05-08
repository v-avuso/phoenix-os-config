# Manual Steps

Manual setup not yet represented in NixOS config.

| Area | Step | Why Manual For Now | Target |
| --- | --- | --- | --- |
| Secrets | Restore SSH/private keys | Must not be plaintext in repo | Encrypted secrets workflow |
| Hardware | Review generated hardware config after reinstall | Disk UUIDs and devices are machine-specific | Keep documented recovery habit |
| User state | Restore selected app profiles | Not system config | Separate backup process |
| Accounts | Sign into browser/password manager/cloud services | Requires user auth | Keep manual unless safe automation exists |

## TODO

- Decide secrets approach.
- Decide whether to add Home Manager.
- Document exact rebuild command workflow once chosen.
