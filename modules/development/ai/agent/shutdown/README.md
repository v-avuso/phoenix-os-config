# Source-built OpenShell shutdown candidates

## Intentions

Own the small pinned shutdown repairs and reproducible candidate binaries without
changing live feature flags, authority or upstream image ABI. Preserve explicit
administrative cancellation, recovery-loss failure classification and bounded
accepted-tail RPC acknowledgement. Existing validation receipts remain in
[the prototype documentation](../tests/shutdown-cancellation/README.md).

`packages.nix` exports fixed supervisor/runtime candidates from OpenShell 0.1.2
commit `6648bd0c290efbc41ba131ee9831ee45cd431f94`, source archive SHA256
`0ea7e81c5980680d4e65ad292a77ed3fc992a3cf5414bb99669f5c57d9ceb551`.
The three adjacent patches are unchanged validated inputs. Cargo.lock is unchanged
(SHA256 `ea10e2922eece4077a2c1be17cac83214aa5f79f39fd6c5cc830e1a2cf9d459a`);
766 registry dependencies and no Git dependencies share one Nixpkgs vendor import.
The shared vendor hash is
`sha256-zQo6Z62V4n1vQU59fD2Rx3y0nMQuD2Q6A9lzsRyaswI=`; its import
is dependency evidence, not a Rust build receipt.

Reuse locked Nixpkgs Zig/cargo-zigbuild and the existing transitive rust-overlay
(`inputs.timewall.inputs.rust-overlay`) Rust/Cargo 1.95 minimal toolchain with
the official matching musl target. Pass that locked input as `rustOverlay`; no new
flake input or lock update is needed. Its musl archive matches the previously
verified SHA256 `aee540abf132920f791ef781489851a078d69dff493fb628d49c1d573f92bb3a`.
Use the upstream GNU2.28 C/C++ wrapper for supervisor dependencies. `OPENSHELL_GIT_VERSION=0.1.2-phoenix.1` identifies the
candidate without modifying Cargo metadata. Select only each required binary;
never rebuild gateway/workload or consume scratch target/cache as build inputs.

Before release compilation, review evaluation/dry-run and vendor receipts. Use
`--max-jobs 1 --cores 2`, two Cargo jobs, a 20-minute per-build external limit,
25GiB scratch and 8GiB dependency-cache stop limits. These are parallelism
budgets, not hard CPU affinity; daemon-private temporary usage was not directly
measurable. Both offline cold source builds passed: supervisor 4m10s, runtime
2m16s. Both report `0.1.2-phoenix.1`; supervisor has GNU maximum 2.28, standard
loader and no RPATH/store references; runtime is fully static without interpreter,
dynamic dependencies or RPATH/store references. Generic GNU `--version` on NixOS
was checked through the realized glibc loader without rewriting the binary.

Frozen package source `kps896wy…` produced supervisor `dc9cmfsk…` (SHA256
`6ac814d42de4a92aa62c0d0dde95be839538e2021265f09ed044c08730e2fce9`)
and runtime `jrg2nw33…` (SHA256
`ff8b34afce2744c1f3ff81305077ce9daddc40ee65254212a643a14655c44c21`).
Exact build/ELF receipts and logs are `source-{supervisor,runtime}-build-receipt.json`
and `source-*-nix.log` under the existing scratch receipt directory. Image integration,
config/layer checks and representative final-candidate VM proof remain next.
Live options remain OFF; activation is a separate reviewed step.
