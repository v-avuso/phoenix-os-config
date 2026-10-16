"""Adapter contracts with fixed disposable clients; no auth or deployment."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
class Broker(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name); self.record = self.root / "record"
        client = self.root / "client"
        client.write_text("#!" + sys.executable + "\nimport os,sys,json\nfrom pathlib import Path\nPath(os.environ['RECORD']).write_text(json.dumps(sys.argv[1:]))\n")
        client.chmod(0o755)
        self.config = self.root / "config.json"
        self.config.write_text(json.dumps(dict(library=str(ROOT / "request.py"),
            policy=dict(version=1,securityReviewEnabled=False,clientUid=os.getuid(),operatorUid=os.getuid(),
              updaterUid=os.getuid(),target="metal",diagnostics={"admin."+n:"automatic" for n in
              ("kernel-journal","dmesg","trace-summary","trace-format","service-status","wakeup-get","wakeup-set")},
              wakeupDevices=["0000:00:14.0"],statusServices=["NetworkManager.service"]),
            commands={name:str(client) for name in ("phoenix-test","phoenix-switch","phoenix-boot","phoenix-admin","phoenix-command")})))
    def run_adapter(self, *args):
        return subprocess.run([sys.executable,"-I",str(ROOT / "ai-broker.py"),str(self.config),*args],
            env=dict(os.environ,RECORD=str(self.record)),capture_output=True,text=True)
    def test_registered_command_identifier_and_explicit_override_only(self):
        result=self.run_adapter("--reason","Inspect fixed operation","--","phoenix-command","identity")
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(json.loads(self.record.read_text()),["--task","ai-broker","--reason","Inspect fixed operation","identity"])
        result=self.run_adapter("--reason","Explicit operator request","--","phoenix-command","--human-override","identity")
        self.assertEqual(result.returncode,0,result.stderr)
        for extra in (("identity","extra"),("identity | sh",),("--human-override","identity","extra")):
            self.assertNotEqual(self.run_adapter("--reason","bounded","--","phoenix-command",*extra).returncode,0)

    def test_required_reason_and_closed_command_options(self):
        for args in (("--","phoenix-test"), ("--reason"," ","--","phoenix-test"),
          ("--reason","x","--","sh","-c","phoenix-test"),
          ("--reason","x","--","sudo","nixos-rebuild","switch"),
          ("--reason","x","--","phoenix-test","--sudo"),
          ("--reason","x","--","phoenix-test","--target","vm"),
          ("--reason","x","--","phoenix-test","--action","switch"),
          ("--reason","x","--","phoenix-test","|","sh"),
          ("--reason","x","--","phoenix-test","--reason","override"),
          ("--reason","x","--","phoenix-test","--option","x","y"),
          ("--reason","x","--","phoenix-admin","service-status","unknown.service"),
          ("--reason","x","--","phoenix-admin","dmesg",";"),
          ("--reason","x"*301,"--","phoenix-test"),
          ("--reason","line\nbreak","--","phoenix-test"),
          ("--reason","x","--reason","override","--","phoenix-test"),
          ("--reason","x","--task","bad!","--","phoenix-test"),
          ("--reason","x","--","phoenix-test","--worktree","relative"),
          ("--reason","x","--","phoenix-test","--branch","one","--worktree","/two")):
            result=self.run_adapter(*args)
            self.assertNotEqual(result.returncode,0)
            self.assertFalse(self.record.exists())
    def test_explanation_option_carries_static_flag_only_when_enabled(self):
        config=json.loads(self.config.read_text());config["explanationEnabled"]=True
        self.config.write_text(json.dumps(config))
        result=self.run_adapter("--reason","Validate change","--","phoenix-test")
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(json.loads(self.record.read_text()),["--target","metal","--action","test","--task","ai-broker","--reason","Validate change","--authorization-context"])
        self.record.unlink()
        result=self.run_adapter("--reason","Validate change","--","phoenix-test","--authorization-context")
        self.assertNotEqual(result.returncode,0)
        self.assertFalse(self.record.exists())

    def test_each_agent_activation_uses_fixed_action_and_installed_target(self):
        for action in ("test", "switch", "boot"):
            result=self.run_adapter("--task","fixture","--reason","Requested deployment","--",
                                    "phoenix-"+action,"--worktree",str(self.root))
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertEqual(json.loads(self.record.read_text()),
                ["--target","metal","--action",action,"--task","fixture","--reason","Requested deployment","--worktree",str(self.root)])

    def test_missing_deployment_mapping_never_uses_legacy_or_path(self):
        config=json.loads(self.config.read_text())
        config["commands"]={"phoenix-admin":config["commands"]["phoenix-admin"]}
        self.config.write_text(json.dumps(config))
        result=self.run_adapter("--reason","Validate change","--","phoenix-test")
        self.assertNotEqual(result.returncode,0)
        self.assertFalse(self.record.exists())

    def test_fixed_clients_receive_exact_task_reason_and_args(self):
        result=self.run_adapter("--task","fixture","--reason","Inspect requested change","--",
                                "phoenix-test","--branch","feature")
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(json.loads(self.record.read_text()),["--target","metal","--action","test","--task","fixture","--reason","Inspect requested change","--branch","feature"])
        result=self.run_adapter("--reason","Inspect current logs","--","phoenix-admin","kernel-journal","42")
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(json.loads(self.record.read_text()),["--task","ai-broker","--reason","Inspect current logs","kernel-journal","42"])
        result=self.run_adapter("--reason","Reserved diagnostic","--","phoenix-admin",
                                "--reservation-file","/private/task.json","dmesg")
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(json.loads(self.record.read_text()),["--task","ai-broker","--reason","Reserved diagnostic",
                         "--reservation-file","/private/task.json","dmesg"])

if __name__ == "__main__": unittest.main()
