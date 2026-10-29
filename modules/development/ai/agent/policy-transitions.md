# Administrator-approved security-policy handovers

## Intentions

- Preserve exact fingerprint, target and immutable source/closure checks.
- Require the security administrator's informed authorization before changing the
  review authority; a reviewer verdict alone cannot replace that authority.
- Retain useful review context after an authorized upgrade without relabelling old
  approvals or treating activation as approval.

## Boundary and ordinary operation

Version 2 separates two identities:

- **Security authority**: policy text, controller/reviewer/security/source-validator
  code, helper contents, caller/reviewer/builder identities, model settings,
  deployment guards, fixed activation environment, authorization policy, and
  declared execution roles. Changing these still needs administrator authorization.
- **Execution toolchain**: exact immutable package paths for Python, Nix, systemd,
  sandbox tools, the reviewer executable, CA bundle, target guard and locale data.
  Every version-2 checkpoint binds these paths along with its exact source/closure.

Packaging relocates the same helper bytes when the Git source changes. The
fingerprint canonicalizes only the verified one-line helper path assignments in
controller/reviewer code, hashing every referenced helper separately. Missing,
duplicate or mismatched declarations fail closed. It never strips arbitrary store
paths or excludes controller/validator logic. Fixed activation environment values
remain authority; separately declared package-backed values may change only in
the toolchain identity, with their variable names retained in authority.

After a candidate build, the controller reads the exact immutable systemd unit and
its controller configuration. `policy-transition-required` rejects changed
security authority before review, publication or activation. Changed tools alone
require `toolchain-transition-required`, unless the exact candidate already has a
protected receipt or the controller is processing a validated distribution update.
Review-OFF systems retain their existing native operator deployment behavior.

### Distribution updates

The existing deterministic source validator remains the sole automatic path. It
allows only its established publisher/lock changes and satisfied hold removals;
custom configuration, helper, policy or controller changes remain rejected. It
checks against the same exact installed active or staged source selected by the
runner. With review enabled, version 2 additionally requires protected approval of
that predecessor source/closure; an activation marker alone never grants trust.

After source validation and a build with unchanged security authority, the root
controller publishes a `distributor-update` receipt binding successor policy,
toolchain, target, source and closure to compact protected predecessor evidence.
Publication rechecks installed bindings. Activation rechecks them again, including
inside the durable activation helper. Existing root-only storage, deployment locks,
GC roots and bounded retention are reused. The compact evidence survives pruning
without recursive history or wholesale adoption of another policy's records.
Ordinary review and pending/disruption decisions retain exact toolchain bindings.
No receipt, verdict, permission flag or tool selector is accepted from the socket.

This deliberately trusts the already approved distribution publishers to supply
new executable implementations. It does not independently audit package contents
or protect against a compromised publisher/compiler/runtime. Pinning all tools
would avoid that trust but prevent ordinary security/package upgrades; prompting
for each path change adds friction without reviewing package behavior. The
restricted validator plus exact root receipts makes that existing distribution
trust explicit without adding model calls, services or recurring approval work.

## Human decision, then a bound transition

1. Prepare and test the change without activation. Give the administrator a report:
   why review authority changes, why this design is preferable, old/new fingerprints,
   approved predecessor source/closure, exact candidate source/closure, full diff
   scope and actual validation limits. Explain any unrelated intervening changes.
2. Leave **Authorization: security-policy handover** in Open tasks. An explicitly
   requested PR may carry the implementation for administrator approval. Creating
   or approving that PR does not itself authenticate or activate an exact closure;
   do not invoke authentication or interpret implementation permission as handover approval.
3. After explicit authorization, prepare the on-demand immutable helper from
   `recovery/policy-transition.nix`. Its fixed descriptor contains `installedConfig`,
   `installedPolicy`, `runtime`, `profile`, `baseline`, `predecessorConfig`,
   `predecessorPolicy`, `approvedSource`, `approvedClosure`, `candidateConfig`,
   `candidatePolicy`, `candidateSource`, `candidateClosure`, and informational `commit`.
   Version-1 → version-2 migration also requires `identityMigration` exactly
   `authority-v1-to-v2` and a separate `candidateLegacyPolicy`: the installed legacy
   implementation authenticates that exact candidate before review, then the
   successor verifies `candidatePolicy` with version 2 only after the bound verdict.
   Other algorithm transitions or missing migration fields fail closed. Legacy
   policy computation remains unchanged for predecessor evidence.
   The inspect executable reads bindings without model use, approval or activation;
   it explicitly does not establish protected-checkpoint acceptance.
4. Use the supported native administrator Polkit flow for that **exact immutable
   helper and descriptor**, after the report has been approved. There is no installed
   automatic grant, generic socket receipt import, or reviewer-authorized fallback.
5. The helper verifies a protected predecessor approval and its issuing closure's
   immutable controller/configuration. It independently checks the currently
   installed configuration and candidate binding. This also repairs the already
   broken case where the installed fingerprint differs from its issuing predecessor;
   it never adopts all records from an old policy.
6. The already installed trusted reviewer reviews the full predecessor-to-candidate
   source/mode diff, bound to both fingerprints. Replacement reviewer code does not
   conduct this review. Existing bounded model/context limits apply. Denial, error,
   changed active state or missing predecessor evidence prevents publication and
   activation. No automatic retry, reseeding or override occurs.
7. After locked rechecks, publish one root-owned successor checkpoint with origin
   `administrator-reviewed-transition`, administrator UID, both policy identities,
   exact successor binding and a snapshot of the protected predecessor binding.
   Retain predecessor source/closure GC roots as long as this receipt is retained.
   Activate only the reviewed candidate and verify installed bindings and successor
   checkpoint acceptance.

The successor validates that receipt, both closure/source bindings and both
fingerprints when selecting it. Other old-policy checkpoints stay old-policy;
new changes still need independent review. Receipt integrity relies on the same
root-only record storage as existing approvals, not a new signing service. The
predecessor snapshot survives normal record pruning without unbounded recursive
history; it was copied only from an independently verified protected approval.

The helper reuses the existing source-recovery workflow. It conservatively rejects
review disablement, changed caller/reviewer/builder identities, credential-store
relocation, authorization-policy changes and enabled reservations. Reviewer
executable/model changes are supported: the installed reviewer evaluates them and
the administrator authorizes their exact successor fingerprint. Such broader authority
migrations need a separately designed and explicitly authorized migration, rather
than silently widening this handover. The first installation of this mechanism
itself requires the administrator-approved helper, because older controllers lack
its gate and the current host has already lost same-policy checkpoint continuity.

## Validation and limits

`tests/toolchain-policy.py` covers versioned identity stability, helper binding,
exact receipts, two updates across pruning, stale pending decisions and a real
legacy-to-v2 receipt. `tests/policy-transition.py` exercises real legacy digests, persisted receipt publication,
checkpoint selection and retention with explicit OS/store ownership stubs.
`tests/source-bootstrap.py` covers native-identity admission, installed-reviewer
selection, denial/forgery/error/state-change rejection and review → publication →
activation ordering. `tests/agent-deployment.py` covers the gate through production
automatic and explicit deployment paths, including source validator → toolchain
receipt → activation recheck with distinct caller/updater UIDs, active/staged
predecessors and retention of one record. No model calls are added to updates. These offline fixtures do not establish
native Polkit UX, protected live reviewer access or real activation continuity;
those require the separately authorized installation/acceptance run.
