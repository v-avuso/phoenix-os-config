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
config/layer checks passed, followed by final-candidate VM proof below.
Live options remain OFF; activation is a separate reviewed step.

`images.nix` defines only the two candidate images from these fixed packages and
`dockerTools.pullImage` official 0.1.2 Linux/amd64 digest pins. Base config IDs
are checked before copying the full config (without duplicating inherited Env);
one layer replaces only the executable at its fixed mode. Both base transport
hashes were discovered once and exact imports passed; independently verified base
config IDs match the existing release receipts. Both final images then built
offline without Rust rebuilds. The fixture
accepts an independently verified `binarySha256` in each image record and still
hashes the actual running `/proc/PID/exe`. Historical records retain their fixed
prototype hashes. Verify full config, old-layer identity, sole added executable
and its package hash before running the final image path in the guest.

Final image recipe source `8s7yir1q…` produced supervisor image `7ddc3780…`
(archive `y778p23q…`, SHA256
`2f6da0f314b68f53e465dfa796397e5e86275dabc03e26ef74aa46485ed423c6`)
and runtime image `510b992e…` (archive `n6dbxll7…`, SHA256
`cc90da13f9cdae9279f0978710fcddee897ae08e9f58dd335edfa9dff8184cec`).
Full config equality, byte-identical old layers and a sole root-owned executable
with exact source-package hash/mode passed for each. No added libraries, symlinks
or Nix filesystem paths are present. Exact artifacts and the verifier are in
`final-images-receipt.json` and `verify-final-images.py` in the scratch receipt
directory. Final source-built images passed ordinary log-drain (1.528s) and ordered manager
teardown (1.489s) with frozen fixture source `2s0vryrn…`: both container exits 0,
TERM/FINAL, exact administrative client cancellation 1, one successful actual
RPC acknowledgement, and running ELF/image bindings. Ordinary also proved one
final live gateway event; manager was inactive immediately before reads and
preserved resource/cgroup gates without PAM or restart. Outputs are `a50gbi6x…`
and `rhp7fhnk…`; exact evidence and continuation commands are
`final-candidate-vm-receipt.json` and `CONTINUE-SOURCE-IMAGES.md` in scratch.
Source imports, toolchain/vendor inputs and image builds are now fixed/repeatable.
No live host rollout occurred. Negative results and remaining integration limits
are recorded below.

Representative negative fixture scopes now pass with the same final images and
ordering/resource/binary gates. TERM-ignore (`gz6cd040…`, output `ppa5zrh0…`)
stopped in 5.484s: ignored TERM/no FINAL, reported workload status 137, runtime 0,
explicit client cancellation 1 and actual ACK; status 137 alone does not prove
container PID1 SIGKILL. Gateway-loss (`dhzdmn7w…`, output `80wqx5i5…`) stopped
locally in 1.536s: gateway inactive/restart disabled, both exits 0/no OOM, scopes
inactive, independent TERM/FINAL file copied from the exact stopped container,
and actual log outcome false/0/true/Some(NotConnected). No fabricated ACK/all-logs
claim is made. A separate 75s observation (`iiavl8nf…`, output `fsgqw67c…`)
retains local cleanup at 1.507s and observes CLI exit 255 with the exact pinned
`Unable to restore the sandbox connection within 60 seconds.` diagnostic
(completion within the 75s observation; 73.381s includes post-read captures,
not exact recovery duration). This is bounded failed transport recovery, not
administrative cancellation or successful unavailable-gateway operation. The
original receipt cleanup-only classifier remains false and is preserved. The
corrected classifier separately recognizes exit 255 plus the exact recovery
message. Pinned `main.rs` keeps sandboxes by default unless `--no-keep` is used,
so supervised recovery is expected; no ephemeral-delete error was observed. The original peer assertion used the
killed gateway as its observer; that red receipt remains preserved.

Exact negative receipts are `negative-runtime-vm-receipt.json` and
`negative-peer-observer-vm-receipt.json` in scratch. Both retain the initial
under 10s gate and 45s fallback; no 50s stall was accepted. The atomic module bundle
remains OFF. Next is controlled quiescent rollout; the peer transport failure
receipt is separate from local cleanup. No production flag or host service was changed.

## Opt-in module integration

`phoenix.agent.shutdownOrdering.enable` now selects the matched source images and
no-conmon/Before-gateway ordering atomically; it still defaults OFF. OFF retains
the official image pins, gateway configuration and launcher revision behavior.
Initial ON support is operator identity only: protected identity is rejected until
its distinct service composition has separate acceptance.

The build-time manifest derives exact archive/config/binary bindings from the
closed images. The generated immutable gateway config uses those content IDs.
A fixed pre-start helper addresses only the existing private rootless Podman API:
wait within the shared deadline for the exact Unix socket (retrying only missing/
refused), verify present IDs, or hash/load a missing fixed archive and verify its ID. It
never pulls, reads credentials, or takes `launch.lock` (the launcher already holds
that lock during `systemctl start`). Static failures exclude Podman output. One
20s import budget extends the existing 30s startup bound to 50s only when ON;
the 45s shutdown fallback is unchanged. Present IDs skip archive scans/imports.

The manifest path participates in launcher revision selection; existing shared
instance-use locks reject busy instance replacement before stop/create. Image
addition during service startup is separate from instance replacement and can
precede that guard. Neither importer nor launcher guard protects Home Manager
stopping an old gateway: rollout requires explicit quiescence before unit
activation. Native fallback, provider auth/history and recovery remain unchanged.
Eleven offline helper tests, 21 launcher tests and generated ON/OFF composition
checks pass, including exact ID substitution and the protected-identity rejection.
OFF gateway bytes match committed baseline `6baccb901…`. A disposable guest using
the actual synthetic-user Home Manager units passes cold empty-store startup in
6.136s while `launch.lock` is held: the importer loads both exact IDs without
deadlock. An active workload/logstream then passes manager teardown in 1.503s,
with both exits 0, exact cancellation 1, one successful RPC receipt, verified
running binaries and preserved resource/cgroup gates. The manager is immediately
inactive; the 45s fallback is unchanged. Frozen fixture source `dik0yrgq…`, output
`xc7027vd…`; exact evidence is `cold-module-vm-receipt.json` alongside
`backend-integration-focused-receipt.json` in scratch. This uses synthetic guest
registration and a small public workload, not full Phoenix GUI/model/auth
acceptance or host activation. The later peer-loss observation verifies expected
bounded recovery failure (exit 255 and the exact 60s expiry diagnostic), not
successful reconnection.

The full metal system from source `501bdbb`, with
`shutdownOrdering.enable = true` through `extendModules`, built offline successfully:
`/nix/store/b218x0ch3j4na8566cvm5kbrlv5yz05d-nixos-system-phoenix-26.05.20261004.0d9e9b8`.
Exact evidence is `/tmp/phoenix-shutdown-cost-s3_rohmh/enabled-system-build-receipt.json`.
Repository defaults and the live host remain OFF; this closure was not activated.
The whole-flake offline no-build check passed metal/VM/default before the final
fixture/docs commits; production implementation was unchanged. This docs-only
checkpoint records the tested source and requires no self-rebuild. Controlled
quiescent rollout and real Phoenix GUI/model acceptance remain separate.
