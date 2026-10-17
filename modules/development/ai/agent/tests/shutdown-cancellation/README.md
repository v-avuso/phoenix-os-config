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
