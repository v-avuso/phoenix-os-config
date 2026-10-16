"""Fixed client routing/capacity with explicit socket and native-auth doubles."""
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import threading
import unittest
ROOT=Path(__file__).resolve().parents[1]
class Client(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup);self.root=Path(tmp.name)
        self.record=self.root/'record';self.authority=self.root/'authority'
        self.authority.write_text(json.dumps(dict(registry=dict(entries=dict(identity=dict(executable='/immutable/identity',arguments=['-u']))))))
        helper=self.root/'helper.py';helper.write_text("import json,sys\nfrom pathlib import Path\nPath("+repr(str(self.record))+").write_text(sys.stdin.read())\nprint(json.dumps(dict(ok=True,exitCode=0,stdout='authenticated\\n',stderr='')))\n")
        self.critical_record=self.root/'critical-record'
        critical=self.root/'critical.py'
        critical.write_text(helper.read_text().replace(repr(str(self.record)),repr(str(self.critical_record))))
        self.socket=str(self.root/'socket');self.settings=self.root/'config'
        self.settings.write_text(json.dumps(dict(socket=self.socket,authority=str(self.authority),operatorCommand=[sys.executable,str(helper)],criticalCommand=[sys.executable,str(critical)])))
    def run_client(self,response=None,override=False):
        if response is not None:
            listener=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM);listener.bind(self.socket);listener.listen()
            def serve():
                with listener:
                    connection,_=listener.accept()
                    with connection:
                        while connection.recv(4096):pass
                        connection.sendall(json.dumps(response).encode())
            thread=threading.Thread(target=serve);thread.start()
        args=[sys.executable,'-I',str(ROOT/'command-client.py'),str(self.settings),'--task','fixture','--reason','bounded request']
        if override:args.append('--human-override')
        result=subprocess.run([*args,'identity'],capture_output=True,timeout=10)
        if response is not None:
            thread.join(5);Path(self.socket).unlink()
        return result
    def test_human_decision_uses_normal_native_route(self):
        result=self.run_client(dict(ok=False,code='command-human-authentication-required'))
        self.assertEqual(result.returncode,0);self.assertEqual(result.stdout,b'authenticated\n');self.assertTrue(self.record.exists())
    def test_denial_shows_sanitized_reason_without_automatic_auth(self):
        result=self.run_client(dict(ok=False,code='command-review-denied',summary='Unsafe\x1b\u202e path'))
        self.assertEqual(result.returncode,1);self.assertFalse(self.record.exists());self.assertIn(b'Unsafe path',result.stderr);self.assertNotIn(b'\x1b',result.stderr)
    def test_typed_error_and_explicit_override(self):
        result=self.run_client(dict(ok=False,code='command-review-authentication-missing'))
        self.assertIn(b'command-review-authentication-missing',result.stderr);self.assertFalse(self.record.exists())
        self.assertEqual(self.run_client(override=True).returncode,0)
        self.assertTrue(self.critical_record.exists());self.assertFalse(self.record.exists())
        request=json.loads(self.critical_record.read_text())['command'];self.assertEqual(request['authority'],hashlib.sha256(self.authority.read_bytes()).hexdigest())
    def test_nonprefixed_review_errors_offer_critical_route_without_auth(self):
        for code in ('command-schema-invalid','command-context-compacted'):
            with self.subTest(code=code):
                result=self.run_client(dict(ok=False,code=code))
                self.assertIn(b'--human-override identity',result.stderr)
                self.assertFalse(self.record.exists());self.assertFalse(self.critical_record.exists())
        for code in ('command-authority-changed','command-binding-changed'):
            result=self.run_client(dict(ok=False,code=code))
            self.assertNotIn(b'--human-override',result.stderr)

    def test_escaped_control_output_capacity(self):
        result=self.run_client(dict(ok=True,exitCode=0,stdout='\x00'*65536,stderr=''))
        self.assertEqual(result.returncode,0);self.assertEqual(result.stdout,b'\0'*65536)
if __name__=='__main__':unittest.main()
