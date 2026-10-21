# Typst publishing on Phoenix

## Intentions

Provide declarative compiler/font availability, offline-capable upstream packages
and shared adapter installation. Components own their designs, integrations and
tests so they can be extracted without moving module-wide infrastructure with them.

## Installation and ownership

`default.nix` is imported by the documents module. Phoenix NixOS installs Typst and
fonts, including Liberation Sans. Home Manager installs the vault helper and data
links. Use the normal reviewed Phoenix deployment flow when changing declarative
installation; source edits in the live local design need no activation.

| Location | Owner and role |
| --- | --- |
| `templates/phoenix-letter/template/` | Independent `@local/phoenix-letter:0.1.0` package; [usage](templates/phoenix-letter/template/README.md), [design rationale](templates/phoenix-letter/template/DOCU.md), core fixtures |
| `templates/phoenix-letter/` | [Integration package](templates/phoenix-letter/README.md), canonical adapter and integration tests; [exploratory vision](templates/phoenix-letter/VISION.md) |
| `template-adapters/omd2typst/` | Central aggregation directory, deployed as one vault directory link |
| `deploy-vault.py`, `tests/deployment.py` | Shared registration/migration and path-preservation checks |
| `templates/*.typ` | Original Letter Pro, Briefs, Formal and Metropole Report adapters; unchanged and separate from Phoenix Letter |

The local package points to `${user.repoDirectory}/modules/apps/documents/typst/templates/phoenix-letter/template`.
This is a live source link: keep that checkout available. The official Letter Pro
3.0.0 archive is fetched with a fixed SHA-256 and installed in Typst's data package
directory, which precedes the cache. First Nix setup may need network/cache access; installed Phoenix letters
compile offline. Other original adapters retain their cache/download behavior.
Compiler/fonts come from locked nixpkgs. The legacy template distribution remains
at `~/.local/share/phoenix/typst/templates`.

The unchanged original adapters retain their existing upstreams and notices:

| Adapter | Pinned upstream | License |
| --- | --- | --- |
| Letter Pro | `@preview/letter-pro:3.0.0` | MIT |
| [Briefs](https://typst.app/universe/package/briefs/) | `@preview/briefs:0.4.0` | MIT |
| [Formal](https://typst.app/universe/package/formal/) | `@preview/formal:0.2.0` | MIT package; MIT-0 templates |
| [Metropole Report](https://typst.app/universe/package/metropole-report/) | `@preview/metropole-report:0.1.0` | GPL-3.0-or-later |

## Adapter aggregation

The central `phoenix-letter.typ` is a relative link to
`../../templates/phoenix-letter/adapters/omd2typst/phoenix-letter.typ`, its single
canonical implementation. The vault helper links the entire central directory to
`3-misc/phoenix-typst/omd2typst`; the extra link hop requires no copying or watcher.
See [Phoenix Letter deployment](templates/phoenix-letter/README.md#installation-and-obsidian)
for registration, copied-adapter migration and Obsidian configuration.

Keep the common module root when storing or distributing the central collection;
copying only `template-adapters/omd2typst/` with its symlinks would omit their targets.
The Home Manager templates snapshot contains the canonical component and its inner
compatibility links. The package source targets the inner template directly.
The two outer package compatibility links preserve the previous deployed source
path until a later normal activation; they contain no duplicate implementation.

## Validation

For shared deployment checks: `python3 tests/deployment.py` from this directory.
The module runner also invokes Phoenix Letter's component-owned checks. From the
repository root, use locked dependencies without activation:

```sh
letter_nixpkgs="$(nix eval --raw --no-write-lock-file .#nixosConfigurations.metal.pkgs.path)"
nix-shell -I "nixpkgs=$letter_nixpkgs" \
  -p typst nodejs poppler-utils verapdf 'python3.withPackages (p: [ p.pypdf ])' \
  --run 'python3 modules/apps/documents/typst/tests/run.py /path/to/omd-to-typst/main.js'
```

The runner owns disposable directories. Lower-level adapter reload tests must
never target a real vault/source file. Component docs describe standalone, window,
pagination, PDF/UA-1, privacy and visual acceptance checks. These tests do not
establish live Electron indexing on a different installation.

`tests/source-layout.nix` additionally builds against a Git-flake module source and
an isolated templates snapshot. It verifies relative link targets, old/new package
resolution, registration from the store and strict compilation through the stored
adapter. Stage intended new files before Git-flake checks; never use a checkout-wide
`path:.` source. For example, from the repository root:

```sh
nix build --no-link --impure --expr '
  let f = builtins.getFlake ("git+file://" + toString ./.);
      c = f.nixosConfigurations.metal;
      hm = builtins.head (builtins.attrValues c.config.home-manager.users);
      root = f.outPath + "/modules/apps/documents/typst";
  in import (root + "/tests/source-layout.nix") {
    pkgs = c.pkgs; typstRoot = root;
    letterPro = hm.xdg.dataFile."typst/packages/preview/letter-pro/3.0.0".source;
  }'
```

Use the corresponding configured host/user if those differ. Evaluation/builds are
not activation. Preserve upstream notices when changing archive/package sources;
see component docs for attribution, licenses and dependency-update validation.
