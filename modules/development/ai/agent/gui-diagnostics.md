# Sandboxed desktop connection diagnostics

First check the managed sandbox phase and structured readiness conditions. A
`StartFailed` instance cannot execute the routing getter, so its connection
failure supplies no evidence about retained credentials. Resolve startup before
repeating the getter; never infer a token failure from an unavailable worker.

The retained gateway credential and desktop routing discovery are separate
stages. A saved or recently refreshed credential does not prove that the
credentialed request passed gateway inspection or that account discovery
succeeded. Do not clear the desktop profile or start browser sign-in solely
because routing discovery failed.

The HTTP worker reports a fixed stage and category without exception messages,
URLs, account values, request headers or response bodies. Approved diagnostics
are surfaced through the app-server account RPC and HTTP bridge's 502 response.
Unknown worker diagnostic values remain generic. A stream failure after headers
is journal-only and closes the response; it cannot replace an established HTTP
status.

- `request-validation`: malformed request, absent declared environment or CLI identity.
- `routing-discovery`: trusted account bootstrap fetch or metadata validation.
- `backend-request`: admitted backend request; HTTP rejection is distinguished.
- `response-stream`: interrupted or oversized response after headers.

`http-unauthorized` and `http-forbidden` identify the status, not its author:
the gateway or upstream can reject requests. `tls`, `transport` and `timeout`
identify transport failures without reflecting their possibly sensitive text.
Inspect the matching user relay journal and gateway policy/credential diagnostics
before choosing a remedy. No automatic retry, credential export or additional
network endpoint is introduced.

No-token acceptance fixtures: `tests/agent-gui-http.py`,
`tests/agent-gui-connection.py`, `tests/agent-gui.py` and
`tests/agent-gui-http-hook.cjs`. These verify safe protocol propagation and
credential boundaries. They do not establish live model/MCP connectivity,
credential validity or browser login success.

Source compatibility: the inspected installed native wrapper uses Codex CLI
0.160.0; the inspected desktop ASAR is 26.930.51102. Its bootstrap validates
workspace routing overrides against `NO_CONSTRAINT`, `us`, `us_cr`. Keep the
existing fixed origin and gateway inspection boundary; diagnosis is not evidence
that widening it would repair a connection.
