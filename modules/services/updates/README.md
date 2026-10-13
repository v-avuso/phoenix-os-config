# Deterministic updates

The runner prepares committed `main` dependency updates from the supported fixed
publishers. It defers when the branch/source baseline or owned local files diverge.
The protected controller validates publisher policy and immutable baseline/profile,
builds the submitted source and binds the resulting closure before boot staging.
Routine updates invoke neither AI review nor graphical operator authentication.

Source and serialized JSON capacities are shared with deployment through
[transport.json](../../development/ai/agent/transport.json): 4MiB content and 32MiB
wire data. This allows JSON escaping without changing the separate AI input budget.
Capacity failures report `stage=source-transport` and
`code=source-capacity-exceeded` or `wire-capacity-exceeded`.

Run the disposable fixtures with `python tests/update-runner.py` and
`python tests/agent-deployment.py` from the repository root; no activation occurs.
