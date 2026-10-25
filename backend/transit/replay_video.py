"""Bounded private background rendering; no participant credentials reach Chromium."""
import hashlib
import os
from django.conf import settings
import json
import secrets
import subprocess
import tempfile
import threading
import time
from pathlib import Path

_jobs = {}
_lock = threading.Lock()

def cache_dir(session):
    db=Path(getattr(settings,'PAP_USABILITY_DB',Path.home()/'.local/state/pap/usability/events.sqlite3'))
    folder=db.parent/'exports'/str(session)
    folder.mkdir(parents=True,exist_ok=True,mode=0o700)
    return folder

def revision(rows):
    digest=hashlib.sha256(b'export-v3')
    for row in rows:digest.update(json.dumps(row,ensure_ascii=False).encode())
    return digest.hexdigest()

def token_for(owner,key):
    return hashlib.sha256((str(owner)+key).encode()).hexdigest()

def start(events, owner, key=None):
    with _lock:
        key=key or hashlib.sha256(json.dumps(events).encode()).hexdigest()
        token=token_for(owner,key)
        output=cache_dir(owner[1])/(token+'.webm')
        if output.is_file():
            _jobs[token]={'owner':owner,'state':'ready','path':output}
            return token
        if token in _jobs and _jobs[token]['state']=='running':return token
        if any(j['state']=='running' for j in _jobs.values()):
            raise RuntimeError('Já há um vídeo sendo gerado. Tente novamente ao terminar.')
        folder=tempfile.TemporaryDirectory(prefix='pap-video-')
        job={'owner':owner,'created':time.time(),'state':'running','temp':folder,'destination':output}
        _jobs[token]=job
        thread=threading.Thread(target=_render,args=(job,events),daemon=True)
        thread.start()
        return token

def _render(job, events):
    folder=Path(job['temp'].name)
    source=folder/'events.json';output=folder/'replay.webm'
    try:
        source.write_text(json.dumps(events))
        script=Path(__file__).resolve().parents[2]/'scripts/render_replay_video.cjs'
        subprocess.run(['node',str(script),str(source),str(output)],check=True,capture_output=True,timeout=3700)
        if not output.is_file() or output.stat().st_size==0:raise RuntimeError('Empty video')
        os.replace(output,job['destination'])
        os.chmod(job['destination'],0o600)
        job['path']=job['destination'];job['state']='ready'
    except Exception:
        job['state']='error'
    finally:
        source.unlink(missing_ok=True)
        job['temp'].cleanup()

def get(token, owner):
    if not isinstance(token,str) or len(token)!=64 or any(c not in '0123456789abcdef' for c in token):return None
    job=_jobs.get(token)
    if job is None:
        output=cache_dir(owner[1])/(token+'.webm')
        # Token is unguessable; cached downloads still require active admin and session access.
        if output.is_file():job={'owner':owner,'state':'ready','path':output}
    return job if job and job['owner']==owner else None
