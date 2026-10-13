"""Shared context UI with a stub presenter; no dialogs or authentication."""
import importlib.util
import json
import io
import contextlib
import tempfile
import sys
from types import SimpleNamespace
from pathlib import Path
import unittest
from unittest import mock
ROOT = Path(__file__).resolve().parents[1]
def load(name, path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
class Presentation(unittest.TestCase):
    def setUp(self):
        self.auth=load("context_authorization", ROOT/"request.py")
        self.policy=self.auth.default_policy(False,1000,1000)
        self.config={"authorizationPolicy":self.policy,"authorizationPresentation":
                     {"module":str(ROOT/"presentation.py"),"program":"/fixed/zenity"}}
        self.request=self.auth.named("deployment.test",{"target":"metal"},"fixture","Check <b>this & that</b>")
        self.preflight={"ok":True,"id":"a"*32,"decision":"human"}
    def test_readable_escaped_body_and_default_cancel(self):
        with mock.patch("subprocess.run",return_value=mock.Mock(returncode=0)) as ui, mock.patch.object(self.auth,"audit") as audit:
            self.auth.explain(self.config,self.request,self.preflight,source="/workspace/project")
            argv=ui.call_args.args[0]
            self.assertEqual(argv[0],"/fixed/zenity")
            text=next(v.removeprefix("--text=") for v in argv if v.startswith("--text="))
            for value in ("phoenix-test", "deployment.test", "metal", "fixture", "/workspace/project", "Check &lt;b&gt;this &amp; that&lt;/b&gt;", "human", "disabled"):
                self.assertIn(value,text)
            self.assertIn("--default-cancel",argv)
            self.assertIn("--ok-label=Continue to authentication",argv)
            audit.assert_called_once()
            self.assertFalse(audit.call_args.kwargs["trusted"])
    def test_cancel_or_unavailable_fails_closed_with_static_audit(self):
        for result,category in ((mock.Mock(returncode=1),"context-cancelled"),(mock.Mock(returncode=2),"context-unavailable")):
            with mock.patch("subprocess.run",return_value=result),mock.patch.object(self.auth,"audit") as audit:
                with self.assertRaisesRegex(ValueError,category):
                    self.auth.explain(self.config,self.request,self.preflight)
                self.assertEqual(audit.call_args.kwargs["category"],category)
        with mock.patch("subprocess.run",side_effect=OSError("private error")),mock.patch.object(self.auth,"audit") as audit:
            with self.assertRaisesRegex(ValueError,"context-unavailable"):
                self.auth.explain(self.config,self.request,self.preflight)
            self.assertEqual(audit.call_args.kwargs["category"],"context-unavailable")
    def test_automatic_or_review_zero_ui_and_mismatched_decision_denied(self):
        with mock.patch("subprocess.run") as ui:
            self.policy["securityReviewEnabled"]=True
            self.auth.explain(self.config,self.request,dict(self.preflight,decision="security-review"))
            request=self.auth.named("admin.dmesg",{},"fixture","Read logs")
            self.auth.explain(self.config,request,dict(self.preflight,decision="automatic"))
            ui.assert_not_called()
            with self.assertRaises(ValueError): self.auth.explain(self.config,self.request,self.preflight)
            self.policy["diagnostics"]["admin.dmesg"]="denied"
            with self.assertRaises(ValueError): self.auth.explain(self.config,request,dict(self.preflight,decision="denied"))
            ui.assert_not_called()
    def test_disabled_display_fails_closed(self):
        self.config["authorizationPresentation"]=None
        with self.assertRaisesRegex(ValueError,"context-unavailable"),mock.patch("subprocess.run") as ui:
            self.auth.explain(self.config,self.request,self.preflight)
        ui.assert_not_called()
class ClientBinding(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        auth=load("binding_auth",ROOT/"request.py")
        self.policy=auth.default_policy(False,1000,1000)
        self.policy["diagnostics"]["admin.dmesg"]="human"
        self.config=dict(authorizationPolicy=self.policy,
            authorizationPresentation={"module":str(ROOT/"presentation.py"),"program":"/fixed/zenity"},
            operatorCommand=["/fixed/pkexec","/fixed/helper"],repo="/workspace/project",clientOnly=True,
            modelReviewEnabled=False,deploymentSocket="/fixture/socket")
        self.file=self.root/"config.json";self.file.write_text(json.dumps(self.config))
        self.preflight=dict(ok=True,id="a"*32,decision="human")
    def connection(self):
        connection=mock.MagicMock();connection.__enter__.return_value=connection
        connection.makefile.return_value=io.BytesIO(json.dumps(self.preflight).encode()+b"\n")
        return connection
    def test_admin_cancel_and_continue_preserve_fixed_helper_envelope(self):
        src=(ROOT.parent/"admin.py").read_text().replace("@authorizationClientConfig@",str(self.file)).replace("@authorizationLibrary@",str(ROOT/"request.py"))
        entry=self.root/"admin.py";entry.write_text(src)
        admin=load("binding_admin",entry)
        for response,context in ((1,True),(0,True),(0,False)):
            events=[]
            def run(argv,**kwargs):
                if argv[0]=="/fixed/zenity":
                    events.append("context");return SimpleNamespace(returncode=response)
                events.append("auth")
                self.assertEqual(argv,self.config["operatorCommand"])
                envelope=json.loads(kwargs["input"])
                self.assertEqual(envelope["request"]["reason"],"Inspect requested logs")
                self.assertEqual(envelope["preflightId"],self.preflight["id"])
                return SimpleNamespace(returncode=0,stdout=b'{"ok":true,"output":"fixture"}')
            with mock.patch.object(admin.socket,"socket",return_value=self.connection()), \
                 mock.patch.object(admin.Path,"exists",return_value=True), \
                 mock.patch("subprocess.run",side_effect=run),contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):
                if response:
                    with self.assertRaisesRegex(ValueError,"context-cancelled"):
                        admin.client(["dmesg"],"Inspect requested logs",authorization_context=context)
                else: admin.client(["dmesg"],"Inspect requested logs",authorization_context=context)
            self.assertEqual(events,["context"] if response else ["context","auth"] if context else ["auth"])
    def test_contained_context_returns_native_broker_guidance_without_ui(self):
        review=load("contained_review",ROOT.parent/"deploy-review.py")
        self.config["sandboxClient"]=True;self.file.write_text(json.dumps(self.config))
        stderr=io.StringIO()
        with mock.patch.object(sys,"argv",["review",str(self.file),"--action","test","--target","metal","--reason","Validate change","--authorization-context"]), \
             mock.patch.object(review.socket,"socket",return_value=self.connection()), \
             mock.patch.object(review,"snapshot") as snapshot,mock.patch.object(review,"run") as authenticate, \
             mock.patch("subprocess.run") as ui,contextlib.redirect_stderr(stderr),self.assertRaises(SystemExit):
            review.main()
        self.assertIn("ai-broker",stderr.getvalue())
        self.assertIn("host-authentication-required",stderr.getvalue())
        snapshot.assert_not_called();authenticate.assert_not_called();ui.assert_not_called()
    def test_context_cannot_generalize_security_override(self):
        review=load("override_context_review",ROOT.parent/"deploy-review.py")
        with mock.patch.object(sys,"argv",["review",str(self.file),"--reason","fixture","--authorization-context","--security-override","b"*64]), \
             mock.patch.object(review,"run") as authenticate,contextlib.redirect_stderr(io.StringIO()),self.assertRaises(SystemExit):
            review.main()
        authenticate.assert_not_called()

    def test_deployment_context_binds_frozen_request_and_cancel_never_authenticates(self):
        review=load("binding_review",ROOT.parent/"deploy-review.py")
        def snapshot(config,source):
            (source/"flake.nix").write_text("frozen fixture")
            return "a"*40,{"flake.nix":"frozen fixture"}
        for response,context in ((1,True),(0,True),(0,False)):
            events=[]
            def ui(argv,**kwargs):
                events.append("context");return SimpleNamespace(returncode=response)
            def authenticate(argv,**kwargs):
                events.append("auth")
                self.assertEqual(argv,self.config["operatorCommand"])
                request=json.loads(kwargs["data"])
                self.assertEqual(request["files"],{"flake.nix":"frozen fixture"})
                self.assertEqual(request["reason"],"Validate requested configuration")
                self.assertEqual(request["preflightId"],self.preflight["id"])
                return b'{"ok":true}'
            with mock.patch.object(sys,"argv",["review",str(self.file),"--action","test","--target","metal","--reason","Validate requested configuration"] + (["--authorization-context"] if context else [])), \
                 mock.patch.object(review.socket,"socket",return_value=self.connection()), \
                 mock.patch.object(review,"snapshot",side_effect=snapshot), \
                 mock.patch.object(review,"git",return_value=b"main"),mock.patch.object(review,"warn_deployment_diff"), \
                 mock.patch.object(review,"run",side_effect=authenticate),mock.patch("subprocess.run",side_effect=ui), \
                 contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):
                if response:
                    with self.assertRaisesRegex(ValueError,"context-cancelled"): review.main()
                else: review.main()
            self.assertEqual(events,["context"] if response else ["context","auth"] if context else ["auth"])

if __name__ == "__main__": unittest.main()
