{ pkgs, ... }:
let
  toml = pkgs.formats.toml { };
  workerConfig = toml.generate "phoenix-agent-codex.toml" {
    # OpenShell owns the enforceable outer boundary. Its seccomp policy blocks
    # nested Codex Bubblewrap user namespaces; no native fallback is permitted.
    # Commands allowed by OpenShell do not trigger Codex command Auto-review.
    sandbox_mode = "danger-full-access";
    approval_policy = "on-request";
    approvals_reviewer = "auto_review";
    # Preserve upstream reviewer policy. These are worker instructions, not a
    # substitute for a reviewer policy or deterministic access controls.
    developer_instructions = builtins.readFile ./review-codex-policy.md;
  };
in
{
  _module.args.phoenixAgentCodexConfig = workerConfig;
}
