# Agent epic backlog

## Intentions and estimate limits

Deliver everyday contained GUI/CLI work and low-friction, independently authorized
privileged operations while preserving native recovery, operator authentication,
immutable execution bindings and rollback. Prefer coarse responsibility boundaries
and the existing public interface; this backlog does not authorize implementation,
enablement, activation or a broader root command surface.

Completion ranges below are rough estimates of functionality delivered against the
stated scope, not test coverage, security assurance or probability of success.
Accepted primary workflows are 100% for that scope; broader acceptance is separate.
Remaining complexity uses Fibonacci points (1, 2, 3, 5, 8, 13), not hours or compute.
Ranges express integration/acceptance uncertainty; do not sum them as a forecast.
Sources are current declarations and the linked evidence documents, not fresh host
verification. Historical receipts do not identify today's running generation.

## Delivered baseline and remaining work

| Scope | Functionality estimate | Remaining complexity | Remaining outcome / acceptance |
| --- | --- | --- | --- |
| Primary shared GUI/CLI workflow | **100% primary accepted** | **0 known implementation** | Optional observation of archive/pin, broader history/UI behavior and relay sizes is not unfinished primary functionality; investigate only an actual regression. Preserve independent Native recovery. [Evidence](HANDOFF.md#evidence-limits-and-separate-unfinished-work). |
| Bounded authorization interface and seven diagnostics | **100% installed bounded scope** | **0 known implementation** | Revalidate mapped callers/denial paths only when identity or policy changes. Shared UID is a documented limit addressed by the distinct identity milestone, not a hypothetical diagnostic bug. [Contract](authorization/README.md). |
| Immutable deployment and optional security review | **90–95% broader workflow** (primary reviewed test/switch accepted) | 3–5 | Finish exact critical-action override/cancel UX end to end and contained/alternate-worktree caller acceptance. Reviewed test/switch and recovery passed; socket-peer VM and guest activation/rollback are separate passed slices. [Evidence](security-review.md), [handoff](HANDOFF.md). |
| Common agent authorization pipeline | **55–75% broader agreed scope** | 8–13 | Existing fixed interface is complete for its closed mappings; independent new-command review, immutable adapters and protected adaptive publication remain. This aggregate is a judgment, not a weighted sum. |
| OpenShell backend | **85–95% everyday scope** | 5–13 | Everyday contained backend works; full shutdown/status/log behavior remains a specific unresolved risk, tracked separately below. Keep native recovery and verify host/worktree boundaries when changed. |
| General privileged-command review and typed execution | **0% feature implemented** (shared plumbing is reuse) | 8–13 | Start from a real unsupported operation; add one immutable typed adapter, independent review and exact code/arguments/configuration/state/policy binding. Prove allow/deny/unavailable review, stale-state rejection and native human fallback end to end before opt-in use. Existing mappings do not implement this. [Intended extension](authorization/README.md#intended-extension-not-implemented). |
| Adaptive protected allowlist publication | **0%** | 8–13 | Define narrow capabilities and rationale, reviewed version-tracked publication, revocation and rollback. Worker must never directly mutate live authority; root cache stores exact approvals, not a growing rule registry. Keep OFF until representative trial and explicit approval. |
| Protected identity | **60–80%** | 8–13 | Prove distinct-UID launcher → OpenShell → broker, operator-owned retained auth/override, offline cutover/quiescence, workspace ACLs/history, GUI/TTY/model operation and recovery. Fixtures do not prove migrated live identity. [Acceptance](identity.md#acceptance). |
| Testing reservations | **65–85%** | 5–8 | Complete two-agent acquire/renew/complete/release, expiry/crash and stale-owner/baseline cases, authenticated admin recovery, and reservation-mediated real activation/rollback. Recorder systemd lifetime/exclusion passed; full Polkit/identity/live workflow did not. Expiry must not activate or roll back. [Evidence](reservations.md). |
| Disruption guard | **55–75%** | 5–8 | Trial concrete desktop unit inspection, typed uncertainty and fresh exact operator exception through the actual activation helper. It cannot prove absence of arbitrary activation-shell disruption. [Boundary](disruption.md). |
| Native authorization explanation | **70–90%** | 3–5 | Verify native GUI presentation/cancel/auth flow and contained host guidance; weigh extra Continue click against useful context. It supplies no authority and is separate from critical security override. [Usage](authorization/README.md#native-explanation-experimental-default-off). |
| Shutdown ordering, status, logs and cleanup | **40–65%** | 8–13 | Identify the exact stalled await before any Rust repair; finish ordinary-stop terminal/attached-transport cleanup and user-manager teardown. Ordered guest A/B mitigated the combined-stop delay, but is not full acceptance. Verify final supervisor-event delivery with gateway alive and compare independent persistent captures for combined stop; upstream's gateway tail is memory-only. Preserve administrative report-skip semantics and resource cgroups. [Contracts and evidence](shutdown-acceptance.md). |
| Reviewer cost visibility (optional extension) | Not estimated; no agreed additional feature scope | 3–5 | Expose bounded nonsecret usage/limit outcomes and distinguish controller invocations from model-internal requests/tokens. Current input/output/time/invocation bounds exist; internal API requests and cumulative tokens lack hard caps. Establish any new recurring budget before widening review; routine updates stay zero AI. [Limits](security-review.md). |
| Managed-worktree sandbox access | **0% dedicated configured support** (selectors already exist) | 3 | Default mounts omit `~/.codex/worktrees`. Configure a narrow approved worktree root, not the whole `.codex` profile; prove registered immutable source selection and contained caller access without widening credentials/history access. Native selector support alone does not establish this path. [Source selection](AGENTS.md#source-selection). |
| Coarse module controls and composition | **40–60%** | 5–8 | Design and check supported independent disable combinations at responsibility boundaries; document dependencies and native recovery. Add only missing useful controls, not a boolean per helper. Review-off must select human authentication, not automatic approval, and retain the controller, immutable binding and rollback. Current inventory follows below. |
| File organization (optional extension) | Not estimated; no agreed refactor scope | 3–5 | Optional: move cohesive ownership groups only when navigation/maintenance benefit exceeds migration and validation cost; preserve public imports and colocated fixtures/docs. Architecture table already explains ownership; no one-module-per-small-feature rule. |

Code-quality review is explicitly deferred/out of this epic's deployment-security
remit. Do not widen security review into routine quality review or package-content
review; revisit as a separately scoped operator request.

## Actual switch inventory

Declared repository selection is not a new runtime inspection. `../default.nix`
imports the composition; absence of an enable option means import-controlled, not
independently toggleable. Removing an import can break required module arguments.

| Responsibility | Existing control | Reusable default / repository selection | Gap |
| --- | --- | --- | --- |
| Authorization policy/core public interface | `phoenix-authorize` gate (`ai-broker` alias); no core `enable`; imported by broker and deployment | Installed by composition | No supported overall enable/disable contract. |
| Diagnostic broker | `phoenix.authorization.automaticDiagnostics.enable` defaults true; no broker `enable`; `phoenix.authorization.diagnostics.<name>` is `automatic`, `human` or `denied` | Seven diagnostics default automatic; flag OFF defaults human and forbids automatic overrides | Denying operations does not disable broker installation. |
| Deployment controller | No deployment-engine `enable` | Installed by composition | Review switch does not remove authentication/controller/rollback. |
| Security review | `services.phoenixDeployment.securityReview.enable`; legacy `modelReview.enable` alias | OFF / **ON** | General command review and adaptive publication have no implementation or switches. |
| OpenShell runtime | No runtime `enable` | Imported; installs runtime/services | No independent supported disable contract; identity/shutdown options alter it. |
| Bubblewrap GUI | No GUI `enable` | Imported | Shared-state switch does not remove GUI or its relays. |
| Shared GUI state | `phoenix.agent.gui.sharedState.enable` | OFF / **ON** | Broader behavior observation remains separate. |
| Protected identity | `phoenix.agent.identity.enable` | OFF / OFF | Isolated full-workflow acceptance pending. |
| Reservations | `phoenix.agent.reservations.enable` | OFF / OFF | Full workflow/recovery acceptance pending. |
| Shutdown ordering | `phoenix.agent.shutdownOrdering.enable` | OFF / OFF | Shutdown/status/log acceptance incomplete. |
| Disruption guard | `services.phoenixDeployment.disruptionGuard.enable` | OFF / OFF | Actual desktop/helper/native exception trial pending. |
| Explanation | `phoenix.authorization.explanation.enable` | OFF / OFF | Isolated native GUI acceptance pending. |

Inventory sources: [composition](../default.nix), [runtime](default.nix),
[broker](broker.nix), [authorization](authorization/default.nix),
[deployment](deployment.nix), [review options](security-review.nix), [GUI](gui.nix),
[identity](identity.nix), [reservations](reservations.nix),
[shutdown](shutdown-ordering.nix). No switches are added by this document.

## Recommended authorization sequence

1. Keep `ai-broker --task … --reason … -- COMMAND …` as the single agent-facing
   entry point. Preserve human terminal commands and native sudo/authentication;
   do not intercept global sudo or present Codex auto-review as OS authority.
2. Route deployment directly to its existing diff review/controller, without a
   redundant generic-command AI pass. Reuse installed deterministic decisions for known safe typed operations and
   exact protected approval-cache matches. Keep normal deployment review separate
   from diagnostic policy and routine deterministic updates.
3. For a supported typed adapter's unknown request instance, use an independent
   bounded reviewer, then execute only the same frozen code and validated inputs.
   Denial, unavailable review, unbindable mutable state or unsupported command
   families go to explicit native human fallback. Never promote arbitrary strings
   to an unrestricted root shell. A universal arbitrary-root-shell reviewer is a
   separate high-complexity (13-point initial exploration; total scope unknown) ambition, not the next milestone.
4. Trial one real operation with fast fixtures, then disposable VM root/socket/
   systemd semantics, then agreed host acceptance. Keep generic review and adaptive
   publication OFF until their representative trial and operator approval. Only
   afterward consider narrowly bounded protected policy updates through reviewed
   deployment; verify rollback, revocation and stale-state failure.

For each remaining milestone record representative success/failure evidence and
explicit omissions in its owning document. Use [HANDOFF](HANDOFF.md) for current
continuation, not a second task diary here. Integration/host acceptance must select
one worktree and immutable source, coordinate shared system state and retain an
agreed recovery path; docs-only backlog work requires no activation.
