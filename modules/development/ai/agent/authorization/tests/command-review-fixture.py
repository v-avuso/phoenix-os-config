"""VM-only model double; real UID transition and worker envelope remain exercised."""
import json
from pathlib import Path
import subprocess
class ReviewDenied(Exception): pass
class ReviewVerdictError(Exception):
    def __init__(self,code):self.code=code

def run(argv, *, data=None, timeout=60, env=None, **kwargs):
    return subprocess.run(argv,input=data,timeout=timeout,env=env,capture_output=True,check=True).stdout

def review(config,binding,files,diff,temporary,baseline=None):
    path=Path('/var/lib/command-review/visits')
    with path.open('a') as stream:stream.write(binding['operation']+'\n')
    if binding['operation']=='error':raise ReviewVerdictError('review-invocation-failed')
    if binding['operation']=='timeout-review':raise ReviewVerdictError('review-timeout')
    verdict=dict(binding,approved=binding['operation']!='denied',summary='fixture only')
    if binding['operation']=='wrong':verdict['programSha256']='replacement'
    return verdict
