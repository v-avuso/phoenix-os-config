# Phoenix command ownership

- Human activation commands retain terminal `nixos-rebuild --sudo` authentication
  and progress. Agent deployment belongs to ai-broker's immutable client mapping;
  never redirect human wrappers or infer caller identity from environment markers.
- Test both routes together when changing command packaging: human selectors/tails
  reach rebuild; agent action/target/reason/selectors reach the controller client
  directly, with no arbitrary command mapping or legacy fallback.
