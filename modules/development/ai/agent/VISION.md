# Portable security reviews — proposals

## Intentions

Make independent review evidence portable and independently verifiable while
preserving operator control, bounded review cost and target-specific deployment
authorization. Everything below is optional future work, **not implemented**;
the [current protected checkpoint mechanism](security-review.md#baseline-and-checkpoint-reuse)
remains authoritative.

## Proposed capabilities

- Cryptographically signed attestations bound to immutable Git commit/tree
  content, with an exact content/mode manifest for uncommitted changes. Keep
  reviewer identities and signing authority outside ordinary repository and
  Codex-worker write access.
- Record reviewer/model identity, version, reasoning effort, scope, timestamp,
  policy and reviewed content. Distinguish independent verdicts, explicit human
  trust seeds and overrides; do not infer their origin from an approval badge.
- Reuse valid source attestations across branches, worktrees and machines;
  keep portable source approval separate from target-specific source/build
  deployment authorization. Review residual changes since a trusted baseline,
  including uncommitted edits and integration effects.
- Offer policy-controlled review at commit, push or merge time, with explicitly
  unreviewed commits allowed where appropriate. Centrally configure review tiers,
  minimum standards and cost limits before adding recurring automation.
- Consider file/component audit records and periodic stronger-model reviews.
  Explore Git-history presentation, such as security-review badges in SourceGit,
  with access to the underlying verified evidence and its scope.
- Evaluate maintained standards/tooling before custom design: [in-toto](https://in-toto.io/),
  the [SLSA attestation model](https://slsa.dev/spec/v1.2/attestation-model) and
  [Sigstore](https://docs.sigstore.dev/about/overview/). Evaluate fit, identity,
  verification and lifecycle costs; signatures authenticate statements, not the
  correctness of the review. No architecture or standard is selected here.

## Security considerations

- A badge alone is not proof of authorization. Ordinary user-writable Git
  metadata is not a sufficient trust boundary.
- File-level approval does not imply component or system-wide approval.
  Reuse must account for dependencies, surrounding code, integration, security
  policy and the review's stated scope; changed context can require new review.
- Define trusted issuers, key protection, revocation and verifier policy before
  accepting portable evidence. Separate evidence storage from authority.
- A manual `phoenix-switch` must never forge independent approval. Preserve the
  distinction between activation provenance, operator authentication, explicit
  human trust and an independent reviewer verdict.
