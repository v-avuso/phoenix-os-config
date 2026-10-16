"""Authorization requests through fixed existing Phoenix clients; no shell."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import sys

COMMANDS = {"phoenix-test", "phoenix-switch", "phoenix-boot", "phoenix-admin", "phoenix-command"}

def prepare(config, argv):
    spec = importlib.util.spec_from_file_location("phoenix_authorization", config["library"])
    authorization = importlib.util.module_from_spec(spec); spec.loader.exec_module(authorization)
    parser = argparse.ArgumentParser(prog="phoenix-authorize", allow_abbrev=False,
        description="Use phoenix-authorize (alias: ai-broker) --reason PURPOSE [--task TASK] -- phoenix-test|switch|boot|admin|command ...; reasons are context, not authority")
    parser.add_argument("--reason", required=True, action="append")
    parser.add_argument("--task", action="append")
    if argv == ["--help"]:
        parser.parse_args(argv)
    if "--" not in argv:
        raise ValueError("structured command arguments after -- are required")
    split = argv.index("--")
    options = parser.parse_args(argv[:split]); command = argv[split + 1:]
    if len(options.reason) != 1 or (options.task is not None and len(options.task) != 1):
        raise ValueError("supply one reason and at most one task")
    reason = authorization.text(options.reason[0], 300, "nonsecret reason")
    task = authorization.text(options.task[0] if options.task else "ai-broker", 100, "task")
    if (not 1 <= len(command) <= 16 or sum(len(arg.encode()) for arg in command) > 16384
            or any(len(arg) > 4096 for arg in command)):
        raise ValueError("command arguments exceed bounds")
    for arg in command:
        authorization.text(arg, 4096, "command argument")
    name, *args = command
    if name not in COMMANDS or name not in config["commands"]:
        raise ValueError("unsupported installed command")
    executable = config["commands"][name]
    if not isinstance(executable, str) or not Path(executable).is_absolute():
        raise ValueError("invalid installed client")
    installed = authorization.policy({"authorizationPolicy":config["policy"]})
    forwarded = []
    deployment = []
    if name == "phoenix-command":
        import re
        identifier = args[1:] if args[:1] == ["--human-override"] else args
        if len(identifier) != 1 or not re.fullmatch(r"[a-z][a-z0-9-]{0,63}", identifier[0]):
            raise ValueError("select one installed operation identifier")
        forwarded = args
    elif name == "phoenix-admin":
        # Options belong to this adapter; the client receives canonical semantic args.
        reservation = []
        if args[:1] == ["--reservation-file"]:
            if len(args) < 3 or not Path(args[1]).is_absolute():
                raise ValueError("invalid diagnostic reservation path")
            reservation, args = args[:2], args[2:]
        request = authorization.diagnostic(args, reason, task)
        authorization.validate(request, installed)
        forwarded = reservation + authorization.diagnostic_argv(request)
    else:
        deployment = ["--target", installed["target"], "--action", name.removeprefix("phoenix-")]
        seen = set()
        while args:
            flag = args.pop(0)
            if flag not in {"--branch", "--worktree", "--reservation-file"} or flag in seen or not args:
                raise ValueError("unsupported or duplicate deployment option")
            value = args.pop(0)
            if value.startswith("-") or (flag != "--branch" and not Path(value).is_absolute()):
                raise ValueError("invalid deployment selector or reservation path")
            if flag == "--branch" and len(value) > 256:
                raise ValueError("branch exceeds bounds")
            seen.add(flag); forwarded.extend([flag, value])
        if {"--branch", "--worktree"}.issubset(seen):
            raise ValueError("choose one source selector")
        request = authorization.named("deployment." + name.removeprefix("phoenix-"),
                                      {"target":installed["target"]}, task, reason)
        authorization.validate(request, installed)
    context = ["--authorization-context"] if name != "phoenix-command" and config.get("explanationEnabled", False) else []
    return [executable, *deployment, "--task", task, "--reason", reason, *context, *forwarded]

def main():
    config = json.loads(Path(sys.argv[1]).read_text())
    # The packaged entry point fixes this immutable config. Existing clients own
    # root preflight, peer admission, authentication, source freeze and execution.
    command = prepare(config, sys.argv[2:])
    os.execv(command[0], command)

if __name__ == "__main__":
    try: main()
    except (ValueError, KeyError, OSError):
        raise SystemExit("ai-broker: invalid request or unavailable installed client") from None
