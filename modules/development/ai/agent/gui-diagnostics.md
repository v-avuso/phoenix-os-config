# Sandboxed desktop connection diagnostics

## Intentions

Keep the contained desktop usable with its retained gateway login and declared
projects/history. Diagnose startup, account metadata and routing separately;
preserve native profiles, credential ownership and the fixed inspected endpoint
boundary. Public routing metadata must not grant credentials or entitlements.

## Diagnosis

First compare the recorded instance with the revision derived from the installed
launcher image/policy/mount paths, then check its phase and structured readiness
conditions. Activation can change the desired revision while the marker still
identifies an older failed instance. A current `StartFailed` instance cannot
execute the routing getter, so its connection failure supplies no evidence about retained credentials. Resolve startup before
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

[Codex 0.160.0 account processor](https://github.com/openai/codex/blob/rust-v0.160.0/codex-rs/app-server/src/request_processors/account_processor/workspace_routing.rs)
resolves native workspace routing before returning `account/read` metadata. The relay repairs only its exact internal-error routing
failure/401 vocabulary using the existing mediated account discovery and `/me`.
Both must succeed and identify the configured selected account; failed mediation
returns the bounded diagnostic, never an authenticated result. Other native
errors are preserved. The response uses the pinned account/plan/routing schema;
public metadata is not a credential or a fabricated entitlement.

The pinned Community wrapper supplies `--class=$CODEX_LINUX_APP_ID`, and Hyprland
0.55.4's packaged example supports `suppress_event = "maximize"`. The generated
and active Lua include the contained-class rule. Real contained-window behavior
and browser sign-in presentation still require a supervised GUI acceptance check;
source inspection and no-GUI protocol trials do not establish them.

## Acceptance boundary

A controlled no-GUI comparison with the existing retained-auth launcher confirmed
that the installed relay returned the guarded native routing error while
`getAuthStatus` succeeded. The feature relay returned schema-valid account
metadata and routing through the same mediated discovery, with external auth
still usable. Fixtures also reject mediation denial, account ambiguity, malformed
metadata and unrelated native errors. These establish the bootstrap RPC repair;
packaged deployment and actual contained-window/login presentation remain pending.
