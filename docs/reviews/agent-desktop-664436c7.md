# Reviewed sandbox desktop dependency evidence

The full 41,731-byte evidence is preserved in approved commit
`ed913e5497192dff0a3d8165798380856d409177`, at this same path, and in its
activated immutable source:
`/nix/store/azrjjgc03z1r4c0qxj069ipkqs4vs8h6-source/docs/reviews/agent-desktop-664436c7.md`.
Evidence SHA-256: `fa8452cdf97d44852b0c383022fcc66e4f9d9412f54de4add0b3947e2870c5d7`.

Retrieve the committed artifact with:

```sh
git show ed913e5497192dff0a3d8165798380856d409177:docs/reviews/agent-desktop-664436c7.md
```

It contains exact recipe/runtime excerpts, dependency identities and relevant
diffs for `8e3f6b4b665b9e9c219b286cf57b89f516bb0bd8` →
`664436c7d0f3f7919a626c25999424f92bf4a044`. Independent comparison matched
all source excerpts, hashes and package pins; one final unchanged blank diff
context line was normalized. The controller reviewed that evidence together
with the full configuration and built closure before approving the switch.

This index avoids duplicating vendor code in every future bounded review.
It never authorizes deployment; new dependency changes need fresh code evidence
and a source/closure-bound verdict. See [acceptance](../AGENT_SANDBOX_ACCEPTANCE.md)
and the [operating guide](../AGENT_SANDBOX.md).
