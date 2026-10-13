import json, os, pathlib, selectors, signal, subprocess, sys, tempfile, time, uuid
# Optional exact-binary proof; no personal state, network or model turns.
import argparse
parser=argparse.ArgumentParser(description="Disposable Codex 0.160 history read/resume proof")
parser.add_argument("--bwrap", required=True)
parser.add_argument("--codex", required=True)
args=parser.parse_args()
BWRAP=args.bwrap; CLI=args.codex
for binary in (BWRAP, CLI):
 assert pathlib.Path(binary).is_absolute() and pathlib.Path(binary).is_file()
version=subprocess.check_output([CLI,"--version"],env={"HOME":"/nonexistent"},timeout=5,stderr=subprocess.DEVNULL).decode().strip()
assert version == "codex-cli 0.160.0", "Fixture requires the exact 0.160.0 CLI"
with tempfile.TemporaryDirectory(prefix='phoenix-history-proof-') as d:
 r=pathlib.Path(d); home=r/'native'; home.mkdir(); private=r/'worker'; private.mkdir(); db=r/'sqlite'; db.mkdir()
 (home/'auth.json').write_text(json.dumps({'fixtureSecret':'synthetic-not-a-credential'}))
 for n in ['sessions','archived_sessions','thread-writer-locks']:(home/n).mkdir()
 tid=str(uuid.uuid4()); stamp='2026-10-13T00:00:00Z'; roll=home/'sessions'/f'rollout-2026-10-13T00-00-00-{tid}.jsonl'
 meta={'timestamp':stamp,'type':'session_meta','payload':{'session_id':tid,'id':tid,'timestamp':stamp,'cwd':d,'originator':'disposable-proof','cli_version':'0.160.0','source':'cli','model_provider':'openai','history_mode':'legacy'}}
 event={'timestamp':stamp,'type':'event_msg','payload':{'type':'user_message','message':'Disposable history fixture','kind':'plain'}}
 roll.write_text('\n'.join(map(json.dumps,[meta,event]))+'\n')
 results=[]
 for worker in [False,True,False]:
  cmd=[BWRAP,'--die-with-parent','--new-session','--unshare-all','--ro-bind','/nix/store','/nix/store','--proc','/proc','--dev','/dev','--tmpfs','/tmp','--bind',d,d]
  if worker:
   cmd+=['--bind',str(private),str(home)]
   for n in ['sessions','archived_sessions','thread-writer-locks']:cmd+=['--bind',str(home/n),str(home/n)]
  cmd+=['--clearenv','--setenv','HOME',str(home),'--setenv','CODEX_HOME',str(home),'--setenv','CODEX_SQLITE_HOME',str(db),'--chdir',d,sys.executable,'-c',('import os,sys; from pathlib import Path; assert not Path(os.environ["CODEX_HOME"],"auth.json").exists(); os.execv(sys.argv[1],sys.argv[1:])' if worker else 'import os,sys; os.execv(sys.argv[1],sys.argv[1:])'),CLI,'-c','check_for_update_on_startup=false','app-server']
  p=subprocess.Popen(cmd,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
  sel=selectors.DefaultSelector();sel.register(p.stdout,selectors.EVENT_READ); buf=b''; deadline=time.monotonic()+25
  def rpc(i,method,params):
   global buf
   p.stdin.write((json.dumps({'id':i,'method':method,'params':params})+'\n').encode());p.stdin.flush()
   while time.monotonic()<deadline:
    if not sel.select(max(0,deadline-time.monotonic())):break
    data=os.read(p.stdout.fileno(),65536)
    if not data:break
    buf+=data
    while b'\n' in buf:
     line,buf=buf.split(b'\n',1)
     try:obj=json.loads(line)
     except ValueError:continue
     if obj.get('id')==i:return obj
   return {'error':{'code':'timeout'}}
  try:
   init=rpc(1,'initialize',{'clientInfo':{'name':'disposable-history-proof','version':'1'},'capabilities':{'experimentalApi':True}})
   p.stdin.write(b'{"method":"initialized","params":{}}\n');p.stdin.flush()
   read=rpc(2,'thread/read',{'threadId':tid,'includeTurns':True})
   resume=rpc(3,'thread/resume',{'threadId':tid,'path':str(roll),'cwd':d,'persistExtendedHistory':False})
   fork=rpc(4,'thread/fork',{'threadId':tid,'cwd':d,'persistExtendedHistory':True}) if worker else None
   if fork and 'result' in fork:
    tid=fork['result']['thread']['id']; roll=pathlib.Path(fork['result']['thread']['path'])
   results.append({'workerNativeAuthAbsent':worker, 'forkCreated': bool(fork and 'result' in fork),'view':'worker' if worker else 'native','initialized':'result'in init,'read':'result'in read,'resumed':'result'in resume,'readCode':read.get('error',{}).get('code'),'resumeCode':resume.get('error',{}).get('code')})
  finally:
   os.killpg(p.pid,signal.SIGTERM)
   try:p.communicate(timeout=4)
   except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);p.communicate(timeout=4)
   sel.close()
 assert len(results)==3 and all(row['initialized'] and row['read'] and row['resumed'] for row in results), 'History read/resume proof failed'
 assert results[1]['forkCreated'], 'Worker fork creation failed'
 print(json.dumps({'cli':'0.160.0','network':'unshared; no model turn requested','results':results,'processesReaped':True,'state':'disposable synthetic only'}))
