# Deterministic updates

## Intentions

- Refresh supported package sources without AI cost or interactive approval.
- Preserve unrelated work and enforce exact source/build binding before boot staging.
- Keep progress visible and failures diagnosable without unbounded logs or retries.

The runner prepares committed `main` dependency updates from the supported fixed
publishers. It defers when the branch/source baseline or owned local files diverge.
The protected controller validates publisher policy and immutable baseline/profile,
builds the submitted source and binds the resulting closure before boot staging.
Routine updates invoke neither AI review nor graphical operator authentication.

Source manifests preserve safe internal file symlinks, including the Typst adapter
and package compatibility links. Literal targets and modes must match the approved
baseline; routine updates cannot add or retarget links. See the shared
[source contract and old-validator recovery](../../development/ai/agent/source-manifest.md).

`phoenix-update` prints short preparation phases and forwards controller build
output as it happens, including Nix lock preparation diagnostics. Long-running
Nix preparation commands emit a heartbeat after 30 seconds without output. Its
final result is readable text; `phoenix-update --json`
selects machine-readable stdout (progress remains on stderr). Each run retains a
log in the updater state directory: the latest five logs, at most 5MiB each (compacted to the latest 4MiB), with
the final result pointing to its log. Build failures retain their stage, code and
bounded diagnostic tail in `last-result.json`.

The latest failed committed candidate remains under `codex/updates/` with its
commit, branch and failure details in `failed-candidate.json`. Temporary worktrees
are removed. A later failure replaces that retained candidate; successful staging
clears it and normal cleanup removes obsolete service-authored branches. Existing
unchanged-candidate retry limits still apply; retention does not authorize staging
or bypass current baseline checks.

Temporary deferrals return success. If the same deferral reason persists for at
least 24 hours, `deferral.json` records its age and the result reports
`attentionRequired=true` with an actionable human message. That run exits with
failure so scheduled failure notifications also flag stalled updates. A changed
reason starts a new interval; a non-deferred result clears the interval.

Source and serialized JSON capacities are shared with deployment through
[transport.json](../../development/ai/agent/transport.json): 4MiB content and 32MiB
wire data. This allows JSON escaping without changing the separate AI input budget.
Capacity failures report `stage=source-transport` and
`code=source-capacity-exceeded` or `wire-capacity-exceeded`.

Run the disposable fixtures from the repository root with
`python3 modules/services/updates/tests/update-runner.py` and
`python3 modules/development/ai/agent/tests/agent-deployment.py`; no activation occurs.
The isolated `tests/notification-runtime.nix` factory takes `pkgs` and the actual
evaluated notifier `serviceConfig`. Its VM checks that the session socket remains
usable while adjacent runtime files stay hidden; it does not prove desktop delivery.
