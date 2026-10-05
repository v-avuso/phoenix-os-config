# Stable update preparation

This directory contains an isolated policy/candidate component. It is not
imported by the running configuration, and no automatic updater is installed
or running. The candidate service declaration is disabled by default and also
remains unimported. The current protected controller rejects boot requests, so
this component cannot claim that a generation was staged or activated.

The intended cadence is daily with a three-day default cooldown. The initial
one-day group is `firefox`, `codex-desktop`, and `codex-cli`; there is no
14-day group. Ages apply to first observation of an upstream stable snapshot,
not to the release date of each package. An independent observer must verify
publication, exact refs, source integrity, and package-specific release
evidence before passing pins to the candidate component. A revision string
alone is not proof of publication. The one-day group is an optional wait-time
preference; normal stable updates still carry upstream security fixes through
the default three-day path.

Policy holds take precedence over cooldowns. A hold records a reason, an exact
pin, and a review date; the date only prompts review and never releases it.
Optional `resumeAtVersion` enables a narrowly conditional release. For example,
a hypothetical Firefox fix might use `resumeAtVersion = "142.0"` after credible
stable-release evidence identifies that threshold. A caller must verify the
actual payload version is stable, in the same release family, and at or above
the threshold for each exact candidate revision. Policy code accepts only
that caller-verified app/threshold/revision decision; it does not compare
versions. Unknown or mismatched evidence remains held. Omit the field or set it
to `null` for an indefinite hold. Remove a hold deliberately from policy after
review; never treat the resume threshold as proof that the issue is fixed.

The source map is deliberately explicit:

| Application | Pinned source | Package interface / limitation |
| --- | --- | --- |
| `firefox` | independent `nixpkgs-updates-fast` input on `nixos-26.05` | Requires final Home Manager `programs.firefox.package` wiring; profiles and policies stay intact. |
| `codex-desktop` | `codex-desktop-linux` accepted source for Native | Sandboxed remains separately pinned as `codex-desktop-sandbox`; preserving both runtime interfaces and reviewed source evidence is integration work. |
| `codex-cli` | no input pin in this component | Requires a conventional exported package attribute consumed by `nix-update`; no handwritten Nix expression rewriting is provided. |

Adding an age cohort requires a named, independently pinned source and package
mapping. Recognizing an application identifier in policy does not mean its
adapter exists. The current default lock command persists exact selected
revisions through Nix and checks that only the selected input closures change;
it does not hand-edit `flake.lock`.

Candidate preparation starts only from an exact protected approved commit
whose tracked file contents match the immutable approved source. It uses a
temporary Git worktree and commits only allowlisted updater paths; it does not
change the normal checkout's HEAD, index, or files. Unrelated dirty and staged
edits stay intact. A dirty affected file, changed main HEAD, failed
observation, invalid lock graph, or failed controller request cannot be
reported as staged. Even after a successful controller response, the isolated
commit still requires coordinator-owned merge-back, so ordinary
`phoenix-switch` does not yet include it. Merge-back must revalidate current
committed policy and holds before applying a candidate; a newly committed hold
invalidates a candidate even without a text conflict.

The Community source adapter must additionally validate the exact stable
payload manifest and, for the exact source revision, successful completed
GitHub Actions contexts `source-and-node`, `rust`, `nix`, and
`official-linux-gate`. Missing, pending, failed, or changed contexts keep the
current Community version. These public checks are publisher acceptance
evidence, not malware proof or a substitute for inspecting source changes and
containment behavior. The current component validates supplied payload/check
records but does not fetch them or perform the bounded pagination itself.

Before this can become the requested normal workflow, integration must provide
the verified daily observer and policy/hold reload, the three package adapters,
fast Nixpkgs and Firefox wiring, CLI package metadata, Native/Sandbox source
review, current-checkout policy revalidation and safe merge-back, controller
boot support with staging failure restoration, and final module import. The
candidate service has no request producer yet, and its controller interface is
intentionally fixed to the existing socket, `action = "boot"`, and a fixed
updater reason. No reboot, garbage collection, cooling change, vulnerability
scanner, or automatic install is implemented here.
