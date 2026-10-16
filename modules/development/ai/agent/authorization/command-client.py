"""Fixed installed command client; explicit human fallback, never automatic."""
import argparse
import json
import hashlib
from pathlib import Path
import socket
import subprocess
import sys

LIMIT = 6 * 65536 + 16384
# Only failures of independent review offer an explicit critical route. A changed
# authority/program binding requires a new exact request, never an override hint.
REVIEW_FAILURES = {'command-schema-invalid','command-binding-mismatch',
    'command-context-compacted','command-context-request-invalid','command-context-request-oversized'}

def envelope(args, authority):
    return {'version':1,'operation':args.operation,'task':args.task,'reason':args.reason,'authority':authority}

def main():
    config = json.loads(Path(sys.argv[1]).read_text())
    parser = argparse.ArgumentParser(prog='phoenix-command', allow_abbrev=False)
    parser.add_argument('--task', required=True); parser.add_argument('--reason', required=True)
    parser.add_argument('--human-override', action='store_true', help='Explicit fresh native authentication; never selected automatically')
    parser.add_argument('operation')
    args = parser.parse_args(sys.argv[2:])
    publication = Path(config['authority']).read_bytes()
    request = envelope(args, hashlib.sha256(publication).hexdigest())
    data = json.dumps({'command':request}).encode()+b'\n'
    if len(data)>4096: raise ValueError('request bound')
    def authenticate(critical=False):
        helper = config.get('criticalCommand' if critical else 'operatorCommand')
        if not helper:
            return None
        entry = json.loads(publication)['registry']['entries'].get(args.operation)
        if entry is None: raise ValueError('unknown operation')
        print('Exact installed command: '+json.dumps([entry['executable'],*entry['arguments']]),file=sys.stderr)
        print('Task/reason (untrusted context): '+json.dumps([args.task,args.reason]),file=sys.stderr)
        result = subprocess.run(helper,input=data,capture_output=True,timeout=360)
        if result.returncode:
            print('phoenix-command: native authentication or command failed',file=sys.stderr)
            return b'{"ok":false,"code":"command-authentication-failed"}'
        if len(result.stdout)>LIMIT: raise ValueError('response bound')
        return result.stdout
    if args.human_override:
        raw = authenticate(critical=True)
        if raw is None:
            print('phoenix-command: human authentication requires the native host client', file=sys.stderr)
            return 1
    else:
        with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as client:
            client.settimeout(360); client.connect(config['socket']);client.sendall(data);client.shutdown(socket.SHUT_WR)
            raw=bytearray()
            while True:
                block=client.recv(8192)
                if not block: break
                raw.extend(block)
                if len(raw)>LIMIT: raise ValueError('response bound')
        decision = json.loads(raw)
        # Configured human mode is the ordinary route after a matched root decision.
        # Review denial/error never automatically enters authentication.
        if decision.get('code') == 'command-human-authentication-required':
            authenticated = authenticate()
            if authenticated is not None: raw = authenticated
    response=json.loads(raw)
    if not response.get('ok',False):
        import re
        code = response.get('code','command-protocol-error')
        if not isinstance(code,str) or not re.fullmatch(r'[a-z][a-z0-9-]{0,79}',code): code='command-protocol-error'
        print('phoenix-command: '+code+'; no execution granted',file=sys.stderr)
        if code == 'command-review-denied' and isinstance(response.get('summary'),str):
            import unicodedata
            summary=''.join(c for c in response['summary'] if not unicodedata.category(c).startswith('C'))[:1000]
            print('Reviewer explanation (advisory): '+summary,file=sys.stderr)
        review_failure = code.startswith('command-review-') or code in REVIEW_FAILURES
        if code == 'command-human-authentication-required' or review_failure:
            import shlex
            explicit = ['--human-override'] if review_failure else []
            native = ['phoenix-authorize','--task',args.task,'--reason',args.reason,'--','phoenix-command',*explicit,args.operation]
            print('Native host route (requires authorization): '+shlex.join(native),file=sys.stderr)
        return 1
    sys.stdout.write(response.get('stdout',''));sys.stderr.write(response.get('stderr',''))
    return response['exitCode'] if 0 <= response.get('exitCode',1) <= 255 else 1

if __name__=='__main__':
    try: raise SystemExit(main())
    except (ValueError,OSError,KeyError,subprocess.TimeoutExpired):
        raise SystemExit('phoenix-command: invalid request or unavailable installed client') from None
