# Frozen source manifests

## Intentions

Preserve the exact source reviewed and built by the protected deployment flow,
including legitimate repository links, without following mutable paths or adding
authority to routine updates.

## Source contract

[`source-manifest.py`](source-manifest.py) is shared by the immutable deployment
client, root controller and updater. Nix packages it independently and passes its
immutable path explicitly; its bytes participate in the security-policy digest.
Existing checkpoints cannot silently authorize a changed validator.

The existing `files`/`modes` dictionaries carry UTF-8 content and Git modes:
`100644`/`100755` for regular files, `120000` for links. A link's content is its
literal target text, never the contents reached through the link. Review diffs
include its path, mode and target. Store verification compares both dictionaries.
`flake.nix` and `flake.lock` must remain regular files.

Only direct relative links to regular files in the same complete frozen manifest
are supported. Working-tree snapshots additionally require targets to be in the
Git index. Absolute/external/escaping/dangling/directory links, link chains and
cycles, submodules, ambiguous target spellings and file/directory collisions are
rejected. Relative `..` components are allowed only while remaining within real
manifest directories. No target is dereferenced to admit a link.

Mutable reads use directory descriptors, `O_NOFOLLOW`, bounded reads and inode/
metadata rechecks. Validation uses captured data, rather than checking a live
target and subsequently following it. Reconstruction validates the complete graph
before writing into a private empty directory, creates regular files first and
links last, and retains builder-readable permissions under the root service umask.
The store copy is compared again before build. This freezes captured content;
it does not claim a transactional snapshot of concurrent edits across all files.

Routine updates retain their existing exact baseline/profile, publisher and
source/mode rules. They can neither add nor retarget links and invoke no AI or
new operator authentication. Configuration deployments retain normal AI review
or their existing explicit authenticated human policy.

## One-time recovery from an older validator

The older installed client rejects links before submission; its controller also
rejects the current linked baseline. Removing the first check, editing checkpoint
records, changing review policy, trusting a branch name, or submitting a caller
closure to the broker is not a recovery procedure.

Prepare and validate the entire patch without activation. Freeze the intended
Git-visible source with the repaired snapshot client, add that vetted temporary
tree to the Nix store, and build the metal closure from that exact immutable
source as the ordinary user. Do not copy the checkout with `path:.`. Check the
closure's `etc/phoenix-agent/activated-source` against the frozen source and record
the exact source, closure, current runtime and boot profile in the operator handoff.
Keep the candidate closure GC-rooted until the decision is complete.

Activation is not security approval. `choose_checkpoint` now considers only
root-owned same-policy/target approvals and fails closed when none exist. A native
`nixos-rebuild switch` alone is therefore insufficient. Commit metadata is not
needed to bind an immutable deployment, but the updater compares committed `main`
with the installed source: commit the exact intended tree before the first update.

The on-demand [`recovery/source-bootstrap.nix`](recovery/source-bootstrap.nix)
factory packages a zero-argument immutable recovery helper, with no installed
policy grant or recurring service. Its descriptor binds the installed configuration
and policy, expected runtime/profile/baseline, a specific previous approved source
and closure, and the exact candidate source/closure/new policy/commit. The helper:

1. Requires fresh native operator authentication and unchanged authorization,
   target, identities and review settings; takes the existing deployment lock.
   It refuses enabled reservations rather than inventing reservation authority.
2. Verifies the previous source/closure against its protected old-policy approval
   record and checks all immutable closure/source bindings. Journal provenance
   alone cannot satisfy this root check. A retained denial of the candidate blocks it.
3. Uses the production isolated worker and retained reviewer to review the complete
   old-approved → candidate diff, with normal two-call/context bounds and no retries.
   Old-policy approval is comparison evidence, never new-policy approval reuse.
4. Validates the exact verdict, rechecks runtime/profile/policies under the activation
   guard, and publishes the candidate's new-policy checkpoint with the existing
   root-owned API. A denial is retained and never converted into approval.
5. Calls the existing bound activation engine, preserving its transient helper,
   final checks, profile handling, rollback and disruption behavior.

An independent review of the final frozen source (including this recovery code)
and explicit operator approval of the exact helper are required before invoking:

```sh
/run/wrappers/bin/pkexec --disable-internal-agent /nix/store/EXACT-RECOVERY/bin/phoenix-source-recovery
```

The coordinator supplies the exact immutable executable after its nonprivileged
`phoenix-source-recovery-inspect` check. That inspection cannot confirm protected
checkpoint records; the authenticated helper must do so before review/publication.
Do not use raw activation commands, edit checkpoint files, disable review, or call
`trust-active` to conceal an unreviewed transition. No credential/profile copying
or permanent authorization change is involved. A busy deployment, missing old
approval, failed review or changed binding stops recovery.

After activation, verify the installed checkpoint under the new policy, runtime
and boot-profile sources, controller refresh and committed `main` content/modes.
Then run a real `phoenix-update` through its ordinary supported path and inspect
its result and journal. The unchanged persistent timer needs no special action.
Subsequent changed agent sources must still enter protected review; activation of
an unreviewed source without a checkpoint cannot establish a trusted diff baseline.

## Verification

Run `tests/source-manifest.py`, `tests/agent-review.py`,
`tests/agent-deployment.py`, `tests/source-bootstrap.py` and
`../../../services/updates/tests/update-runner.py`
with Python from the repository root (using their repository-relative paths).
Fixtures exercise captured links, unsafe graphs, parent redirection, retarget races,
controller umask, literal mode/target review, exact checkpoints and AI-free routine
updates. Store/build/model/activation doubles are explicit; they do not establish
host activation or a real scheduled update's success.
