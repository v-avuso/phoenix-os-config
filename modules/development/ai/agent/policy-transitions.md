# Administrator-approved security-policy handovers

## Intentions

- Preserve exact fingerprint, target and immutable source/closure checks.
- Require the security administrator's informed authorization before changing the
  review authority; a reviewer verdict alone cannot replace that authority.
- Retain useful review context after an authorized upgrade without relabelling old
  approvals or treating activation as approval.

## Boundary and ordinary operation

The fingerprint covers policy, controller/reviewer code, helper bytes, execution
identities and tools. Even a diagnostic change in those files changes it; toolchain
updates can also change it. The digest algorithm remains unchanged. A change to
that algorithm itself needs an explicit versioned migration, not normalization or
removal of security-relevant inputs.

After a candidate build, the controller reads the exact controller/configuration
selected by the candidate's immutable systemd unit. If its fingerprint differs,
`policy-transition-required` stops before model review, checkpoint publication or
activation. The response and compact journal summary identify both fingerprints.
This applies to explicit deployments, unattended updates and critical overrides.
Same-policy deployment/checkpoint reuse retains its existing behavior. Review-OFF
systems retain native operator deployment; a root administrator remains able to
replace system code/state outside this mechanism.

## Human decision, then a bound transition

1. Prepare and test the change without activation. Give the administrator a report:
   why review authority changes, why this design is preferable, old/new fingerprints,
   approved predecessor source/closure, exact candidate source/closure, full diff
   scope and actual validation limits. Explain any unrelated intervening changes.
2. Leave **Authorization: security-policy handover** in Open tasks. Do not open a PR,
   invoke an authentication dialog or interpret implementation permission as approval.
3. After explicit authorization, prepare the on-demand immutable helper from
   `recovery/policy-transition.nix`. Its fixed descriptor contains `installedConfig`,
   `installedPolicy`, `runtime`, `profile`, `baseline`, `predecessorConfig`,
   `predecessorPolicy`, `approvedSource`, `approvedClosure`, `candidateConfig`,
   `candidatePolicy`, `candidateSource`, `candidateClosure`, and informational `commit`.
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

`tests/policy-transition.py` exercises real digests, persisted receipt publication,
checkpoint selection and retention with explicit OS/store ownership stubs.
`tests/source-bootstrap.py` covers native-identity admission, installed-reviewer
selection, denial/forgery/error/state-change rejection and review → publication →
activation ordering. `tests/agent-deployment.py` covers the gate through production
automatic and explicit deployment paths. These offline fixtures do not establish
native Polkit UX, protected live reviewer access or real activation continuity;
those require the separately authorized installation/acceptance run.
