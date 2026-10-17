# Administrative terminal-delivery proof

This validation-only overlay tests one OpenShell 0.1.2 shutdown defect. It keeps
all verified upstream supervisor image layers/config and replaces only
`/openshell-supervisor` through locked nixpkgs `dockerTools.buildImage`.
It is not installed configuration or a reproducible full source package yet.

Source: upstream commit `6648bd0c290efbc41ba131ee9831ee45cd431f94`;
[supervisor.patch](supervisor.patch) SHA256
`5af656da20035f021b4a2a268dd17e33ecc38faad09b5130117e77dd3b401a40`.
The isolated scratch runner `/tmp/phoenix-shutdown-cost-s3_rohmh/build-supervisor.py`
uses upstream GNU wrapper setup and `cargo zigbuild --offline --locked --release
--target x86_64-unknown-linux-gnu.2.28 -j2 -p openshell-supervisor
--bin openshell-supervisor`, Rust 1.95/Zig 0.16, two CPUs, 20 minutes and 25 GiB caps.
The validation binary retains package version 0.0.0; SHA256
`112a50bafdc5b94998cf4d3c403efad3f96b3f0cf637f7cd096c301ec7c88654`.
It requires at most GLIBC 2.28 and has no RPATH/RUNPATH. Add this exact binary with
`nix-store --add-fixed sha256`, then pass its immutable path as `binary` to
[image.nix](image.nix) using a Git-flake source; never `path:.`.

The existing shutdown fixture defaults to `acceptanceScope = "full"`, unchanged.
The explicit `"terminal-delivery"` scope permits ordinary stop only: real active
workload plus attached create/log streams, TERM/FINAL, both containers stopped
without 137, stop below 10 seconds, and finite nonzero attached status excluding
124/137 with the exact administrative cancellation explanation. Structured output
retains actual runtime exit classification; this does **not** prove zero runtime
exit, complete graceful shutdown, final log flush or blocked detached SSH cleanup.
The production 45 second fallback remains unchanged.

The isolated terminal-delivery VM passed from frozen Git-flake source
`g2k6w78an4vglf590q4a3qiv65c4lyfl-source`, with supervisor image ID
`bcb8d358069b8f8525c33a59c76a0d459d53b0068da9b700a1e8e609b91b2003`.
Ordinary stop took 1.491 seconds; TERM/FINAL arrived and the attached client
finished with status 1 plus the exact cancellation explanation. The supervisor
exited 0 and runtime 1; both stopped without 137. Active workload and nonempty
live log stream were verified before stop. The gateway logged relay EOF, and no
stream completion status was captured before the owned reader was stopped;
stream completion, final log flush and full graceful shutdown remain unproved.
Structured evidence:
`/nix/store/gkqj17q04ndn401bamqj9b2y98rcrfr8-vm-test-run-phoenix-shutdown-openshell/final/shutdown-evidence/terminal-delivery-outcome.json`.
This remains a validation prototype: no reproducible full source package or live
option enablement follows from the trial.

## Runtime classification prototype

[runtime-classification.patch](runtime-classification.patch), SHA256
`494c38d9a1a28d3224e52e7919d16329ff9753281caa2e83018c72f7ccfd034e`,
keeps explicit versus expired-recovery cause inside the existing lifecycle state.
Completed retries acknowledge either cause without reclassifying recovery loss;
in-progress explicit retries remain possible. Nine focused native tests passed,
including the failing-before-repair signal classification and opposite ownership
orderings. The isolated runtime-classification VM also passed from frozen source
`c10cjab2kch0kg3d5hhvkyazs7jlvhbh-source`, using runtime image ID
`1f746b8f2ba00577f710fd1d0e78b00e47c930c620b85e4f0e0285523eabf680`
and the validated supervisor above. Stop took 1.478 seconds; both containers
exited 0 with TERM/FINAL, while the client correctly returned cancellation 1.
The guest verified the running `/proc/PID/exe` hash and image-bound extracted
binary path before stopping; the old confirmation warning was absent.
Structured evidence:
`/nix/store/6l8ar5bmny4sd3vckg09mf4hs7q65ab8-vm-test-run-phoenix-shutdown-openshell/final/shutdown-evidence/runtime-classification-outcome.json`.
The log reader had no captured completion status before its owned stop; gateway
relay EOF remains independent. Final push acknowledgement, final log flush and
full graceful shutdown are not proved. No live rollout was performed.

The scratch `build-runtime.py` runner builds only `openshell-sandbox` with
`cargo zigbuild --offline --locked --release --target x86_64-unknown-linux-musl
-j2 -p openshell-sandbox --bin openshell-sandbox`, plus target-only `--sysroot`
pointing at isolated official Rust 1.95 musl std (same compiler commit). Binary
SHA256 `745245e8f79e6a5050a78570a79b24ac3488c50dd3636ec5c8409755ec418d94`
is fully static ELF64 x86-64, no interpreter/NEEDED/RPATH, version 0.0.0.
Use `image.nix` with `role = "runtime"`; it preserves the scratch-image config,
base layers and mode 0555, replacing only `/openshell-sandbox`.

Explicit ordinary-only `acceptanceScope = "runtime-classification"` inherits
terminal-delivery checks and additionally requires both container exits zero,
absence of the old confirmation warning, and running runtime ELF hash bound to
the selected runtime image ID. Local container logs and structured state remain
captured. Full default acceptance stays strict; final log flush and complete
graceful shutdown are independent, unproved requirements. No live enablement or
reproducible full source package is implied by these validation artifacts.

## Owned log-drain proof and matched validation build

[log-drain.patch](log-drain.patch), SHA256
`2f4981993d4e73de6d817771bce83266a645902f138d3054eea27c2a77eb7318`,
applies separately to the same pristine pinned source (fuzz 0, byte-identical to
tested scratch files). Only `openshell-supervisor-process/src/log_push.rs` and
`openshell-supervisor/src/main.rs` change. The earlier cancellation-only supervisor above predates this patch. A matched
GNU 2.28 supervisor was built offline in 99.77 seconds, binary SHA256
`14c412633c65c57a2c20fc2f3c093c6a181238f25628a854ffe95abd43f88f8c`.
It retains the standard loader/library set, max GLIBC 2.28, no RPATH/RUNPATH and
prototype version 0.0.0. `image.nix` now binds that supervisor while the static
runtime remains unchanged; the prior binary/receipts are preserved in scratch
`artifacts/cancellation-supervisor/`. The matched ordinary log-drain VM passed as below.

RED demonstrated the old production final-send branch returning before server
acknowledgement. GREEN passed 19 focused tests, including retained sender clones,
EOF before withheld acknowledgement, missing/error/auth acknowledgement,
backpressure/deadline, <=50-line batches above the server's 100-line cap, owned
RPC cancellation/drop, and prior loss reported separately from retained-tail ack.
The caller's post-layer expected-error paths now reach shutdown; main was
cargo-checked, not integration-executed. Tests use controlled RPC futures, not
real tonic/server acknowledgement. Normal best-effort overflow/backoff and
administrative canonical-report skipping remain; one absolute second bounds
shutdown queue drain plus EOF/RPC response, with static local incomplete output.

Resume commands with the existing isolated cache, CPU affinity two and caps:
`/nix/store/0r6k8xa2kgqyp3r4v2w7yrb80ma2iawm-python3-3.13.12/bin/python3 /tmp/phoenix-shutdown-cost-s3_rohmh/test-log-green.py`
and `.../python3 /tmp/phoenix-shutdown-cost-s3_rohmh/check-log-main.py`.
The runners execute `cargo test --offline --locked -j2 -p
openshell-supervisor-process --lib log_push::tests -- --test-threads=2` and
`cargo check --offline --locked -j2 -p openshell-supervisor --bin openshell-supervisor`.
Exact environment/results and hashes remain in scratch `log-*-receipt.json` and
`log-drain-manifest.json`; all inputs are scratch/public Nix store paths.
Explicit ordinary-only `acceptanceScope = "log-drain"` verifies both running ELF
hashes/image bindings and inherits cancellation/runtime checks. It requires one
final marker in the fresh sandbox's live gateway tail plus exactly one local
actual RPC outcome: accepted-tail acknowledgement true, drops 0, prior-stream
uncertainty false, incomplete None. Local INFO-marker count is diagnostic only:
the pinned console defaults to WARN while the independent push layer accepts INFO.
Query output and structured state are captured.
The corrected VM passed with source `g85n9g0f…`, output `cpfb8pfd…`: stop
1.436 seconds, TERM/FINAL, explicit cancellation 1, both containers exit 0,
verified running ELF/image bindings, exactly one acknowledged RPC outcome and
one final event in the fresh live gateway. The first run failed only an invalid
local INFO-marker assertion: captured console defaults to WARN, independently
of the INFO push layer; its failed receipt remains preserved. Exact structured
evidence is `log-vm-corrected-receipt.json` in the scratch receipt directory.
This proves the accepted live tail. Detached denial-summary draining is a
telemetry limit, not a baseline blocker; restart durability is outside the
upstream memory-tail contract.
Tail observer exit and gateway restart are not acknowledgement/durability proof;
full graceful shutdown and live rollout remain unaccepted.

`acceptanceScope = "ordered-lifecycle"` is the transaction/manager
fixture extension requiring module-generated ordering, the same running binary
bindings, cgroup placement/resource limits, TERM/FINAL, both exits 0, stop under
ten seconds, exact administrative cancellation and the same successful local
RPC outcome. It does not restart the gateway or require a tail-observer exit.
Unknown disconnects or incomplete cooperative RPC outcomes fail for diagnosis;
unavailable-peer negatives are separate. Full/default gates remain unchanged.

The matched ordered scope passed both modes with frozen source `cahkkvcv…`:
transaction 1.452 seconds (`hfr9wyxc…`) and manager 1.483 seconds (`5izgjazi…`).
Both prove TERM/FINAL, both containers stopped/exit 0 without OOM/SIGKILL, exact
client cancellation 1, one actual RPC ACK true/0/false/None, running binary/image
bindings and no-conmon/Before-gateway placement with 512MiB/512-pid limits.
Manager status was inactive (3) immediately before post-stop reads; no PAM or
gateway/manager restart was introduced. Tail-reader exit 1 is independent.
Exact receipts are `ordered-lifecycle-vm-receipt.json` and
`manager-lifecycle-vm-receipt.json` in the scratch receipt directory. These remain
validation-only overlays; reproducible source packaging and controlled rollout
are next, not a claim that every background telemetry task drains.
